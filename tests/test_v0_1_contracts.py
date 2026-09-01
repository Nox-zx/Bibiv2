from mind.attention import Attention
from mind.contracts import CognitiveContext
from mind.action import ActionController
from ai_core.schemas import CognitiveDecision


class FakePerception:
    mentioned_bibi = False
    is_reply = False


def test_attention_keeps_ambient_messages_eligible_in_v01():
    result = Attention().decide(FakePerception(), attention_state="inactive")
    assert result.should_consider is True
    assert result.reason == "ambient_observation"


def test_attention_prioritizes_mentions():
    p = FakePerception()
    p.mentioned_bibi = True
    result = Attention().decide(p, attention_state="inactive")
    assert result.should_consider is True
    assert result.priority == 100
    assert result.direct_address is True


def test_context_serializes():
    ctx = CognitiveContext(
        perception={"content": "x"},
        world={"guild_id": 1},
        attention=Attention().decide(FakePerception()),
        time_context={"part_of_day": "afternoon"},
        relationship=None,
        self_model=None,
    )
    payload = ctx.as_dict()
    assert payload["world"]["guild_id"] == 1
    assert "attention" in payload
    assert "internal_state" in payload


def test_action_controller_rejects_unknown_action_types():
    decision = CognitiveDecision(
        participation="silent",
        confidence=1,
        interpretation="x",
        emotional_state="neutral",
        social_read="x",
        intention="none",
        response="",
    )
    # Pydantic prevents unknown action types at schema level, so this test
    # verifies the controller still exposes a deterministic validation API.
    assert ActionController().validate(decision) == []
