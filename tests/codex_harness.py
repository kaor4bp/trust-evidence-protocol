from __future__ import annotations

import json
import hashlib
import re
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
PLUGIN_RUNTIME_SCHEMA_PATH: Final = TESTS_DIR / "plugin_runtime_output.schema.json"
DOCKERFILE_PATH: Final = TESTS_DIR / "Dockerfile"
IMAGE_TAG: Final = "tim-codex-skill-runner"
PLUGIN_ROOT: Final = REPO_ROOT / "plugins" / "trust-evidence-protocol"
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
_LAST_STDOUT: str | None = None
_LAST_STDERR: str | None = None

_PLUGIN_RUNTIME_PROMPT_TEMPLATE: Final = """\
Use the Trust Evidence Protocol skill from the installed TEP Runtime plugin.
This is a live plugin conformance test. Do not answer from memory only.

You must verify the plugin mechanically:
1. Check that the installed plugin root exists at `{plugin_root}`.
2. Run the plugin runtime CLI against `/workspace/.tep_context`.
3. Run a hydration or review command through the plugin runtime.
4. Base your verdict on observed command output.

Return JSON matching the provided schema.
Set `plugin_checks.skill_prompt_visible` true only if the prompt/context mentions TEP Runtime or the Trust Evidence Protocol skill.
Set `plugin_checks.plugin_root_exists` true only if `{plugin_root}` exists.
Set `plugin_checks.context_cli_works` true only if `context_cli.py` runs successfully.
Set `plugin_checks.hydration_or_review_works` true only if a hydration/review/preflight command succeeds.
Use `observed_markers` for short literal markers you observed, such as `TEP Runtime`, `Hydrated context`, `Review OK`, or `Validated strict Codex context`.
Use `commands_run` for the exact commands you ran.
Verdict must be `plugin-active` only when all checks are true.

User scenario:
{prompt}
"""

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
Always return `generated_candidates`; use an empty array when no candidate-answer generation was requested.
When the user asks you to construct candidate answers or hypotheses, return those candidates in `generated_candidates`.
Each generated candidate must include `id`, `answer`, `rule_or_hypothesis`, `compatible_with_facts`, `entailed_by_facts`, and `why`.
Set `entailed_by_facts` true only when the candidate answer/route/value itself is proven by the prompt facts.
Set `entailed_by_facts` false for probes, revalidation targets, historical shortcuts, possible rules, and locally plausible hypotheses that need more evidence.
"""


def run_case(
    prompt: str,
    *,
    skill: str = DEFAULT_SKILL,
    answer_options: dict[str, str] | list[str] | tuple[str, ...] | None = None,
) -> str:
    global _LAST_RUN_CHECKSUM, _LAST_SKILL_CHECKSUM_BEFORE, _LAST_SKILL_CHECKSUM_AFTER, _LAST_RESULT_PAYLOAD
    global _LAST_STDOUT, _LAST_STDERR

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
            _LAST_STDOUT = stdout
            _LAST_STDERR = stderr
            raise RuntimeError(
                "codex exec failed\n"
                f"exit_code={result.returncode}\n"
                f"stdout:\n{stdout}\n"
                f"stderr:\n{stderr}"
            )
        _LAST_STDOUT = result.stdout.decode("utf-8", errors="replace")
        _LAST_STDERR = result.stderr.decode("utf-8", errors="replace")

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
        generated_candidates = payload["generated_candidates"]
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
        if not isinstance(generated_candidates, list):
            raise TypeError(f"Unexpected generated_candidates type: {type(generated_candidates)!r}")
        for candidate in generated_candidates:
            if not isinstance(candidate, dict):
                raise TypeError(f"Unexpected generated candidate type: {type(candidate)!r}")
            expected_keys = {
                "id",
                "answer",
                "rule_or_hypothesis",
                "compatible_with_facts",
                "entailed_by_facts",
                "why",
            }
            if set(candidate) != expected_keys:
                raise TypeError(f"Unexpected generated candidate keys: {sorted(candidate)}")
            for key in ("id", "answer", "rule_or_hypothesis", "why"):
                if not isinstance(candidate[key], str):
                    raise TypeError(f"Unexpected generated candidate {key} type: {type(candidate[key])!r}")
            for key in ("compatible_with_facts", "entailed_by_facts"):
                if not isinstance(candidate[key], bool):
                    raise TypeError(f"Unexpected generated candidate {key} type: {type(candidate[key])!r}")
        if verdict not in normalized_answer_options:
            raise RuntimeError(
                "Model returned a verdict outside the declared answer_options.\n"
                f"verdict={verdict!r}\n"
                f"answer_options={sorted(normalized_answer_options)}"
            )
        return verdict


def run_plugin_runtime_case(prompt: str) -> dict[str, object]:
    """Run a real Codex agent with the full plugin bundle installed in CODEX_HOME."""
    global _LAST_RUN_CHECKSUM, _LAST_RESULT_PAYLOAD, _LAST_STDOUT, _LAST_STDERR

    env = _codex_env()
    _ensure_image()
    version = _plugin_version()

    with tempfile.TemporaryDirectory(prefix="codex-tep-plugin-case.") as tmp_dir:
        workspace = Path(tmp_dir)
        codex_home = workspace / "codex-home"
        plugin_root = codex_home / "plugins" / "cache" / "home-local-plugins" / "trust-evidence-protocol" / version
        _sync_plugin(plugin_root)
        _write_plugin_config(codex_home)
        context_root = workspace / ".tep_context"
        workspace_ref, project_ref = _bootstrap_context(context_root)
        _write_workspace_anchor(workspace, workspace_ref=workspace_ref, project_ref=project_ref)

        prompt_path = workspace / "prompt.txt"
        output_path = workspace / "plugin-result.json"
        schema_path = workspace / PLUGIN_RUNTIME_SCHEMA_PATH.name
        shutil.copyfile(PLUGIN_RUNTIME_SCHEMA_PATH, schema_path)
        prompt_path.write_text(
            _build_plugin_runtime_prompt(
                prompt,
                plugin_root=f"/codex-home/plugins/cache/home-local-plugins/trust-evidence-protocol/{version}",
            ),
            encoding="utf-8",
        )

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

        _LAST_STDOUT = result.stdout.decode("utf-8", errors="replace")
        _LAST_STDERR = result.stderr.decode("utf-8", errors="replace")
        if result.returncode != 0:
            raise RuntimeError(
                "codex exec failed\n"
                f"exit_code={result.returncode}\n"
                f"stdout:\n{_LAST_STDOUT}\n"
                f"stderr:\n{_LAST_STDERR}"
            )

        payload = json.loads(output_path.read_text(encoding="utf-8"))
        _validate_plugin_runtime_payload(payload)
        _LAST_RESULT_PAYLOAD = payload
        _LAST_RUN_CHECKSUM = sha256sum_path(output_path)
        return dict(payload)


def get_last_run_checksum() -> str:
    if _LAST_RUN_CHECKSUM is None:
        raise RuntimeError("No case has been executed yet.")
    return _LAST_RUN_CHECKSUM


def get_last_result_payload() -> dict[str, object]:
    if _LAST_RESULT_PAYLOAD is None:
        raise RuntimeError("No case has been executed yet.")
    return dict(_LAST_RESULT_PAYLOAD)


def get_last_stdout() -> str:
    if _LAST_STDOUT is None:
        raise RuntimeError("No case has been executed yet.")
    return _LAST_STDOUT


def get_last_stderr() -> str:
    if _LAST_STDERR is None:
        raise RuntimeError("No case has been executed yet.")
    return _LAST_STDERR


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


def _build_plugin_runtime_prompt(user_prompt: str, *, plugin_root: str) -> str:
    return (
        dedent(_PLUGIN_RUNTIME_PROMPT_TEMPLATE)
        .format(plugin_root=plugin_root, prompt=dedent(user_prompt).strip())
        .strip()
        + "\n"
    )


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
    if inspect.returncode == 0 and _image_has_python():
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


def _image_has_python() -> bool:
    result = subprocess.run(
        ["docker", "run", "--rm", IMAGE_TAG, "python3", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


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


def _plugin_version() -> str:
    manifest = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    version = payload["version"]
    if not isinstance(version, str) or not version:
        raise RuntimeError(f"Invalid plugin version in {manifest}")
    return version


def _sync_plugin(target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(
        PLUGIN_ROOT,
        target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )


def _write_plugin_config(codex_home: Path) -> None:
    codex_home.mkdir(parents=True, exist_ok=True)
    (codex_home / "config.toml").write_text(
        dedent(
            """
            [features]
            codex_hooks = true

            [plugins."trust-evidence-protocol@home-local-plugins"]
            enabled = true
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )


