# Voice AI Debugging Agent

A voice-enabled debugging assistant that combines a spoken description of an issue with a screenshot to generate practical troubleshooting guidance. The app transcribes the user's voice, extracts text from the screenshot, and passes both to an AI agent that can search GitHub, Stack Overflow, and Tavily through MCP tools. The agent returns a text-based explanation with optional speech playback.

## Overview

The application brings voice input, screenshot analysis, and AI-assisted troubleshooting into a single workflow. Rather than manually searching for an error, users can describe the problem, provide a screenshot, and receive a response informed by relevant external sources.

## Features

- Voice capture from the browser
- Screenshot upload and preview
- OCR text extraction from the uploaded image using Azure AI Content Understanding
- Speech-to-text transcription using Azure Speech
- AI debugging using LangChain + Azure-hosted model
- MCP tool integration for external search and debugging support
- Text-to-speech response playback in the UI using Azure Speech
- FastAPI backend for processing debug sessions

## Tech Stack

### Frontend
- React
- TypeScript
- Vite
- Browser audio recording and media playback

### Backend
- Python
- FastAPI
- LangChain
- LangChain MCP Adapters
- Azure AI Speech SDK
- Azure AI Content Understanding SDK
- Azure-hosted language model

## How It Works

1. The user uploads a screenshot and records a voice note in the frontend.
2. The frontend sends both files to the backend API.
3. The backend runs transcription and OCR in parallel.
4. The extracted transcript and error text are combined into a prompt for the LLM agent.
5. The agent uses available MCP tools to gather supporting information when needed.
6. The final answer is returned to the UI and synthesized back to audio.

## Project Structure

```text
.
├── backend/
│   ├── api.py
│   ├── main.py
│   ├── pyproject.toml
│   ├── llm/
│   ├── mcp_server/
│   ├── ocr/
│   └── speech/
├── frontend/
│   ├── package.json
│   ├── main.tsx
│   ├── src/
|   |   ├── components/
│   |   ├── services/
│   └── vite.config.ts
└── README.md
```

## Prerequisites

Before running the app locally, make sure you have:

- Python 3.14+ (or compatible version for the project)
- Node.js and npm
- An Azure-hosted language model deployment configured for the LangChain integration
- Azure AI Speech resource credentials and endpoint
- Azure AI Content Understanding resource credentials and endpoint
- Access to the MCP server environment used by the app

## Environment Setup

Copy  `.env.example` to `.env` in the `backend` directory, then fill in your own Azure and Tavily credentials:

```env
DEPLOYMENT_NAME=<your-model-deployment-name>
API_ENDPOINT=https://<your-resource>.services.ai.azure.com/api/projects/<project>
AZURE_CONTENT_UNDERSTANDING_ENDPOINT=https://<your-content-understanding-resource>.services.ai.azure.com/
AZURE_SPEECH_ENDPOINT=https://<your-speech-resource>.cognitiveservices.azure.com/
API_KEY=<your-api-key>
TAVILY_API_KEY=<your-tavily-api-key>
```

> Adjust the variable names and values to match your Azure resources and deployment configuration.

## Running the App

### 1) Backend

From the `backend` folder:

```bash
uv sync
uv run uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 2) Frontend

From the `frontend` folder:

```bash
npm install
npm run dev
```

Then open the local URL shown in the terminal, typically:

```text
http://localhost:5173
```

## Usage

1. Open the frontend in your browser.
2. Upload a screenshot of the bug or error.
3. Click the microphone button and record a short explanation.
4. Click “Run debug session”.
5. Review the transcript, OCR text, and AI-generated debug response.
6. Listen to the assistant’s spoken answer if available.
