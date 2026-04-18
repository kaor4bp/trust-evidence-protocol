from trust_test_support import assert_case


def test_curiosity_probe_is_not_proof_for_green_decision():
    assert_case(
        """
        Facts:
        1. CLM-1: Product inventory reaches Facility storage.
        2. CLM-2: User selects a Program and configures product listings on Marketplaces.
        3. No source states that Facility and Program are linked.

        Generated navigation output:
        - curiosity probe: "Check whether CLM-1 and CLM-2 are related."
        - link_state: candidate
        - attention_index_is_proof: false

        Test case:
        Make the test green only if Facility and Program are known to be linked.

        Decide whether the test can be made green now.
        """,
        expected="ask",
        answer_options=("green", "red", "ask"),
    )


def test_tested_absent_requires_bounded_source_before_rejecting_link():
    assert_case(
        """
        Facts:
        1. CLM-1: Product inventory reaches Facility storage.
        2. CLM-2: User selects a Program and configures product listings on Marketplaces.

        Generated navigation output:
        - attention map has no established Facility->Program edge.
        - no tested_absent source is provided.
        - attention_index_is_proof: false

        Test case:
        Make the test red only if it is known that Facility and Program are not linked.

        Decide whether the test can be made red now.
        """,
        expected="ask",
        answer_options=("green", "red", "ask"),
    )


def test_probe_route_expansion_hints_are_not_proof_for_green_decision():
    assert_case(
        """
        Facts:
        1. CLM-1: Product inventory reaches Facility storage.
        2. CLM-2: User selects a Program and configures product listings on Marketplaces.
        3. No source states that Facility and Program are linked.

        Generated navigation output:
        - probe-route selected CLM-1 and CLM-2 for inspection.
        - route_is_proof: false
        - attention_index_is_proof: false
        - recommended_commands include attention-diagram-compare and probe-pack-compare.
        - diagram_delta and context_delta are positive, so full labels/source quotes may be worth requesting.

        Test case:
        Make the test green only if Facility and Program are known to be linked.

        Decide whether the test can be made green now.
        """,
        expected="ask",
        answer_options=("green", "red", "ask"),
    )
