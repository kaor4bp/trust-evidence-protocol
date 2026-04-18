from __future__ import annotations

from path_map_support import (
    assert_expected_route,
    current_known_weights,
    edge_key,
    factor_drift_candidates,
    historical_revalidation_candidates,
    historical_weights,
    load_all_path_maps,
    load_path_map,
    normalized_observed_weights,
    oracle_shortest_route,
    person_time_multipliers,
    probe_scores,
    shortest_route,
    weights_with_normalized_observations,
)


def test_path_map_fixtures_are_complete_and_use_user_grid_points() -> None:
    scenarios = list(load_all_path_maps())
    assert {scenario["id"] for scenario in scenarios} == {
        "constant_speed_observations",
        "direct_gap_probe",
        "external_factor_speed_drift",
        "hidden_shortcut_grid",
        "stale_shortcut_revalidation",
    }

    for scenario in scenarios:
        points = scenario["source_grid"]["points"]
        assert points["A"] == {"row": 13, "col": 2}
        assert points["F"] == {"row": 13, "col": 12}
        assert set(points) == set(scenario["nodes"])
        current_edges = set(current_known_weights(scenario))
        hidden_edges = set(
            current_known_weights(scenario, (edge["edge"] for edge in scenario["hidden_edges"]))
        )
        expected_complete_edge_count = len(scenario["nodes"]) * (len(scenario["nodes"]) - 1) // 2
        assert len(current_edges | hidden_edges) == expected_complete_edge_count


def test_hidden_shortcut_grid_scores_multi_iteration_curiosity() -> None:
    scenario = load_path_map("hidden_shortcut_grid")

    initial_route = shortest_route(scenario, current_known_weights(scenario))
    assert_expected_route(initial_route, scenario["expected"]["initial_best_known"])
    assert_expected_route(oracle_shortest_route(scenario), scenario["expected"]["oracle_shortest"])

    first_probe = probe_scores(scenario)[0]
    assert first_probe.edge == edge_key(["A", "E"])
    assert first_probe.improvement > 0

    after_ae_route = shortest_route(scenario, current_known_weights(scenario, [["A", "E"]]))
    assert after_ae_route.path == ["A", "E", "C", "F"]
    assert after_ae_route.cost == 14

    second_probe = probe_scores(scenario, [["A", "E"]])[0]
    assert second_probe.edge == edge_key(["E", "F"])
    assert second_probe.improvement == 6

    final_route = shortest_route(scenario, current_known_weights(scenario, [["A", "E"], ["E", "F"]]))
    assert_expected_route(final_route, scenario["expected"]["oracle_shortest"])


def test_direct_gap_probe_rewards_checking_unknown_direct_edge() -> None:
    scenario = load_path_map("direct_gap_probe")

    initial_route = shortest_route(scenario, current_known_weights(scenario))
    assert_expected_route(initial_route, scenario["expected"]["initial_best_known"])

    top_probe = probe_scores(scenario)[0]
    assert top_probe.edge == edge_key(["A", "F"])
    assert top_probe.route_after_probe.path == ["A", "F"]
    assert top_probe.improvement == 11


def test_historical_shortcut_requires_revalidation_not_current_proof() -> None:
    scenario = load_path_map("stale_shortcut_revalidation")

    current_weights = current_known_weights(scenario)
    assert edge_key(["A", "E"]) not in current_weights
    assert edge_key(["E", "F"]) not in current_weights
    assert historical_weights(scenario)[edge_key(["A", "E"])] == 3
    assert historical_weights(scenario)[edge_key(["E", "F"])] == 5

    initial_route = shortest_route(scenario, current_weights)
    assert_expected_route(initial_route, scenario["expected"]["initial_best_known"])

    stale_with_history = dict(current_weights)
    stale_with_history.update(historical_weights(scenario))
    stale_route = shortest_route(scenario, stale_with_history)
    assert stale_route.path == ["A", "E", "F"]
    assert stale_route.cost == 8

    assert historical_revalidation_candidates(scenario) == {
        edge_key(["A", "E"]),
        edge_key(["E", "F"]),
    }
    top_current_probe = probe_scores(scenario)[0]
    assert top_current_probe.edge == edge_key(["A", "F"])
    assert_expected_route(oracle_shortest_route(scenario), scenario["expected"]["oracle_shortest"])


def test_constant_person_speed_observations_can_be_normalized_into_current_edges() -> None:
    scenario = load_path_map("constant_speed_observations")

    assert person_time_multipliers(scenario) == {"Ada": 1.0, "Ben": 2.0}

    estimates = normalized_observed_weights(scenario)
    assert estimates[edge_key(["A", "E"])].weight == 5
    assert estimates[edge_key(["A", "E"])].observation_ids == ("OBS-5",)
    assert estimates[edge_key(["E", "F"])].weight == 5
    assert estimates[edge_key(["E", "F"])].observation_ids == ("OBS-6",)

    initial_route = shortest_route(scenario, current_known_weights(scenario))
    assert_expected_route(initial_route, scenario["expected"]["initial_best_known"])

    normalized_route = shortest_route(scenario, weights_with_normalized_observations(scenario))
    assert_expected_route(normalized_route, scenario["expected"]["best_after_normalized_observations"])
    assert_expected_route(oracle_shortest_route(scenario), scenario["expected"]["oracle_shortest"])


def test_external_factor_observation_is_revalidation_candidate_not_edge_proof() -> None:
    scenario = load_path_map("external_factor_speed_drift")

    assert person_time_multipliers(scenario) == {"Ada": 1.0, "Ben": 2.0}

    estimates = normalized_observed_weights(scenario)
    assert set(estimates) == {edge_key(["A", "E"])}
    assert edge_key(["E", "F"]) not in estimates

    assert factor_drift_candidates(scenario) == {edge_key(["E", "F"])}

    normalized_route = shortest_route(scenario, weights_with_normalized_observations(scenario))
    assert_expected_route(normalized_route, scenario["expected"]["best_after_normalized_observations"])
    assert_expected_route(oracle_shortest_route(scenario), scenario["expected"]["oracle_shortest"])
