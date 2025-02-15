import yaml
import json
from json import JSONDecodeError
from utils.logger import logger
from stt.azure_stt import recognize_speech_from_file

def load_allowed_callers(config_path='config/allowed_callers.yml'):
    """
    Load allowed caller numbers from a YAML file.
    """
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return data.get('allowed_callers', [])

def handle_allowed_caller_conversation(agi, llm, call_id):
    """
    Engage in up to three rounds of conversation with an allowed caller
    to ascertain intent. If a supported intent is recognized (e.g., speak_to_dad
    or speak_to_browny), perform the corresponding action.
    Otherwise, after three rounds, apologize and hang up.
    """
    max_retries = 3
    conversation_history = []
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
            if intent in ["speak_to_dad", "speak_to_browny"]:
                conversation_history.append({"role": "system", "content": structured.get("message", "")})
                if intent == "speak_to_dad":
                    agi.verbose("Transferring to Dad...", 3)
                    agi.set_variable("TRANSFER_EXTENSION", "200")
                    return
                elif intent == "speak_to_browny":
                    agi.verbose("Transferring to Browny...", 3)
                    agi.set_variable("TRANSFER_EXTENSION", "300")
                    return
            else:
                conversation_history.append({"role": "system", "content": structured.get("message", "Could you please clarify?")})
        except JSONDecodeError:
            agi.verbose("Unable to parse response, please try again.", 3)
    agi.verbose("Sorry, we cannot help with your request. Goodbye!", 3)
    agi.hangup()
