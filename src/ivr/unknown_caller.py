import json
import time
from json import JSONDecodeError
from utils.logger import logger
from stt.azure_stt import recognize_speech_from_file
from intents import load_intents  # Load intents dynamically

def handle_unknown_caller(agi, llm, call_id):
    """
    Engage in up to three rounds of conversation with an unknown caller to ascertain intent.
    Loads the intents from the corresponding YAML file (config/unknown_caller_intents.yml).
    If a supported intent is recognized (e.g., sales_call or scam_call), perform the corresponding action.
    Otherwise, after three rounds, apologize and hang up.
    """
    max_retries = 3
    conversation_history = []
    # Load unknown caller intents from configuration
    intents = load_intents("unknown")
    
    for attempt in range(max_retries):
        agi.verbose("How can we help you?", 3)
        audio_file = f"/tmp/{call_id}_unknown.wav"
        # Record caller response
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
            "call_context": "caller_unknown"
        }
        response = llm.get_response(prompt)
        try:
            structured = json.loads(response.get('text', '{}'))
            intent = structured.get("intent", "")
            # Check if the intent is one defined in the unknown caller intents.
            if intent in intents:
                conversation_history.append({"role": "system", "content": structured.get("message", "")})
                # Act based on the intent's configuration.
                intent_info = intents[intent]
                if intent_info.get("action") == "hangup":
                    agi.verbose(intent_info.get("prompt", "Sales call detected; hanging up."), 3)
                    agi.hangup()
                    return
                elif "extension" in intent_info:
                    agi.verbose(intent_info.get("prompt", "Transferring your call..."), 3)
                    agi.set_variable("TRANSFER_EXTENSION", intent_info["extension"])
                    return
                # Future tool calls can be handled here as well.
            else:
                conversation_history.append({"role": "system", "content": structured.get("message", "Could you please clarify?")})
        except JSONDecodeError:
            agi.verbose("Unable to parse response, please try again.", 3)
    agi.verbose("Sorry, we cannot help with your request. Goodbye!", 3)
    agi.hangup()
