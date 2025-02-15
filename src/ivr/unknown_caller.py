import json
import time
from json import JSONDecodeError
from utils.logger import logger
from stt.azure_stt import recognize_speech_from_file

def handle_unknown_caller(agi, llm, call_id):
    """
    Engage in up to three rounds of conversation with an unknown caller to ascertain intent.
    If no valid intent is derived, apologize and hang up.
    """
    max_retries = 3
    conversation_history = []
    for attempt in range(max_retries):
        agi.verbose("How can we help you?", 3)
        audio_file = f"/tmp/{call_id}_unknown.wav"
        # Record caller response (assuming record_audio is called here or via AGI)
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
            if intent in ["sales_call", "scam_call"]:
                conversation_history.append({"role": "system", "content": structured.get("message", "")})
                if intent == "sales_call":
                    agi.verbose("Sales call detected; hanging up.", 3)
                    agi.hangup()
                    return
                elif intent == "scam_call":
                    agi.verbose("Scam call detected; transferring to scam IVR.", 3)
                    agi.set_variable("TRANSFER_EXTENSION", "scam_ivr")
                    return
            else:
                conversation_history.append({"role": "system", "content": structured.get("message", "Could you please clarify?")})
        except JSONDecodeError:
            agi.verbose("Unable to parse response, please try again.", 3)
    agi.verbose("Sorry, we cannot help with your request. Goodbye!", 3)
    agi.hangup()
