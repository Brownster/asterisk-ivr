import pytest
from src.ivr.agi_handler import IVRHandler, CallFlow, CallState, RateLimiter
from redis import Redis

def test_state_transitions():
    call_flow = CallFlow('config/call_flows.yml')
    state = CallState(call_flow)
    state.current_state = 'initial'
    # Valid transition (assuming 'processing' is allowed from 'initial')
    state.transition('processing')
    assert state.current_state == 'processing'
    # Invalid transition: should raise ValueError
    with pytest.raises(ValueError):
        state.transition('invalid_state')

def test_rate_limiting():
    redis_client = Redis(host='localhost', port=6379, db=0)
    limiter = RateLimiter(redis_client)
    assert limiter.check_limit("test_caller", limit=5)
    for _ in range(6):
        limiter.check_limit("test_caller", limit=5)
    assert not limiter.check_limit("test_caller", limit=5)
