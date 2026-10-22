import truststore
truststore.inject_into_ssl()

import os 
from pathlib import Path
from urllib.parse import urlparse
from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.ai.contentunderstanding.models import AnalysisInput, AnalysisResult
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

def is_absolute_url(value: str) -> bool:
    parsed_url = urlparse(value)
    return bool(parsed_url.scheme and parsed_url.netloc)


def extract_text(image_path: str) -> str:
    # Insert the following configurations.
    # 1) AZURE_CONTENT_UNDERSTANDING_ENDPOINT - the endpoint to your Content Understanding resource.
    endpoint = os.getenv("AZURE_CONTENT_UNDERSTANDING_ENDPOINT")

    # 2) CONTENT_UNDERSTANDING_KEY - your Content Understanding API key (optional if using DefaultAzureCredential).
    key = os.getenv("API_KEY")

    # 3) FILE_URL - you can replace this with your own URL. [Note: Local file instead of a URL]
    file_path = Path(image_path)   # or "./images/scan.png"

    # ANALYZER_ID - the ID of the analyzer to use.
    analyzer_id = "prebuilt-read"

    # API_VERSION - the API version to use.
    api_version = "2026-06-01-preview"

    # Validate Endpoint
    if not endpoint or not is_absolute_url(endpoint):
        raise RuntimeError("Invalid or missing Azure Content Understanding endpoint.")

    if not file_path.is_file():
        raise FileNotFoundError(f"Image not found: {file_path.resolve()}")

    # Set up Content Understanding client.
    hasKey = type(key) is str and bool(key.strip())
    credential = AzureKeyCredential(key) if hasKey else DefaultAzureCredential()
    client = ContentUnderstandingClient(endpoint=endpoint, credential=credential, api_version=api_version)

    # [START analyze]
    print(f"Analyzing with {analyzer_id} analyzer...")
    print(f"  File: {file_path}\n")

    try:
        poller = client.begin_analyze_binary(
            analyzer_id=analyzer_id,
            binary_input=file_path.read_bytes(),
        )
        result: AnalysisResult = poller.result()
    except AzureError as err:
        raise RuntimeError(f"Azure OCR failed: {err}") from err
    except Exception as ex:
        raise RuntimeError(f"Unexpected error occurred: {ex}") from ex
    # [END analyze]

    # [START output_result]
    return result.contents[0].markdown