from dataclasses import dataclass

@dataclass
class AttentionDecision:
    attend: bool
    priority: int
    reason: str
    direct: bool

class Attention:
    def decide(self, *, direct: bool, reply: bool, engaged: bool, ambient_relevance: bool) -> AttentionDecision:
        if direct:
            return AttentionDecision(True, 100, "direct_address", True)
        if reply:
            return AttentionDecision(True, 95, "reply", True)
        if engaged:
            return AttentionDecision(True, 70, "active_conversation", False)
        if ambient_relevance:
            return AttentionDecision(True, 40, "ambient_relevance", False)
        return AttentionDecision(False, 0, "not_addressed", False)
