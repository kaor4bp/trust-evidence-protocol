from __future__ import annotations

import json
import hashlib
import shutil
import subprocess
import tempfile
import os
from pathlib import Path
from textwrap import dedent
from typing import Final

REPO_ROOT: Final = Path(__file__).resolve().parent.parent
TESTS_DIR: Final = REPO_ROOT / "tests"
ENV_PATH: Final = REPO_ROOT / ".env"
SCHEMA_PATH: Final = TESTS_DIR / "case_output.schema.json"
DOCKERFILE_PATH: Final = TESTS_DIR / "Dockerfile"
IMAGE_TAG: Final = "tim-codex-skill-runner"
PLUGIN_SKILLS_ROOT: Final = REPO_ROOT / "plugins" / "trust-evidence-protocol" / "skills"
DEFAULT_SKILL: Final = "trust-evidence-protocol"
DEFAULT_ANSWER_OPTIONS: Final[dict[str, str]] = {
    "green": "if you fix the test and it should become green",
    "red": "if the test should remain red or should not be fixed into green",
    "ask": "if you must stop and ask the user before acting",
}
_LAST_RUN_CHECKSUM: str | None = None
_LAST_SKILL_CHECKSUM_BEFORE: str | None = None
_LAST_SKILL_CHECKSUM_AFTER: str | None = None
_LAST_RESULT_PAYLOAD: dict[str, object] | None = None

_SYSTEM_PROMPT_TEMPLATE: Final = """\
Use the {skill} skill.
Answer only from the prompt content provided by the user.
Do not assume access to any hidden oracle, expected answer, or external dataset.
Return a JSON object matching the provided output schema.
The skill policy is allowed decision policy; only factual premises must come from the user prompt.

Critical TEP verdict policy:
- Never choose `green` by solving unknown values from an assertion target, expected total, or "make it green" instruction.
- If a component needed for green has no concrete anchored value, put it in `underdetermined_targets`.
- If such an underdetermined target remains, choose `ask` when available; if `ask` is unavailable, choose `red`.
- `implementation-choice` cannot introduce concrete values that are not entailed by the prompt facts.

Answer options:
{answer_options}

Keep reason short and concrete.
Set `allowed_freedom` to the operative freedom level you used for the final decision.
Return `score_events` as short machine events using only `sign`, `tag`, `target`, `delta`, and `note`.
Use `basis` to declare which source surfaces you relied on.
Use `used_rules` for the main inference rules you applied.
List any still-underdetermined targets in `underdetermined_targets`.
List any under-audit artifacts used as premises in `audit_artifacts_used_as_premises`.
"""


