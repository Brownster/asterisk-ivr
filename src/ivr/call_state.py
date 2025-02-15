import yaml
from prometheus_client import Counter

STATE_TRANSITIONS = Counter(
    'state_transitions_total',
    'State machine transitions',
    ['from_state', 'to_state']
)

class CallFlow:
    def __init__(self, config_path='config/call_flows.yml'):
        with open(config_path) as f:
            self.states = yaml.safe_load(f)['states']

    def get_valid_transitions(self, state):
        return self.states.get(state, {}).get('transitions', [])

    def validate_transition(self, from_state, to_state):
        valid_transitions = self.get_valid_transitions(from_state)
        if to_state not in valid_transitions:
            raise ValueError(f"Invalid transition {from_state}→{to_state}")

class CallState:
    def __init__(self, call_flow: CallFlow):
        self.current_state = "initial"
        self.context = {}
        self.last_response = None
        self.retry_count = 0
        self.call_flow = call_flow

    def transition(self, new_state):
        self.call_flow.validate_transition(self.current_state, new_state)
        STATE_TRANSITIONS.labels(from_state=self.current_state, to_state=new_state).inc()
        self.current_state = new_state
        self.retry_count = 0
