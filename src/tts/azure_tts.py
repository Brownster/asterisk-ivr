import os
import azure.cognitiveservices.speech as speechsdk

def synthesize_speech_to_file(text: str, output_file: str) -> bool:
    """
    Synthesize speech from text using Azure Cognitive Services Speech SDK
    and save it to an output file.
    """
    speech_key = os.environ.get('SPEECH_KEY')
    service_region = os.environ.get('SPEECH_REGION')
    if not speech_key or not service_region:
        raise ValueError("SPEECH_KEY and SPEECH_REGION must be set in environment variables")
    
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    # Choose a neural voice (can be made configurable)
    speech_config.speech_synthesis_voice_name = "en-US-AvaMultilingualNeural"
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    
    result = synthesizer.speak_text_async(text).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return True
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        raise Exception(f"Speech synthesis canceled: {cancellation_details.reason} - {cancellation_details.error_details}")
    return False
