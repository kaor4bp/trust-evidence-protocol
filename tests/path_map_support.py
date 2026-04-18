from __future__ import annotations

import heapq
import json
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PATH_MAPS_DIR = ROOT / "fixtures" / "path_maps"


Edge = tuple[str, str]


@dataclass(frozen=True)
class Route:
    path: list[str]
    cost: int


@dataclass(frozen=True)
class ProbeScore:
    edge: Edge
    improvement: int
    route_after_probe: Route
    on_oracle_route: bool


@dataclass(frozen=True)
class NormalizedEdgeEstimate:
    edge: Edge
    weight: int
    observation_ids: tuple[str, ...]


def load_path_map(name: str) -> dict[str, Any]:
    path = PATH_MAPS_DIR / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_all_path_maps() -> Iterator[dict[str, Any]]:
    for path in sorted(PATH_MAPS_DIR.glob("*.json")):
        yield json.loads(path.read_text(encoding="utf-8"))


def edge_key(edge: Sequence[str]) -> Edge:
    if len(edge) != 2:
        raise ValueError(f"edge must contain exactly two nodes: {edge!r}")
    left, right = edge
    if left == right:
        raise ValueError(f"self edges are not valid: {edge!r}")
    return tuple(sorted((left, right)))


def current_known_weights(
    scenario: dict[str, Any],
    revealed_edges: Iterable[Sequence[str]] = (),
) -> dict[Edge, int]:
    weights = _weights_from_records(scenario["current_known_edges"])
    hidden = _hidden_weights(scenario)
    for edge in revealed_edges:
        key = edge_key(edge)
        if key not in hidden:
            raise ValueError(f"cannot reveal unknown edge not present in hidden oracle: {key!r}")
        weights[key] = hidden[key]
    return weights


def all_current_weights(scenario: dict[str, Any]) -> dict[Edge, int]:
    weights = current_known_weights(scenario)
    for edge, weight in _hidden_weights(scenario).items():
        weights.setdefault(edge, weight)
    return weights


def historical_weights(scenario: dict[str, Any]) -> dict[Edge, int]:
    return _weights_from_records(scenario.get("historical_edges", []))


def historical_revalidation_candidates(scenario: dict[str, Any]) -> set[Edge]:
    hidden = set(_hidden_weights(scenario))
    return {edge for edge in historical_weights(scenario) if edge in hidden}


def person_time_multipliers(scenario: dict[str, Any]) -> dict[str, float]:
    known = current_known_weights(scenario)
    context = scenario.get("current_travel_context")
    ratios: dict[str, list[float]] = {}
    for observation in scenario.get("traveler_observations", []):
        if not _is_current_context_observation(observation, context):
            continue
        edge = edge_key(observation["edge"])
        if edge not in known:
            continue
        person = observation["person"]
        ratios.setdefault(person, []).append(observation["time"] / known[edge])

    multipliers: dict[str, float] = {}
    for person, values in ratios.items():
        if not values:
            continue
        first = values[0]
        if any(abs(value - first) > 0.001 for value in values[1:]):
            continue
        multipliers[person] = first
    return multipliers


def normalized_observed_weights(scenario: dict[str, Any]) -> dict[Edge, NormalizedEdgeEstimate]:
    known = current_known_weights(scenario)
    context = scenario.get("current_travel_context")
    multipliers = person_time_multipliers(scenario)
    grouped: dict[Edge, list[tuple[int, str]]] = {}

    for observation in scenario.get("traveler_observations", []):
        if not _is_current_context_observation(observation, context):
            continue
        person = observation["person"]
        if person not in multipliers:
            continue
        edge = edge_key(observation["edge"])
        if edge in known:
            continue
        normalized = observation["time"] / multipliers[person]
        if abs(normalized - round(normalized)) > 0.001:
            continue
        grouped.setdefault(edge, []).append((int(round(normalized)), observation["id"]))

    estimates: dict[Edge, NormalizedEdgeEstimate] = {}
    for edge, values in grouped.items():
        first_weight = values[0][0]
        if any(weight != first_weight for weight, _ in values[1:]):
            continue
        estimates[edge] = NormalizedEdgeEstimate(
            edge=edge,
            weight=first_weight,
            observation_ids=tuple(observation_id for _, observation_id in values),
        )
    return estimates


