import time
import re
import json
from json import JSONDecodeError
import os
from asterisk.agi import AGI
from redis import Redis
from utils.logger import logger
from monitoring import start_monitoring
from call_manager import CallManager
from speech_handler import process_speech, synthesize_response
from llm_handler import LLMHandler
from utils.greetings import select_greeting
from allowed_callers import load_allowed_callers
from unknown_caller import handle_unknown_caller
from db.db import Database

class IVRHandler:
    def __init__(self):
        # Start Prometheus monitoring
        start_monitoring()  # Exposes metrics on port 9100
        
        # Initialize core components
        self.agi = AGI()
        self.redis = Redis(
            host='localhost',
            port=6379,
            db=0,
            password=os.getenv('REDIS_PASSWORD', '')
        )
        self.db = Database()
        self.call_manager = CallManager(self.redis)
        self.llm_handler = LLMHandler()
        
        # Load allowed and owner caller lists from YAML configuration
        self.allowed_callers = load_allowed_callers()  # e.g., from config/allowed_callers.yml
        self.owner_callers = self._load_owner_callers()  # from config/owner_callers.yml
        
        # Retrieve call context from AGI environment
        self.call_id = self.agi.env.get('agi_uniqueid', 'NO_CALL_ID')
        self.caller_id = self._validate_caller_id()
        logger.info(f"Incoming call from {self.caller_id} (Call ID: {self.call_id})")

    def _validate_caller_id(self):
        """Validate and sanitize caller ID."""
        raw_id = self.agi.env.get('agi_callerid', 'UNKNOWN')
        if not re.match(r'^\+?1?\d{10,15}$', raw_id):
            logger.warning(f"Invalid caller ID format: {raw_id}")
            return 'INVALID'
        return raw_id

    def _load_owner_callers(self):
        """Load owner/internal callers from configuration."""
        try:
            import yaml
            with open('config/owner_callers.yml') as f:
                data = yaml.safe_load(f)
            return data.get('owner_callers', [])
        except Exception as e:
            logger.error(f"Error loading owner callers: {e}")
            return []

    def handle_call(self):
        """Main call handling entry point."""
        if self.caller_id == 'INVALID':
            self.agi.verbose("Invalid caller ID. Disconnecting.", 3)
            self.agi.hangup()
            return

        # Route the call based on caller type:
        if self.caller_id in self.owner_callers:
            self._handle_owner_caller()
        elif self.caller_id in self.allowed_callers:
            # For allowed callers, use the allowed conversation flow.
            from allowed_callers import handle_allowed_caller_conversation
            handle_allowed_caller_conversation(self.agi, self.llm_handler, self.call_id, self.caller_id)
        else:
            # For all other callers, use the unknown caller flow.
            from unknown_caller import handle_unknown_caller
            handle_unknown_caller(self.agi, self.llm_handler, self.call_id)
        # End of routing—if further processing is needed, add here.

    def _handle_owner_caller(self):
        """Process internal/owner calls with persistent conversation history."""
        greeting = select_greeting('internal')
        self.agi.verbose(greeting, 3)
        
        # Load previous conversation history from the database.
        history = self.db.get_conversation_history(self.caller_id)
        if history:
            self.agi.verbose("Loaded previous conversation history.", 3)
        else:
            history = []
        
        # Build the prompt with historical context.
        prompt = {
            "caller_id": self.caller_id,
            "chat_history": history,
            "current_input": "",
            "call_context": "internal"
        }
        
        response = self.llm_handler.get_response(prompt)
        try:
            structured = json.loads(response.get('text', '{}'))
            if 'message' in structured:
                self.agi.verbose(structured['message'], 3)
            else:
                self.agi.verbose("Internal call processed.", 3)
        except JSONDecodeError:
            self.agi.verbose("Internal call processed.", 3)

if __name__ == '__main__':
    handler = IVRHandler()
    handler.handle_call()