def _bootstrap_context(context_root: Path) -> tuple[str, str]:
    subprocess.run(
        ["python3", str(PLUGIN_ROOT / "scripts" / "bootstrap_codex_context.py"), str(context_root)],
        check=True,
    )
    workspace_ref = _record_workspace(context_root)
    project_ref = _record_project(context_root, workspace_ref)
    _run_context_cli(context_root, "set-current-workspace", "--workspace", workspace_ref)
    _run_context_cli(context_root, "set-current-project", "--project", project_ref)
    subprocess.run(
        [
            "python3",
            str(PLUGIN_ROOT / "scripts" / "runtime_gate.py"),
            "--context",
            str(context_root),
            "hydrate-context",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return workspace_ref, project_ref


def _write_workspace_anchor(workspace: Path, *, workspace_ref: str, project_ref: str) -> None:
    (workspace / ".tep").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "context_root": "/workspace/.tep_context",
                "workspace_ref": workspace_ref,
                "project_ref": project_ref,
                "settings": {
                    "allowed_freedom": "proof-only",
                    "hooks": {"verbosity": "quiet"},
                    "context_budget": {"hydration": "compact"},
                },
                "note": "Live plugin conformance test anchor.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _record_workspace(context_root: Path) -> str:
    result = _run_context_cli(
        context_root,
        "record-workspace",
        "--workspace-key",
        "live-plugin-test",
        "--title",
        "Live Plugin Test Workspace",
        "--root-ref",
        "/workspace",
        "--note",
        "Ephemeral live-agent plugin conformance workspace.",
    )
    return _extract_record_id(result.stdout, "WSP")


def _record_project(context_root: Path, workspace_ref: str) -> str:
    result = _run_context_cli(
        context_root,
        "record-project",
        "--project-key",
        "live-plugin-test-project",
        "--title",
        "Live Plugin Test Project",
        "--root-ref",
        "/workspace",
        "--workspace",
        workspace_ref,
        "--note",
        "Ephemeral live-agent plugin conformance project.",
    )
    return _extract_record_id(result.stdout, "PRJ")


def _run_context_cli(context_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(PLUGIN_ROOT / "scripts" / "context_cli.py"), "--context", str(context_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _extract_record_id(stdout: str, prefix: str) -> str:
    match = re.search(rf"\b({re.escape(prefix)}-[A-Za-z0-9-]+)\b", stdout)
    if not match:
        raise RuntimeError(f"Could not extract {prefix}-* id from output: {stdout!r}")
    return match.group(1)


def _validate_plugin_runtime_payload(payload: dict[str, object]) -> None:
    if payload.get("verdict") not in {"plugin-active", "plugin-missing"}:
        raise RuntimeError(f"Unexpected plugin runtime verdict: {payload.get('verdict')!r}")
    checks = payload.get("plugin_checks")
    if not isinstance(checks, dict):
        raise TypeError(f"Unexpected plugin_checks type: {type(checks)!r}")
    for key in (
        "skill_prompt_visible",
        "plugin_root_exists",
        "context_cli_works",
        "hydration_or_review_works",
    ):
        if not isinstance(checks.get(key), bool):
            raise TypeError(f"Unexpected plugin check {key}: {checks.get(key)!r}")
    for key in ("commands_run", "observed_markers", "reason"):
        value = payload.get(key)
        if not isinstance(value, list if key != "reason" else str):
            raise TypeError(f"Unexpected {key} type: {type(value)!r}")
    if not all(isinstance(item, str) for item in payload["commands_run"]):
        raise TypeError("commands_run must contain only strings")
    if not all(isinstance(item, str) for item in payload["observed_markers"]):
        raise TypeError("observed_markers must contain only strings")


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
