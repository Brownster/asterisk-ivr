import yaml
import json
from json import JSONDecodeError
from utils.logger import logger
from stt.azure_stt import recognize_speech_from_file
from intents import load_intents  # Load intents dynamically

def load_allowed_callers(config_path='config/allowed_callers.yml'):
    """
    Load allowed caller numbers from a YAML file.
    """
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return data.get('allowed_callers', [])

def handle_allowed_caller_conversation(agi, llm, call_id, conversation_history=None):
    """
    Engage in up to three rounds of conversation with an allowed caller
    to ascertain intent using intents loaded from configuration.
    Any existing conversation history (e.g., from previous calls) can be passed in
    so that the LLM prompt includes that context.
    
    If a supported intent is recognized (e.g., speak_to_dad or speak_to_browny),
    perform the corresponding action. Otherwise, after three rounds, apologize and hang up.
    """
    max_retries = 3
    if conversation_history is None:
        conversation_history = []
    
    # Load allowed caller intents (e.g., from config/known_caller_intents.yml)
    intents = load_intents("known")
    
    for attempt in range(max_retries):
        agi.verbose("How can we help you today? Please state your request.", 3)
        audio_file = f"/tmp/{call_id}_allowed.wav"
        # Record caller's response.
        agi.record_file(audio_file, "wav", 5000, "#", 3)
        try:
            recognized_text = recognize_speech_from_file(audio_file)
        except Exception as stt_err:
            logger.error(f"STT error: {stt_err}")
            recognized_text = ""
        if not recognized_text:
            agi.verbose("No speech recognized, please try again.", 3)
            continue
        conversation_history.append({"role": "user", "content": recognized_text})
        prompt = {
            "caller_id": agi.env.get('agi_callerid'),
            "chat_history": conversation_history,
            "current_input": recognized_text,
            "call_context": "caller_allowed"
        }
        response = llm.get_response(prompt)
        try:
            structured = json.loads(response.get('text', '{}'))
            intent = structured.get("intent", "")
            # Check if the recognized intent is among those defined for known callers.
            if intent in intents:
                conversation_history.append({"role": "system", "content": structured.get("message", "")})
                # Use the extension or action defined in the intents file.
                intent_info = intents[intent]
                if "extension" in intent_info:
                    agi.verbose(intent_info.get("prompt", "Transferring your call..."), 3)
                    agi.set_variable("TRANSFER_EXTENSION", intent_info["extension"])
                    return
                elif intent_info.get("action") == "hangup":
                    agi.verbose(intent_info.get("prompt", "Goodbye."), 3)
                    agi.hangup()
                    return
                # Future tool calls can be processed here.
            else:
                conversation_history.append({"role": "system", "content": structured.get("message", "Could you please clarify?")})
        except JSONDecodeError:
            agi.verbose("Unable to parse response, please try again.", 3)
    agi.verbose("Sorry, we cannot help with your request. Goodbye!", 3)
    agi.hangup()