def run_case(
    prompt: str,
    *,
    skill: str = DEFAULT_SKILL,
    answer_options: dict[str, str] | list[str] | tuple[str, ...] | None = None,
) -> str:
    global _LAST_RUN_CHECKSUM, _LAST_SKILL_CHECKSUM_BEFORE, _LAST_SKILL_CHECKSUM_AFTER, _LAST_RESULT_PAYLOAD

    env = _codex_env()
    _ensure_image()
    normalized_answer_options = _normalize_answer_options(answer_options)
    source_skill_path = _skill_source_path(skill)
    _LAST_SKILL_CHECKSUM_BEFORE = sha256sum_path(source_skill_path)

    with tempfile.TemporaryDirectory(prefix="codex-trust-case.") as tmp_dir:
        workspace = Path(tmp_dir)
        codex_home = workspace / "codex-home"
        _sync_skill(source_skill_path, codex_home, skill)
        prompt_path = workspace / "prompt.txt"
        output_path = workspace / "result.json"
        schema_path = workspace / SCHEMA_PATH.name

        prompt_path.write_text(
            _build_prompt(prompt, skill=skill, answer_options=normalized_answer_options),
            encoding="utf-8",
        )
        shutil.copyfile(SCHEMA_PATH, schema_path)

        _login_codex(codex_home, env["OPENAI_API_KEY"], env=env)

        command = [
            "docker",
            "run",
            "--rm",
            "-i",
            "-e",
            "CODEX_HOME=/codex-home",
            "-v",
            f"{codex_home}:/codex-home",
            "-v",
            f"{workspace}:/workspace",
            IMAGE_TAG,
            "codex",
            "exec",
            "--cd",
            "/workspace",
            "--sandbox",
            "workspace-write",
            "--skip-git-repo-check",
            "--color",
            "never",
            "--output-schema",
            f"/workspace/{schema_path.name}",
            "-o",
            f"/workspace/{output_path.name}",
            "-",
        ]

        with prompt_path.open("rb") as stdin_file:
            result = subprocess.run(
                command,
                stdin=stdin_file,
                capture_output=True,
                text=False,
                check=False,
                env=env,
            )

        if result.returncode != 0:
            stdout = result.stdout.decode("utf-8", errors="replace")
            stderr = result.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(
                "codex exec failed\n"
                f"exit_code={result.returncode}\n"
                f"stdout:\n{stdout}\n"
                f"stderr:\n{stderr}"
            )

        _LAST_SKILL_CHECKSUM_AFTER = sha256sum_path(source_skill_path)
        if _LAST_SKILL_CHECKSUM_AFTER != _LAST_SKILL_CHECKSUM_BEFORE:
            raise RuntimeError(
                "Skill files changed during case execution.\n"
                f"skill={skill}\n"
                f"before={_LAST_SKILL_CHECKSUM_BEFORE}\n"
                f"after={_LAST_SKILL_CHECKSUM_AFTER}"
            )

        payload = json.loads(output_path.read_text(encoding="utf-8"))
        _LAST_RESULT_PAYLOAD = payload
        _LAST_RUN_CHECKSUM = sha256sum_path(output_path)
        verdict = payload["verdict"]
        if not isinstance(verdict, str):
            raise TypeError(f"Unexpected verdict type: {type(verdict)!r}")
        reason = payload["reason"]
        allowed_freedom = payload["allowed_freedom"]
        score_events = payload["score_events"]
        if not isinstance(reason, str):
            raise TypeError(f"Unexpected reason type: {type(reason)!r}")
        if not isinstance(allowed_freedom, str):
            raise TypeError(f"Unexpected allowed_freedom type: {type(allowed_freedom)!r}")
        if not isinstance(score_events, list):
            raise TypeError(f"Unexpected score_events type: {type(score_events)!r}")
        basis = payload["basis"]
        used_rules = payload["used_rules"]
        underdetermined_targets = payload["underdetermined_targets"]
        audit_artifacts_used_as_premises = payload["audit_artifacts_used_as_premises"]
        for event in score_events:
            if not isinstance(event, dict):
                raise TypeError(f"Unexpected score event type: {type(event)!r}")
            if set(event) != {"sign", "tag", "target", "delta", "note"}:
                raise TypeError(f"Unexpected score event keys: {sorted(event)}")
            if event["sign"] not in {"+", "-"}:
                raise TypeError(f"Unexpected score event sign: {event['sign']!r}")
            if event["tag"] not in {
                "linking",
                "freshness",
                "verification",
                "scope",
                "promotion",
                "persistence",
            }:
                raise TypeError(f"Unexpected score event tag: {event['tag']!r}")
            if not isinstance(event["target"], str):
                raise TypeError(f"Unexpected score event target: {type(event['target'])!r}")
            if not isinstance(event["delta"], int):
                raise TypeError(f"Unexpected score event delta: {type(event['delta'])!r}")
            if not isinstance(event["note"], str):
                raise TypeError(f"Unexpected score event note: {type(event['note'])!r}")
        if not isinstance(basis, list) or not all(isinstance(item, str) for item in basis):
            raise TypeError(f"Unexpected basis type: {type(basis)!r}")
        if not isinstance(used_rules, list) or not all(isinstance(item, str) for item in used_rules):
            raise TypeError(f"Unexpected used_rules type: {type(used_rules)!r}")
        if not isinstance(underdetermined_targets, list) or not all(
            isinstance(item, str) for item in underdetermined_targets
        ):
            raise TypeError(
                f"Unexpected underdetermined_targets type: {type(underdetermined_targets)!r}"
            )
        if not isinstance(audit_artifacts_used_as_premises, list) or not all(
            isinstance(item, str) for item in audit_artifacts_used_as_premises
        ):
            raise TypeError(
                "Unexpected audit_artifacts_used_as_premises type: "
                f"{type(audit_artifacts_used_as_premises)!r}"
            )
        if verdict not in normalized_answer_options:
            raise RuntimeError(
                "Model returned a verdict outside the declared answer_options.\n"
                f"verdict={verdict!r}\n"
                f"answer_options={sorted(normalized_answer_options)}"
            )
        return verdict


def get_last_run_checksum() -> str:
    if _LAST_RUN_CHECKSUM is None:
        raise RuntimeError("No case has been executed yet.")
    return _LAST_RUN_CHECKSUM


def get_last_result_payload() -> dict[str, object]:
    if _LAST_RESULT_PAYLOAD is None:
        raise RuntimeError("No case has been executed yet.")
    return dict(_LAST_RESULT_PAYLOAD)


