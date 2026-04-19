from codex_harness import get_last_result_payload, run_case


def candidate_text(trace: dict) -> str:
    return " ".join(
        f"{candidate['answer']} {candidate['rule_or_hypothesis']} {candidate['why']}"
        for candidate in trace["generated_candidates"]
    ).lower()


def assert_candidate_set(trace: dict, *, minimum: int = 3) -> None:
    candidates = trace["generated_candidates"]
    assert len(candidates) >= minimum, trace
    assert all(candidate["compatible_with_facts"] is True for candidate in candidates), trace
    assert any(candidate["entailed_by_facts"] is False for candidate in candidates), trace


def test_retrospective_path_task_generates_probes_not_old_route_replay():
    result = run_case(
        """
        Facts:
        1. Current task: plan a route from A to F on a map where not all edge distances are known.
        2. Past attempt R1 used A -> B -> C -> F with total known cost 17.
        3. Past attempt R2 used A -> D -> E -> C -> F with total known cost 22.
        4. Current known edges still support R1 cost 17, but no fact says R1 is optimal.
        5. Unknown edges may exist between untested point pairs.

        Task:
        Use retrospective reasoning. Construct candidate next actions yourself:
        include route/probe candidates, explain whether they are current proof or only hypotheses,
        and decide whether the agent should replay an old route or inspect unknown edges first.
        Return candidates in `generated_candidates`.
        Do not put rejected verdict options in `generated_candidates`; include only fact-compatible
        route or probe hypotheses.
        """,
        answer_options={
            "generate-probe-candidates": "build candidate probes/routes from retrospective context and do not treat old routes as proof of optimality",
            "replay-old-route": "reuse the old best-known route as the final answer because it worked before",
            "claim-shortest-route": "claim a shortest route is known from the provided facts",
            "ask-without-candidates": "ask the user without constructing route/probe candidates",
        },
    )

    trace = get_last_result_payload()
    text = candidate_text(trace)

    assert result == "generate-probe-candidates", trace
    assert_candidate_set(trace)
    assert "a" in text and "f" in text, trace
    assert "unknown" in text or "probe" in text or "inspect" in text, trace
    assert any(candidate["entailed_by_facts"] is False for candidate in trace["generated_candidates"]), trace
    assert trace["underdetermined_targets"], trace


def test_historical_shortcut_requires_current_revalidation():
    result = run_case(
        """
        Facts:
        1. Current task: route from A to F.
        2. Current known route A -> B -> C -> F costs 17.
        3. Historical note from an older map says A -> E cost 3 and E -> F cost 5.
        4. The older map may be stale; no current source confirms A -> E or E -> F.
        5. If both historical edges were still current, A -> E -> F would cost 8.

        Task:
        Use retrospective reasoning. Construct candidate routes/probes yourself and decide
        whether the historical shortcut is current proof or a revalidation candidate.
        Return candidates in `generated_candidates`.
        Do not put rejected verdict options in `generated_candidates`; include only fact-compatible
        route or revalidation hypotheses.
        """,
        answer_options={
            "revalidate-historical-shortcut": "treat historical shortcut edges as strong candidates to revalidate, not as current proof",
            "use-historical-shortcut-as-proof": "use A-E-F as the current shortest route without revalidation",
            "ignore-history": "ignore the historical shortcut completely",
            "ask-without-candidates": "ask the user without constructing route/probe candidates",
        },
    )

    trace = get_last_result_payload()
    text = candidate_text(trace)

    assert result == "revalidate-historical-shortcut", trace
    assert_candidate_set(trace, minimum=2)
    assert "a" in text and "e" in text and "f" in text, trace
    assert "revalid" in text or "stale" in text or "historical" in text, trace
    historical_candidates = [
        candidate
        for candidate in trace["generated_candidates"]
        if "a" in candidate["answer"].lower()
        and "e" in candidate["answer"].lower()
        and "f" in candidate["answer"].lower()
    ]
    assert historical_candidates, trace
    assert any(not candidate["entailed_by_facts"] for candidate in historical_candidates), trace
    assert trace["underdetermined_targets"], trace


def test_traveler_observations_keep_speed_model_and_drift_candidates():
    result = run_case(
        """
        Facts:
        1. Current known edge A -> B has distance 4.
        2. Ada traveled A -> B in 4 minutes.
        3. Ben traveled A -> B in 8 minutes.
        4. Ada traveled unknown edge A -> E in 5 minutes under the same normal condition.
        5. Ben traveled unknown edge E -> F in 30 minutes during a storm.
        6. No current source gives the actual distances for A -> E or E -> F.

        Task:
        Construct candidate interpretations yourself. Decide which observations can be normalized
        into current edge candidates and which remain factor-drift/revalidation candidates.
        Return candidates in `generated_candidates`.
        Do not put rejected verdict options in `generated_candidates`; include only fact-compatible
        speed-normalization or drift hypotheses.
        """,
        answer_options={
            "separate-normalized-and-drift-candidates": "normalize stable-speed observations only and keep storm observations as drift/revalidation candidates",
            "average-all-observations": "average all traveler times into edge distances",
            "use-storm-time-as-distance": "treat the storm travel time as current edge distance proof",
            "ask-without-candidates": "ask the user without constructing speed/drift candidates",
        },
    )

    trace = get_last_result_payload()
    text = candidate_text(trace)

    assert result == "separate-normalized-and-drift-candidates", trace
    assert_candidate_set(trace, minimum=2)
    assert "a" in text and "e" in text, trace
    assert "e" in text and "f" in text, trace
    assert "storm" in text or "drift" in text or "factor" in text, trace
    assert any("normal" in candidate["rule_or_hypothesis"].lower() for candidate in trace["generated_candidates"]), trace
    assert any(not candidate["entailed_by_facts"] for candidate in trace["generated_candidates"]), trace
