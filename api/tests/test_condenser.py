from app.condenser import (
    Message,
    condense_history,
    estimate_tokens,
)


def _msg(role: str, content: str) -> Message:
    return {"role": role, "content": content}


def _total_tokens(messages: list[Message]) -> int:
    return sum(estimate_tokens(m["content"]) + 4 for m in messages)


def test_short_history_passes_through_unchanged():
    history = [
        _msg("user", "Hello"),
        _msg("assistant", "Hi there"),
        _msg("user", "How are you?"),
    ]
    assert condense_history(history, token_budget=1000) == history


def test_empty_history_returns_empty():
    assert condense_history([], token_budget=1000) == []


def test_long_conversation_stays_under_budget():
    # 40 turns of ~100-char messages — comfortably over a tight budget.
    history = [
        _msg("user" if i % 2 == 0 else "assistant", f"Message number {i} " + "x" * 100)
        for i in range(40)
    ]
    budget = 200
    condensed = condense_history(history, token_budget=budget)

    # The result must fit the budget (the summary line is small and counted).
    assert _total_tokens(condensed) <= budget + estimate_tokens(condensed[0]["content"]) + 4
    # It must be materially shorter than the input.
    assert len(condensed) < len(history)


def test_recent_messages_kept_verbatim():
    history = [_msg("user", f"old question {i}") for i in range(10)]
    history.append(_msg("user", "the newest and most important question"))
    condensed = condense_history(history, token_budget=60)

    # Newest message survives verbatim as the last entry.
    assert condensed[-1]["content"] == "the newest and most important question"


def test_older_turns_replaced_by_single_summary():
    history = [
        _msg("user", "first question about cats " + "a" * 200),
        _msg("assistant", "answer about cats " + "b" * 200),
        _msg("user", "second question about dogs " + "c" * 200),
        _msg("assistant", "answer about dogs " + "d" * 200),
        _msg("user", "recent question"),
    ]
    condensed = condense_history(history, token_budget=40)

    # First entry is a system summary standing in for dropped older turns.
    assert condensed[0]["role"] == "system"
    assert "earlier" in condensed[0]["content"].lower()
    # Only one summary line, not many.
    assert sum(1 for m in condensed if m["role"] == "system") == 1


def test_newest_message_kept_even_if_alone_over_budget():
    history = [_msg("user", "z" * 10_000)]
    condensed = condense_history(history, token_budget=10)
    assert condensed == history


def test_zero_budget_returns_input_unchanged():
    history = [_msg("user", "anything")]
    assert condense_history(history, token_budget=0) == history
