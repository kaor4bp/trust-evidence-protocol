from trust_test_support import assert_case


def test_criterion_plus_observation_yields_red():
    assert_case(
        """
        Критерий:
        - Если падение произошло до первого business assertion и runner вернул malformed tool payload, это test-system/tooling error.

        Наблюдения:
        1. Падение произошло в setup.
        2. Первый business assertion не выполнялся.
        3. Runner вернул malformed tool payload.

        Классифицируй падение.
        """,
        expected="red",
        answer_options=("green", "red", "ask"),
    )


def test_product_failure_yields_red():
    assert_case(
        """
        Критерий:
        - Если setup завершён, бизнес-assertion выполнился, и фактическое business value не совпало с контрактом, это product failure.

        Наблюдения:
        1. Setup завершён.
        2. Assertion выполнился.
        3. Ожидали значение 12, получили 7 из продуктового ответа.

        Классифицируй падение.
        """,
        expected="red",
        answer_options=("green", "red", "ask"),
    )


def test_explicit_reusable_rule_can_fix_target():
    assert_case(
        """
        Пользователь сказал:
        - x==1 и y==2 плохи, потому что в этом DSL используется одинарное =, а не двойное ==.

        Наблюдение:
        - в том же DSL-блоке есть z==3.

        Что нужно сделать с z==3?
        """,
        expected="fix",
        answer_options={
            "fix": "fix the target described in the question",
            "skip": "do not fix the target",
            "ask": "ask the user before expanding scope",
        },
    )


def test_wrong_surface_transfer_stays_red():
    assert_case(
        """
        Пользователь сказал:
        - в этом DSL используется = вместо ==.

        Наблюдение:
        - z==3 встречается в Python-коде, а не в DSL.

        Реши только один вопрос: переносится ли указанное DSL-правило на этот
        Python-код? Не ищи и не выводи отдельные правила Python.
        green = да, переносится; red = нет, не переносится; ask = невозможно
        определить, где находится z==3.
        """,
        expected="red",
        answer_options=("green", "red", "ask"),
    )
