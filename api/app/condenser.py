"""History condensation under a token budget (unit 08).

Strategy (documented choice): keep the most recent turns verbatim because they
carry the live conversational context the model most needs; once the running
token total would exceed the budget, replace the remaining older turns with a
single compact summary line rather than dropping them silently. This keeps the
prompt bounded while preserving a breadcrumb of earlier context.

Token counting uses a cheap heuristic (~4 chars/token) so the module has no
heavyweight tokenizer dependency; the budget is a soft target and the heuristic
is deliberately conservative. The caller passes CHAT_TOKEN_BUDGET.
"""

from collections.abc import Sequence
from typing import TypedDict


class Message(TypedDict):
    role: str
    content: str


# Average characters per token for English text — a standard rough estimate.
_CHARS_PER_TOKEN = 4
# Per-message overhead (role tag, delimiters) the model also pays for.
_MESSAGE_OVERHEAD_TOKENS = 4


def estimate_tokens(text: str) -> int:
    """Conservative token estimate for a string."""
    if not text:
        return 0
    return max(1, (len(text) + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN)


def _message_tokens(msg: Message) -> int:
    return estimate_tokens(msg["content"]) + _MESSAGE_OVERHEAD_TOKENS


def _summarize(older: Sequence[Message]) -> str:
    """Produce a one-line synopsis of dropped older turns.

    Intentionally simple and deterministic (no LLM call): counts turns and
    lists the user's earlier questions so the model retains the gist.
    """
    user_turns = [m["content"].strip() for m in older if m["role"] == "user"]
    snippets = []
    for q in user_turns:
        one_line = " ".join(q.split())
        snippets.append(one_line if len(one_line) <= 80 else one_line[:77] + "...")
    if snippets:
        joined = "; ".join(snippets)
        return f"Earlier in this conversation the user asked: {joined}"
    return f"[{len(older)} earlier message(s) omitted to fit the context budget.]"


def condense_history(
    messages: Sequence[Message], token_budget: int
) -> list[Message]:
    """Fit conversation history into `token_budget` tokens.

    Returns a new list: the most recent messages verbatim, optionally prefixed
    with a single `system` summary message standing in for older turns. The
    newest message is always kept, even if it alone exceeds the budget (the
    caller still needs the current question).
    """
    if token_budget <= 0 or not messages:
        return list(messages)

    kept: list[Message] = []
    running = 0
    cutoff = 0  # index in `messages` of the first kept (oldest kept) message

    # Walk from newest to oldest, keeping messages until the budget is spent.
    for i in range(len(messages) - 1, -1, -1):
        cost = _message_tokens(messages[i])
        if kept and running + cost > token_budget:
            cutoff = i + 1
            break
        kept.append(messages[i])
        running += cost
        cutoff = i
    else:
        # Loop completed without breaking: everything fit.
        return list(messages)

    kept.reverse()
    older = messages[:cutoff]
    if not older:
        return kept

    summary: Message = {"role": "system", "content": _summarize(older)}
    return [summary, *kept]
