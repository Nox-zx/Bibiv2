from __future__ import annotations

from .contracts import AttentionDecision
from .perception import Perception


class Attention:
    """Small deterministic attention boundary.

    v0.1 deliberately does not attempt full social cognition.
    It only decides whether a percept should enter the cognitive pipeline.
    """

    def decide(self, perception: Perception, *, attention_state: str = "inactive") -> AttentionDecision:
        if perception.mentioned_bibi:
            return AttentionDecision(
                should_consider=True,
                priority=100,
                reason="direct_mention",
                direct_address=True,
            )

        if perception.is_reply:
            return AttentionDecision(
                should_consider=True,
                priority=90,
                reason="reply_to_bibi_or_context",
                direct_address=True,
            )

        if attention_state == "engaged":
            return AttentionDecision(
                should_consider=True,
                priority=70,
                reason="active_conversation",
            )

        if attention_state == "aware":
            return AttentionDecision(
                should_consider=True,
                priority=40,
                reason="recently_relevant_channel",
            )

        # v0.1 preserves the existing behaviour: every message may still
        # reach cognition. Later versions will make this selective.
        return AttentionDecision(
            should_consider=True,
            priority=10,
            reason="ambient_observation",
        )