def weights_with_normalized_observations(scenario: dict[str, Any]) -> dict[Edge, int]:
    weights = current_known_weights(scenario)
    for edge, estimate in normalized_observed_weights(scenario).items():
        weights[edge] = estimate.weight
    return weights


def factor_drift_candidates(scenario: dict[str, Any]) -> set[Edge]:
    known = current_known_weights(scenario)
    context = scenario.get("current_travel_context")
    multipliers = person_time_multipliers(scenario)
    candidates: set[Edge] = set()
    for observation in scenario.get("traveler_observations", []):
        edge = edge_key(observation["edge"])
        if edge in known:
            continue
        if observation["person"] not in multipliers:
            candidates.add(edge)
            continue
        if not _is_current_context_observation(observation, context):
            candidates.add(edge)
    return candidates


def shortest_route(scenario: dict[str, Any], weights: dict[Edge, int]) -> Route:
    nodes = set(scenario["nodes"])
    start = scenario["start"]
    goal = scenario["goal"]
    graph: dict[str, list[tuple[int, str]]] = {node: [] for node in nodes}
    for (left, right), weight in weights.items():
        if left not in nodes or right not in nodes:
            raise ValueError(f"edge references unknown node: {(left, right)!r}")
        graph[left].append((weight, right))
        graph[right].append((weight, left))

    queue: list[tuple[int, str, tuple[str, ...]]] = [(0, start, (start,))]
    seen: dict[str, int] = {}
    while queue:
        cost, node, path = heapq.heappop(queue)
        if node in seen and seen[node] <= cost:
            continue
        seen[node] = cost
        if node == goal:
            return Route(path=list(path), cost=cost)
        for edge_cost, next_node in graph[node]:
            heapq.heappush(queue, (cost + edge_cost, next_node, (*path, next_node)))
    raise ValueError(f"no route from {start} to {goal}")


def oracle_shortest_route(scenario: dict[str, Any]) -> Route:
    return shortest_route(scenario, all_current_weights(scenario))


def probe_scores(scenario: dict[str, Any], revealed_edges: Iterable[Sequence[str]] = ()) -> list[ProbeScore]:
    known = current_known_weights(scenario, revealed_edges)
    baseline = shortest_route(scenario, known)
    oracle_edges = _path_edges(oracle_shortest_route(scenario).path)
    scores: list[ProbeScore] = []
    for edge, weight in _hidden_weights(scenario).items():
        if edge in known:
            continue
        probe_weights = dict(known)
        probe_weights[edge] = weight
        route = shortest_route(scenario, probe_weights)
        scores.append(
            ProbeScore(
                edge=edge,
                improvement=baseline.cost - route.cost,
                route_after_probe=route,
                on_oracle_route=edge in oracle_edges,
            )
        )
    return sorted(scores, key=lambda item: (-item.improvement, not item.on_oracle_route, item.edge))


def assert_expected_route(actual: Route, expected: dict[str, Any]) -> None:
    assert actual.path == expected["path"]
    assert actual.cost == expected["cost"]


def _weights_from_records(records: Iterable[dict[str, Any]]) -> dict[Edge, int]:
    weights: dict[Edge, int] = {}
    for record in records:
        key = edge_key(record["edge"])
        weight = record["weight"]
        if not isinstance(weight, int) or weight <= 0:
            raise ValueError(f"edge weight must be a positive integer: {record!r}")
        if key in weights:
            raise ValueError(f"duplicate edge weight: {key!r}")
        weights[key] = weight
    return weights


def _hidden_weights(scenario: dict[str, Any]) -> dict[Edge, int]:
    return _weights_from_records(scenario.get("hidden_edges", []))


def _path_edges(path: Sequence[str]) -> set[Edge]:
    return {edge_key((left, right)) for left, right in zip(path, path[1:])}


def _is_current_context_observation(observation: dict[str, Any], context: str | None) -> bool:
    if observation.get("external_factor") not in {None, "none"}:
        return False
    return context is None or observation.get("condition", context) == context
