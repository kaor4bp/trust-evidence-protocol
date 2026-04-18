from __future__ import annotations

from pprint import pformat

from codex_harness import get_last_reason, get_last_result_payload, get_last_run_checksum, run_case


def assert_case(
    prompt: str,
    expected: str,
    *,
    skill: str = "trust-evidence-protocol",
    answer_options: dict[str, str] | list[str] | tuple[str, ...] | None = None,
) -> None:
    result = run_case(prompt, skill=skill, answer_options=answer_options)
    assert result == expected, (
        f"expected {expected!r}, got {result!r}\n"
        f"reason: {get_last_reason()}\n"
        f"trace:\n{pformat(get_last_result_payload(), sort_dicts=False)}"
    )
    assert len(get_last_run_checksum()) == 64
