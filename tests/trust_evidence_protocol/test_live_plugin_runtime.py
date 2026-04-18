from codex_harness import get_last_run_checksum, get_last_stdout, run_plugin_runtime_case


def test_live_agent_checks_installed_tep_runtime_plugin():
    payload = run_plugin_runtime_case(
        """
        Verify that this live-agent environment is using the installed TEP Runtime plugin,
        not only a copied standalone skill. Keep the check mechanical and report only
        observed plugin/runtime markers.
        """
    )

    checks = payload["plugin_checks"]
    assert payload["verdict"] == "plugin-active", payload
    assert checks == {
        "skill_prompt_visible": True,
        "plugin_root_exists": True,
        "context_cli_works": True,
        "hydration_or_review_works": True,
    }
    assert payload["commands_run"], payload
    assert payload["observed_markers"], payload
    assert any("context_cli.py" in command for command in payload["commands_run"]), payload
    assert any(
        marker in " ".join(payload["observed_markers"])
        for marker in ("Hydrated context", "Review OK", "Validated strict Codex context")
    ), payload
    assert len(get_last_run_checksum()) == 64
    assert "TEP Runtime" in get_last_stdout() or "Trust Evidence Protocol" in get_last_stdout()
