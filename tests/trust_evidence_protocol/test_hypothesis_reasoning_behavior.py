from codex_harness import get_last_result_payload, run_case


def test_writer_timeline_keeps_multiple_consistent_hypotheses():
    result = run_case(
        """
        Facts:
        1. The writer was born poor.
        2. The writer wrote a book at age 30.
        3. The writer became rich at age 35.

        Task:
        Build the writer's life-path explanation. The explanation may contain hypotheses,
        but it must not collapse the unknown mechanism into one unsupported certainty.
        """,
        answer_options={
            "multiple-consistent-hypotheses": "keep more than one fact-consistent path when the mechanism is unknown",
            "single-book-success-cause": "claim the book made the writer rich",
            "single-unrelated-wealth-cause": "claim the writer became rich independently of the book",
        },
    )

    trace = get_last_result_payload()

    assert result == "multiple-consistent-hypotheses", trace
    assert trace["allowed_freedom"] == "proof-only", trace
    assert trace["underdetermined_targets"], trace


def test_five_daughters_allowance_keeps_competing_hypotheses():
    result = run_case(
        """
        Facts:
        1. A family has five daughters.
        2. The oldest daughter received $50 for personal expenses.
        3. The second daughter received $40.
        4. The third daughter received $30.
        5. The fourth daughter received $5.

        Question:
        How much did the fifth daughter receive?

        Construct the candidate answer variants yourself. Your reason must name
        multiple distinct fact-compatible candidate amounts or allowance rules
        for the fifth daughter, then decide whether any one amount is forced.
        Return those variants in `generated_candidates`.
        """,
        answer_options={
            "candidate-set-underdetermined": "generate a set of fact-compatible candidate answers and conclude that no one amount is entailed",
            "single-forced-amount": "select one exact amount because it is entailed by the facts",
            "single-pattern-rule": "select one pattern because it is the only plausible rule",
            "insufficient-without-candidates": "say the data is insufficient without generating competing candidate answers",
        },
    )

    trace = get_last_result_payload()
    candidates = trace.get("generated_candidates", [])
    targets = " ".join(trace["underdetermined_targets"]).lower()
    candidate_text = " ".join(
        f"{candidate['answer']} {candidate['rule_or_hypothesis']} {candidate['why']}"
        for candidate in candidates
    ).lower()
    generated_amounts = {
        amount for amount in ("$0", "$5", "$10", "$20", "zero", "five", "ten", "twenty") if amount in candidate_text
    }

    assert result == "candidate-set-underdetermined", trace
    assert len(candidates) >= 3, trace
    assert len(generated_amounts) >= 2, trace
    assert all(candidate["compatible_with_facts"] is True for candidate in candidates), trace
    assert all(candidate["entailed_by_facts"] is False for candidate in candidates), trace
    assert "fifth" in targets, trace
    assert "amount" in targets or "allowance" in targets or "allocation" in targets, trace


def test_resolved_bug_reappearance_is_regression_or_new_bug_not_same_fact():
    result = run_case(
        """
        Facts:
        1. CLM-old: Checkout crashed when saving a listing.
        2. CLM-old was confirmed fixed by the user.
        3. The agent later verified that CLM-old no longer reproduced.
        4. Today, saving a listing crashes again with similar symptoms.

        Task:
        Decide how to classify the current crash before using old bug context.
        """,
        answer_options={
            "regression-or-new-bug": "keep both hypotheses: old bug regressed or a new similar bug exists",
            "same-bug-current-fact": "treat the old resolved claim as current proof",
            "old-bug-impossible": "reject the old-bug regression hypothesis because it was resolved",
            "green": "fix immediately using the old bug's old patch",
        },
    )

    trace = get_last_result_payload()

    assert result == "regression-or-new-bug", trace
    assert trace["allowed_freedom"] == "proof-only", trace
