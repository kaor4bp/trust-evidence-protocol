from codex_harness import (
    get_last_run_checksum,
    get_last_stdout,
    run_curiosity_map_runtime_case,
    run_plugin_runtime_case,
)


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


def test_live_agent_checks_mcp_lookup_telemetry_runtime():
    payload = run_plugin_runtime_case(
        """
        Verify telemetry in the installed TEP Runtime plugin mechanically:
        1. Run a compact claim lookup such as `claim-graph --query telemetry --format json`
           against `/workspace/.tep_context`.
        2. Run `telemetry-report --format json` against `/workspace/.tep_context`.
        3. Report observed markers proving telemetry_report is available and reports
           lookup counters such as `telemetry_is_proof`, `event_count`, `by_tool`, or
           `claim-graph`.
        Do not rely on memory; base the verdict on command output.
        """
    )

    checks = payload["plugin_checks"]
    commands = " ".join(payload["commands_run"])
    markers = " ".join(payload["observed_markers"])
    assert payload["verdict"] == "plugin-active", payload
    assert checks["plugin_root_exists"] is True, payload
    assert checks["context_cli_works"] is True, payload
    assert checks["hydration_or_review_works"] is True, payload
    assert "claim-graph" in commands, payload
    assert "telemetry-report" in commands, payload
    assert any(marker in markers for marker in ("telemetry_is_proof", "event_count", "by_tool", "claim-graph")), payload


def test_live_agent_checks_telemetry_anomalies_and_workspace_guards():
    payload = run_plugin_runtime_case(
        """
        Verify the installed TEP Runtime plugin exposes the newer guard surfaces mechanically:
        1. Run `telemetry-report --format json` against `/workspace/.tep_context` and report
           the literal `anomalies` field marker from the JSON output.
        2. Run a command that proves `workspace-admission check --repo /workspace --format json`
           is available.
        3. Run a command that proves `working-context check-drift --task "live guard smoke" --format json`
           is available.
        4. Report observed literal markers: `anomalies`, `workspace-admission`, and `check-drift`.
        Do not rely on memory; base the verdict on command output.
        """
    )

    checks = payload["plugin_checks"]
    commands = " ".join(payload["commands_run"])
    markers = " ".join(payload["observed_markers"])
    assert payload["verdict"] == "plugin-active", payload
    assert checks["plugin_root_exists"] is True, payload
    assert checks["context_cli_works"] is True, payload
    assert checks["hydration_or_review_works"] is True, payload
    assert "telemetry-report" in commands, payload
    assert "workspace-admission" in commands, payload
    assert "check-drift" in commands, payload
    assert "anomalies" in markers, payload
    assert "workspace-admission" in markers, payload
    assert "check-drift" in markers, payload


def test_live_agent_checks_compact_lookup_help_route():
    payload = run_plugin_runtime_case(
        """
        Verify the installed TEP Runtime plugin exposes the compact lookup route in help:
        1. Run `help commands` through the installed plugin runtime CLI.
        2. Report observed literal markers from command output: `linked-records`,
           `guidelines-for`, `code-search`, and `telemetry-report`.
        Do not infer these markers from memory; base the verdict on command output.
        """
    )

    checks = payload["plugin_checks"]
    commands = " ".join(payload["commands_run"])
    markers = " ".join(payload["observed_markers"])
    assert payload["verdict"] == "plugin-active", payload
    assert checks["plugin_root_exists"] is True, payload
    assert checks["context_cli_works"] is True, payload
    assert checks["hydration_or_review_works"] is True, payload
    assert "help commands" in commands, payload
    assert "linked-records" in markers, payload
    assert "guidelines-for" in markers, payload
    assert "code-search" in markers, payload
    assert "telemetry-report" in markers, payload


def test_live_agent_uses_curiosity_map_brief_probe_route():
    payload = run_curiosity_map_runtime_case(
        """
        Verify the installed TEP Runtime plugin can guide curiosity-driven inspection mechanically:
        1. Run `map-brief --scope all --mode theory --volume compact --format json`
           against `/workspace/.tep_context`.
        2. Choose the first available candidate probe from that output.
        3. Run `probe-inspect --index 1 --scope all --mode theory --format json`.
        4. Run `probe-route --index 1 --scope all --mode theory --format json`.
        5. Report observed literal markers from command output: `map_graph_version`,
           `candidate_probes`, `inspection_is_proof`, `route_is_proof`,
           and `recommended_commands`.
        Do not conclude Facility and Program are linked from the probe itself; this test
        checks the TEP route, not the truth of the candidate link.
        """
    )

    checks = payload["plugin_checks"]
    commands = " ".join(payload["commands_run"])
    markers = " ".join(payload["observed_markers"])
    assert payload["verdict"] == "plugin-active", payload
    assert checks["plugin_root_exists"] is True, payload
    assert checks["context_cli_works"] is True, payload
    assert checks["hydration_or_review_works"] is True, payload
    assert "map-brief" in commands, payload
    assert "probe-inspect" in commands, payload
    assert "probe-route" in commands, payload
    assert "map_graph_version" in markers, payload
    assert "candidate_probes" in markers, payload
    assert "inspection_is_proof" in markers, payload
    assert "route_is_proof" in markers, payload
    assert "recommended_commands" in markers, payload
