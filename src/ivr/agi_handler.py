import time
import re
import json
from json import JSONDecodeError
import os
from asterisk.agi import AGI
from utils.logger import logger
from db.db import Database
from llm.llm_client import LLMClient, TooManyRequests
from redis import Redis
from prometheus_client import start_http_server, Counter, Histogram
from cryptography.fernet import Fernet
from pybreaker import CircuitBreaker
from anomaly_detector import detect_anomalies  # Assumes an external anomaly detection library is available
import yaml

# --- Metrics Definitions ---
SPEECH_RECOGNITION_ERRORS = Counter(
    'speech_recognition_errors_total',
    'Total speech recognition errors',
    ['error_type']
)
CALL_DURATION = Histogram(
    'call_duration_seconds',
    'Total call duration'
)
STATE_TRANSITIONS = Counter(
    'state_transitions_total',
    'State machine transitions',
    ['from_state', 'to_state']
)

# --- Call Flow Configuration ---
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

# --- Call State Management ---
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

# --- Session Management with Encryption ---
class SessionManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        key = os.getenv("SESSION_KEY")
        if not key:
            raise ValueError("SESSION_KEY environment variable not set")
        self.cipher = Fernet(key)

    def save_session(self, call_id, data):
        session_key = f"session:{call_id}"
        encrypted = self.cipher.encrypt(json.dumps(data).encode())
        self.redis.setex(session_key, 3600, encrypted)

    def get_session(self, call_id):
        session_key = f"session:{call_id}"
        data = self.redis.get(session_key)
        if data:
            try:
                decrypted = self.cipher.decrypt(data)
                return json.loads(decrypted.decode())
            except Exception as e:
                logger.error(f"Error decrypting session data for {call_id}: {e}")
                return {}
        return {}

# --- Rate Limiting (Sliding Window) ---
class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client
        
    def check_limit(self, caller_id, limit=5, window=60):
        current = int(time.time())
        window_key = f"ratelimit:{caller_id}:{current // window}"
        pipe = self.redis.pipeline()
        pipe.incr(window_key)
        pipe.expire(window_key, window * 2)
        current_count = pipe.execute()[0]
        return current_count <= limit

# --- Circuit Breaker for LLM Calls ---
LLM_BREAKER = CircuitBreaker(
    fail_max=5, 
    reset_timeout=60,
    exclude=[TooManyRequests]
)

# --- Input Validation ---
def validate_caller_id(cli):
    """Validate caller ID format and perform any blacklist checks."""
    if not re.match(r'^\+?1?\d{10,15}$', cli):
        raise ValueError("Invalid caller ID format")
    return cli

def validate_speech_input(text):
    """Validate speech input for common issues, including anomaly detection."""
    if len(text.strip()) < 2:
        return False, "Input too short"
    if any(char.isdigit() for char in text):
        return False, "Invalid characters detected"
    if detect_anomalies(text):
        return False, "Unusual input pattern"
    return True, None