def get_last_reason() -> str:
    return get_last_result_payload()["reason"]


def get_last_allowed_freedom() -> str:
    return get_last_result_payload()["allowed_freedom"]


def get_last_score_events() -> list[dict[str, object]]:
    return list(get_last_result_payload()["score_events"])


def get_last_skill_checksum_before() -> str:
    if _LAST_SKILL_CHECKSUM_BEFORE is None:
        raise RuntimeError("No case has been executed yet.")
    return _LAST_SKILL_CHECKSUM_BEFORE


def get_last_skill_checksum_after() -> str:
    if _LAST_SKILL_CHECKSUM_AFTER is None:
        raise RuntimeError("No case has been executed yet.")
    return _LAST_SKILL_CHECKSUM_AFTER


def sha256sum_path(path: str | Path) -> str:
    target = Path(path)
    if target.is_file():
        return _sha256_file(target)
    if target.is_dir():
        return _sha256_directory(target)
    raise FileNotFoundError(f"Path does not exist: {target}")


def _build_prompt(user_prompt: str, *, skill: str, answer_options: dict[str, str]) -> str:
    answer_options_block = "\n".join(
        f'- "{term}": {description}' for term, description in answer_options.items()
    )
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        skill=skill,
        answer_options=answer_options_block,
    )
    return dedent(system_prompt).strip() + "\n\n" + dedent(user_prompt).strip() + "\n"


def _normalize_answer_options(
    answer_options: dict[str, str] | list[str] | tuple[str, ...] | None,
) -> dict[str, str]:
    if answer_options is None:
        return dict(DEFAULT_ANSWER_OPTIONS)

    if isinstance(answer_options, dict):
        if not answer_options:
            raise ValueError("answer_options dict must not be empty.")
        return dict(answer_options)

    normalized: dict[str, str] = {}
    for term in answer_options:
        if term not in DEFAULT_ANSWER_OPTIONS:
            raise KeyError(
                f"Unknown answer option {term!r}. "
                "Pass a dict[str, str] for custom options."
            )
        normalized[term] = DEFAULT_ANSWER_OPTIONS[term]
    if not normalized:
        raise ValueError("answer_options must not be empty.")
    return normalized


def _codex_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update(_read_dotenv(ENV_PATH))
    if not env.get("OPENAI_API_KEY"):
        raise RuntimeError(
            f"Missing OPENAI_API_KEY. Add it to {ENV_PATH} as:\n"
            "OPENAI_API_KEY=sk-..."
        )
    return env


def _ensure_image() -> None:
    inspect = subprocess.run(
        ["docker", "image", "inspect", IMAGE_TAG],
        capture_output=True,
        text=True,
        check=False,
    )
    if inspect.returncode == 0:
        return

    build = subprocess.run(
        [
            "docker",
            "build",
            "-t",
            IMAGE_TAG,
            "-f",
            str(DOCKERFILE_PATH),
            str(TESTS_DIR),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if build.returncode != 0:
        raise RuntimeError(
            "Failed to build Docker image\n"
            f"stdout:\n{build.stdout}\n"
            f"stderr:\n{build.stderr}"
        )


def _login_codex(codex_home: Path, api_key: str, *, env: dict[str, str]) -> None:
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-i",
            "-e",
            "CODEX_HOME=/codex-home",
            "-v",
            f"{codex_home}:/codex-home",
            IMAGE_TAG,
            "codex",
            "login",
            "-c",
            'cli_auth_credentials_store="file"',
            "--with-api-key",
        ],
        input=api_key.encode("utf-8"),
        capture_output=True,
        text=False,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(
            "codex login failed\n"
            f"exit_code={result.returncode}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            raise RuntimeError(f"Invalid .env line {line_number}: expected KEY=value")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if not key:
            raise RuntimeError(f"Invalid .env line {line_number}: empty key")
        values[key] = value
    return values


def _skill_source_path(skill: str) -> Path:
    skill_dir = PLUGIN_SKILLS_ROOT / skill
    if not skill_dir.is_dir() or not (skill_dir / "SKILL.md").exists():
        raise RuntimeError(f"Skill not found in plugin skills: {skill_dir}")
    return skill_dir


def _sync_skill(source_skill_path: Path, codex_home: Path, skill: str) -> None:
    skills_dir = codex_home / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_skill_path, skills_dir / skill)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_directory(path: Path) -> str:
    digest = hashlib.sha256()
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        relative = child.relative_to(path).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(_sha256_file(child).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()
