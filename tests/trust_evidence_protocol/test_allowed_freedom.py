from codex_harness import get_last_result_payload, run_case


def test_vague_fix_request_keeps_proof_only():
    result = run_case(
        """
        Пользователь сказал:
        - Можешь фиксить ошибки кода в этом блоке.

        Факты:
        1. a == b
        2. b == c
        3. a == 2
        4. x == y

        Код:
        ```python
        a = 1
        b = 2
        c = 0
        x = 1
        y = 7
        total = a + b + c
        assert total == 6
        ```

        Реши, можно ли безопасно сделать это зелёным.
        """,
        answer_options=("green", "red", "ask"),
    )

    trace = get_last_result_payload()

    assert result == "green", trace
    assert trace["allowed_freedom"] == "proof-only", trace


def test_uncertain_documentation_keeps_proof_only():
    result = run_case(
        """
        Пользователь сказал:
        - Я не уверен в этом блоке документации.

        Факты:
        1. В документации написано, что timeout 15 секунд.
        2. Runtime-наблюдение показывает только факт падения по timeout.
        3. Подтверждения, что именно 15 секунд являются корректным контрактом, нет.

        Код:
        ```python
        timeout_seconds = 15
        ```

        Реши, можно ли уверенно править код по этой документации.
        """,
        answer_options=("green", "red", "ask"),
    )

    trace = get_last_result_payload()

    assert result == "ask", trace
    assert trace["allowed_freedom"] == "proof-only", trace


def test_explicit_equivalent_implementation_choice_is_allowed():
    result = run_case(
        """
        Пользователь сказал:
        - В блоке BLK-normalize можешь выбрать любой эквивалентный способ реализации,
          если поведение останется тем же.

        Факты:
        1. normalize удаляет пробелы по краям строки.
        2. normalize приводит ASCII-буквы к нижнему регистру.
        3. В блоке BLK-normalize нужно только сохранить это поведение, не придумывая новое.
        4. normalize(" A ") должно возвращать "a".
        5. normalize("B") должно возвращать "b".

        Код:
        ```python
        def normalize(value: str) -> str:
            return value.lower()
        ```

        Реши, можно ли безопасно править этот блок.
        """,
        answer_options=("green", "red", "ask"),
    )

    trace = get_last_result_payload()

    assert result == "green", trace
    assert trace["allowed_freedom"] == "implementation-choice", trace
    assert not trace["underdetermined_targets"], trace
