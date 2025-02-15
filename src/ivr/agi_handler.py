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
from prometheus_client import start_http_server, Histogram, Counter
from pybreaker import CircuitBreaker
from anomaly_detector import detect_anomalies  # Assumes an external anomaly detection library is available
import yaml

# Import our modular components.
from call_state import CallFlow, CallState
from session_manager import SessionManager
from rate_limiter import RateLimiter
from audio_util import record_audio
from unknown_caller import handle_unknown_caller  # Existing module for unknown callers.
from allowed_callers import load_allowed_callers, handle_allowed_caller_conversation

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

# --- Circuit Breaker for LLM Calls ---
LLM_BREAKER = CircuitBreaker(
    fail_max=5, 
    reset_timeout=60,
    exclude=[TooManyRequests]
)

# --- Main AGI Handler ---
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
        self.allowed_callers = load_allowed_callers()

    @CALL_DURATION.time()
    def handle_call(self):
        try:
            raw_caller_id = self.agi.env.get('agi_callerid', 'UNKNOWN')
            caller_id = validate_caller_id(raw_caller_id)
            call_id = self.agi.env.get('agi_uniqueid', 'NO_CALL_ID')
            
            # Check if caller is the internal caller.
            my_cli = "+15550000000"  # Replace with your CLI
            if caller_id == my_cli:
                self.agi.verbose("Hello Mr Brown", 3)
                # Internal caller functionality here.
                return

            # For allowed callers, start allowed conversation; otherwise, unknown.
            if caller_id in self.allowed_callers:
                handle_allowed_caller_conversation(self.agi, self.llm, call_id)
                return
            else:
                handle_unknown_caller(self.agi, self.llm, call_id)
                return

            # (If needed, further processing for allowed callers can follow here.)
            
            # Load session state if available.
            session_data = self.session_manager.get_session(call_id)
            if session_data:
                self.state.current_state = session_data.get("current_state", "initial")
                self.state.context = session_data.get("context", {})
                logger.info(f"Loaded session state for call {call_id}")
            
            caller = self.db.get_caller(caller_id)
            if not caller:
                logger.info(f"Caller {caller_id} not found; consider creating a new record.")
            
            # Main IVR loop for allowed callers (if you want to continue conversation).
            while True:
                result = self.agi.get_data('custom-prompt', timeout=5000, maxdigits=1)
                if result and result.digit:
                    self.handle_dtmf(result.digit)
                else:
                    audio_file = f"/tmp/{call_id}_recording.wav"
                    record_audio(self.agi, audio_file)
                    try:
                        from stt.azure_stt import recognize_speech_from_file
                        recognized_text = recognize_speech_from_file(audio_file)
                    except Exception as stt_err:
                        logger.error(f"STT error: {stt_err}")
                        recognized_text = ""
                    if recognized_text:
                        self.handle_speech(recognized_text)
                    else:
                        self.agi.verbose("No speech recognized. Please try again.", 3)
                
                self.session_manager.save_session(call_id, {
                    "current_state": self.state.current_state,
                    "context": self.state.context
                })
                
                if self.agi.env.get('agi_hangup') == 'true':
                    break

                time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error in IVR handler: {e}")
            self.agi.hangup()

    def handle_dtmf(self, digit):
        """Handle DTMF input from the caller."""
        self.db.add_chat_history(
            self.agi.env.get('agi_callerid', 'UNKNOWN'),
            self.agi.env.get('agi_uniqueid', 'NO_CALL_ID'),
            'user',
            f"DTMF input: {digit}"
        )
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

            chat_history = []  # Retrieve historical context as needed.

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
            
            from tts.azure_tts import synthesize_speech_to_file
            tts_output = f"/tmp/{self.agi.env.get('agi_uniqueid', 'NO_CALL_ID')}_tts.wav"
            if synthesize_speech_to_file(response.get('text', ''), tts_output):
                self.agi.stream_file(tts_output)
            
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
            self.agi.verbose(response.get('text', ''), 3)
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
