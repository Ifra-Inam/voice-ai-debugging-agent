import asyncio
import base64
import os
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from main import run_debugger
from ocr.ocr_setup import extract_text
from speech.stt_setup import transcribe_audio_file
from speech.tts_setup import speak_text

app = FastAPI(title="Voice AI Debugging Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def process_upload(upload: UploadFile, default_suffix: str) -> str:
    suffix = os.path.splitext(upload.filename or "")[1]
    suffix = suffix or default_suffix

    try:
        contents = await upload.read()

        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix
        ) as temp_file:
            temp_file.write(contents)
            temp_path = temp_file.name

    finally:
        await upload.close()

    try:
        return temp_path
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

async def transcribe_audio(upload: UploadFile) -> str:
    path = await process_upload(upload, ".wav")
    try:
        return await asyncio.to_thread(transcribe_audio_file, path)
    finally:
        if os.path.exists(path):
            os.remove(path)

async def extract_error(upload: UploadFile) -> str:
    path = await process_upload(upload, ".png")
    try:
        return await asyncio.to_thread(extract_text, path)
    finally:
        if os.path.exists(path):
            os.remove(path)

async def synthesize_speech(text: str) -> str:
    result = await asyncio.to_thread(speak_text, text)
    audio_data = result.audio_data

    if not audio_data:
        raise RuntimeError("Azure TTS returned no audio.")

    return base64.b64encode(audio_data).decode("utf-8")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/debug")
async def debug(
    audio: UploadFile = File(...),
    screenshot: UploadFile = File(...),
):
    try:
        # Run STT and OCR concurrently
        transcript, error_text = await asyncio.gather(
            transcribe_audio(audio),
            extract_error(screenshot),
        )

        if not transcript.strip():
            raise HTTPException(
                status_code=422,
                detail="No speech was recognized.",
            )

        if not error_text.strip():
            raise HTTPException(
                status_code=422,
                detail="No text could be extracted from the screenshot.",
            )

        # Run the LLM agent and MCP tools
        debug_result = await run_debugger(transcript, error_text)

        # Generate audio for the frontend
        audio_data = await synthesize_speech(debug_result["answer"])

        return {
            "transcript": transcript,
            "error": error_text,
            "answer": debug_result["answer"],
            "audio_data": audio_data,
            "sources": debug_result["sources"],
            "tool_calls": debug_result["tool_calls"],
        }

    except HTTPException:
        raise
    except Exception as exc:
        # Log the full exception on the backend during development
        import logging
        logging.exception("Debugging request failed")

        raise HTTPException(
            status_code=500,
            detail="The debugging request failed. Check the backend logs.",
        ) from exc