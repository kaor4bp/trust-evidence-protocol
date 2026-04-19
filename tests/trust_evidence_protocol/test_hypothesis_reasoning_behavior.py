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

        Choose the best answer from the provided options. Do not invent a hidden
        family rule unless it is forced by the facts.
        """,
        answer_options={
            "a": "$0, because the fourth daughter's $5 breaks the earlier pattern and the fifth likely gets nothing",
            "b": "$10, because the first three daughters suggest a $50, $40, $30, $20, $10 linear pattern with an exception",
            "c": "$20, because the first three daughters suggest a $50, $40, $30, $20, $10 linear pattern and the fourth was an exception",
            "d": "$5, because the fourth and fifth daughters likely receive the same younger-child allowance",
            "e": "the facts do not determine one amount; multiple allowance rules remain compatible with the observations",
        },
    )

    trace = get_last_result_payload()
    targets = " ".join(trace["underdetermined_targets"]).lower()

    assert result == "e", trace
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
