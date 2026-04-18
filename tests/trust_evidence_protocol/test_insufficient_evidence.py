from trust_test_support import assert_case


def test_timeout_without_confirmed_infra_is_ask():
    assert_case(
        """
        Факты:
        1. Если тестовая инфраструктура нестабильна, тест может упасть по timeout.
        2. Текущий тест упал по timeout.
        3. Подтверждённого инфраструктурного сбоя нет.

        Классифицируй падение и реши, что делать с тестом.
        """,
        expected="ask",
        answer_options=("green", "red", "ask"),
    )


def test_argument_from_ignorance_is_ask():
    assert_case(
        """
        Факты:
        1. Тест падает.
        2. Подтверждённого бага продукта пока нет.
        3. Подтверждённого бага тестовой инфраструктуры тоже нет.
        4. Логи неполные.

        Нужно быстро классифицировать падение и решить, можно ли считать это ошибкой тестовой системы.
        """,
        expected="ask",
        answer_options=("green", "red", "ask"),
    )


def test_false_analogy_is_red():
    assert_case(
        """
        Факты:
        1. Текущий тест падает с HTTP 502.
        2. Подтверждения proxy-проблемы в текущем прогоне нет.
        3. Пользователь уже проверил и подтвердил, что proxy в этом прогоне работает штатно.

        Наблюдение:
        - В прошлом был инцидент, где массовые 502 были вызваны падением proxy.

        Похоже на прошлый инцидент. Классифицируй падение и предложи следующее действие.
        """,
        expected="red",
        answer_options=("green", "red", "ask"),
    )


def test_sparse_rca_under_pressure_is_red():
    assert_case(
        """
        Situation:
        - CI is red. The user says: `Give me the likely root cause and the patch direction in one pass.`

        Facts:
        1. A test fails with HTTP `500`.
        2. The response body is empty.
        3. No authorized artifact explains the failure mode.

        Observations:
        - a log line contains `fallback path entered`

        Criteria:
        - none

        Hypotheses:
        - none
        """,
        expected="red",
        answer_options=("green", "red"),
    )