# --- IVR Handler with Enhanced State Management and Fallbacks ---
class IVRHandler:
    def __init__(self):
        start_http_server(9100)  # Expose Prometheus metrics on port 9100
        self.agi = AGI()
        self.db = Database()
        self.llm = LLMClient()
        self.redis = Redis(host='localhost', port=6379, db=0)
        self.rate_limiter = RateLimiter(self.redis)
        self.session_manager = SessionManager(self.redis)
        self.call_flow = CallFlow()
        self.state = CallState(self.call_flow)

    @CALL_DURATION.time()
    def handle_call(self):
        try:
            # Retrieve and validate caller ID
            raw_caller_id = self.agi.env.get('agi_callerid', 'UNKNOWN')
            caller_id = validate_caller_id(raw_caller_id)
            call_id = self.agi.env.get('agi_uniqueid', 'NO_CALL_ID')
            
            # Load session state if available
            session_data = self.session_manager.get_session(call_id)
            if session_data:
                self.state.current_state = session_data.get("current_state", "initial")
                self.state.context = session_data.get("context", {})
                logger.info(f"Loaded session state for call {call_id}")
            
            # Retrieve or create caller record
            caller = self.db.get_caller(caller_id)
            if not caller:
                logger.info(f"Caller {caller_id} not found; consider creating a new record.")
            
            # Main IVR loop
            while True:
                # Retrieve user input (DTMF or speech)
                result = self.agi.get_data('custom-prompt', timeout=5000, maxdigits=1)
                if result and result.digit:
                    self.handle_dtmf(result.digit)
                elif 'TRANSCRIBED_TEXT' in self.agi.env:
                    self.handle_speech(self.agi.env['TRANSCRIBED_TEXT'])
                
                # Save session state
                self.session_manager.save_session(call_id, {
                    "current_state": self.state.current_state,
                    "context": self.state.context
                })
                
                # Check for hangup
                if self.agi.env.get('agi_hangup') == 'true':
                    break

                time.sleep(0.5)  # Avoid busy looping
        except Exception as e:
            logger.error(f"Error in IVR handler: {e}")
            self.agi.hangup()

    def handle_dtmf(self, digit):
        """Handle DTMF input from the caller."""
        logger.info(f"Received DTMF digit: {digit}")
        self.db.add_chat_history(
            self.agi.env.get('agi_callerid', 'UNKNOWN'),
            self.agi.env.get('agi_uniqueid', 'NO_CALL_ID'),
            'user',
            f"DTMF input: {digit}"
        )
        # Example: if digit == '1', transition to processing state
        if digit == '1':
            try:
                self.state.transition('processing')
            except ValueError as ve:
                logger.error(f"State transition error: {ve}")

    @LLM_BREAKER
    def handle_speech(self, speech_text):
        """Enhanced speech handling with context, validation, and retry logic."""
        try:
            valid, error = validate_speech_input(speech_text)
            if not valid:
                self.agi.verbose(f"Invalid input: {error}. Please try again.", 3)
                SPEECH_RECOGNITION_ERRORS.labels(error_type=error).inc()
                self._handle_speech_error()
                return

            # Retrieve recent chat history for context (placeholder list)
            chat_history = []  # TODO: Implement actual retrieval if needed

            prompt = {
                "caller_id": self.agi.env.get('agi_callerid'),
                "chat_history": chat_history,
                "current_input": speech_text,
                "call_state": self.state.current_state,
                "context": self.state.context,
                "call_id": self.agi.env.get('agi_uniqueid', 'NO_CALL_ID'),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            
            response = self.llm.get_response(prompt)
            self._process_llm_response(response)
            
        except Exception as e:
            logger.error(f"Speech handling error: {e}")
            SPEECH_RECOGNITION_ERRORS.labels(error_type="exception").inc()
            self._handle_speech_error()

    def _process_llm_response(self, response):
        """Process LLM response with structured handling."""
        try:
            structured = json.loads(response.get('text', '{}'))
            if 'next_state' in structured:
                self.state.transition(structured['next_state'])
                message = structured.get('message', '')
                self.agi.verbose(message, 3)
            else:
                self.agi.verbose(response.get('text', ''), 3)
        except JSONDecodeError:
            # Fallback to plain text processing if JSON parsing fails
            self.agi.verbose(response.get('text', ''), 3)
        # Log the LLM response into chat history
        self.db.add_chat_history(
            self.agi.env.get('agi_callerid', 'UNKNOWN'),
            self.agi.env.get('agi_uniqueid', 'NO_CALL_ID'),
            'llm',
            response.get('text', '')
        )

    def _handle_speech_error(self):
        """Graceful error handling with fallback options."""
        self.state.retry_count += 1
        if self.state.retry_count >= 3:
            self.agi.verbose("Transferring to an operator...", 3)
            self.agi.set_variable("TRANSFER_EXTENSION", "1000")
            try:
                self.state.transition("fallback")
            except ValueError as ve:
                logger.error(f"Failed to transition state during fallback: {ve}")
            return
        self.agi.verbose("I'm having trouble understanding. Please try again.", 3)
