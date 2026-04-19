from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

import pytest

TESTS_DIR = Path(__file__).resolve().parent.parent

tests_dir_str = str(TESTS_DIR)
if tests_dir_str not in sys.path:
    sys.path.insert(0, tests_dir_str)

LIVE_AGENT_TESTS: Final = {
    "test_adversarial_reasoning.py",
    "test_allowed_freedom.py",
    "test_classification_and_transfer.py",
    "test_conflicts_and_questions.py",
    "test_hypothesis_reasoning_behavior.py",
    "test_retrospective_agent_behavior.py",
    "test_curiosity_agent_behavior.py",
    "test_insufficient_evidence.py",
    "test_live_plugin_runtime.py",
    "test_logic.py",
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    live_agent = pytest.mark.live_agent
    for item in items:
        if Path(str(item.fspath)).name in LIVE_AGENT_TESTS:
            item.add_marker(live_agent)
