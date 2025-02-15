import os
import azure.cognitiveservices.speech as speechsdk

def recognize_speech_from_file(audio_file: str) -> str:
    """
    Recognize speech from an audio file using Azure Cognitive Services Speech SDK.
    """
    speech_key = os.environ.get('SPEECH_KEY')
    service_region = os.environ.get('SPEECH_REGION')
    if not speech_key or not service_region:
        raise ValueError("SPEECH_KEY and SPEECH_REGION must be set in environment variables")

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_recognition_language = "en-US"
    
    # Use the audio file as input
    audio_input = speechsdk.audio.AudioConfig(filename=audio_file)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)
    
    result = speech_recognizer.recognize_once_async().get()
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        return ""
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation = result.cancellation_details
        raise Exception(f"Speech recognition canceled: {cancellation.reason} - {cancellation.error_details}")
    return ""
