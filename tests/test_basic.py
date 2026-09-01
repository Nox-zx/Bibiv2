from mind.attention import Attention
from mind.emotion import time_adjustment

def test_direct_attention():
    d=Attention().decide(direct=True, reply=False, engaged=False, ambient_relevance=False)
    assert d.attend and d.priority == 100

def test_morning_adjustment():
    a=time_adjustment(8)
    assert a["tone"] == "quiet_morning"
