import azure.cognitiveservices.speech as speechsdk
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def transcribe_audio_file(audio_path: str) -> str:

    # Set up the speech config using resource endpoint
    endpoint_url = os.getenv("AZURE_SPEECH_ENDPOINT")
    speech_key = os.getenv("API_KEY")

    speech_config = speechsdk.SpeechConfig(
        subscription=speech_key,
        endpoint=endpoint_url
    )

    # Create a recognizer with audio file input 
    audio_config = speechsdk.audio.AudioConfig(filename=audio_path)
    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, 
        audio_config=audio_config
    )

    # Start audio recognition
    result = recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    
    if  result.reason == speechsdk.ResultReason.NoMatch:
        return RuntimeError("No speech could be recognized")

    if  result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        return RuntimeError(f"Speech Recognition canceled: {cancellation_details.reason}, {cancellation_details.error_details}")

    raise RuntimeError("Speech recognition failed.")