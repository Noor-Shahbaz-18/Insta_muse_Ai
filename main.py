
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


# ==========================================
# 1. ENVIRONMENT CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMMA_MODEL = os.getenv(
    "GEMMA_MODEL",
    "gemma-4-26b-a4b-it"
)

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing from backend/.env"
    )

client = genai.Client(api_key=GEMINI_API_KEY)


# ==========================================
# 2. FASTAPI APPLICATION
# ==========================================

app = FastAPI(
    title="BrandPilot AI",
    description="AI Instagram Manager and Security Guardian",
    version="1.0.0"
)


# ==========================================
# 3. CORS CONFIGURATION
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ==========================================
# 4. MEDIA CONFIGURATION
# ==========================================

app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOAD_DIR)),
    name="uploads"
)

ALLOWED_TYPES = {
    "image/jpeg": (".jpg", "image"),
    "image/png": (".png", "image"),
    "image/webp": (".webp", "image"),
    "video/mp4": (".mp4", "video"),
    "video/quicktime": (".mov", "video")
}

MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_FILES = 5

# Temporary hackathon storage
MEDIA_STORE = {}
CONTENT_STORE = {}


# ==========================================
# 5. REQUEST MODELS
# ==========================================

class GenerateContentRequest(BaseModel):
    media_ids: list[str] = Field(min_length=1)
    product_name: str
    description: str
    price: float | None = None
    currency: str = "PKR"
    discount: str | None = None
    target_audience: str | None = None
    objective: Literal[
        "sales", "awareness", "engagement", "launch"
    ] = "sales"
    post_type: Literal[
        "feed", "carousel", "reel", "story"
    ] = "feed"
    tone: str = "Professional"
    language: str = "English"
    instructions: str | None = None


# ==========================================
# 6. HELPER FUNCTIONS
# ==========================================

def public_asset(asset):
    return {
        "id": asset["id"],
        "filename": asset["filename"],
        "media_type": asset["media_type"],
        "url": asset["url"],
        "mime_type": asset["mime_type"],
        "size_bytes": asset["size_bytes"]
    }


def clean_json_response(text):
    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def build_prompt(payload, video_count):
    return f"""
You are BrandPilot AI, an Instagram marketing assistant.

Analyze the provided product information and attached
images to create professional marketing content.

Product: {payload.product_name}
Description: {payload.description}
Price: {payload.price}
Currency: {payload.currency}
Discount: {payload.discount or "Not provided"}
Target Audience: {payload.target_audience}
Objective: {payload.objective}
Post Type: {payload.post_type}
Tone: {payload.tone}
Language: {payload.language}
Instructions: {payload.instructions or "None"}

Number of uploaded videos: {video_count}

Important:
Video files are uploaded but their frames have NOT been
provided for visual analysis. Do not invent video scenes.
Do not invent discounts, sizes, materials, or product facts.

Generate marketing copy in JSON format only.

Return exactly these JSON fields:

{{
    "caption": "Instagram caption",
    "hashtags": ["#tag1", "#tag2", "#tag3"],
    "cta": "Call to action",
    "content_rationale": "Short explanation",
    "reel_hook": null,
    "reel_script": null,
    "carousel_slides": []
}}

For reel posts, provide reel_hook and reel_script.
For carousel posts, provide carousel_slides.

Return valid JSON only.
No Markdown or code fences.
""".strip()


# ==========================================
# 7. HOME & HEALTH ENDPOINTS
# ==========================================

@app.get("/")
async def home():
    return {
        "message": "Welcome to BrandPilot AI!",
        "status": "Backend is running"
    }


@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "BrandPilot AI Backend",
        "version": "1.0.0"
    }


# ==========================================
# 8. MULTIPLE FILE UPLOAD API
# ==========================================

@app.post("/api/v1/media/upload")
async def upload_media(
    files: list[UploadFile] = File(
        ...,
        description="Choose up to 5 images or videos"
    )
):
    if not 1 <= len(files) <= MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail="Upload between 1 and 5 files."
        )

    saved_paths = []
    new_assets = []

    try:
        for file in files:

            if file.content_type not in ALLOWED_TYPES:
                raise HTTPException(
                    status_code=415,
                    detail=(
                        f"Unsupported format: {file.content_type}"
                    )
                )

            extension, media_type = ALLOWED_TYPES[
                file.content_type
            ]

            file_id = str(uuid4())
            saved_filename = f"{file_id}{extension}"
            file_path = UPLOAD_DIR / saved_filename

            saved_paths.append(file_path)
            total_size = 0

            with open(file_path, "wb") as output:
                while True:
                    chunk = await file.read(1024 * 1024)

                    if not chunk:
                        break

                    total_size += len(chunk)

                    if total_size > MAX_FILE_SIZE:
                        raise HTTPException(
                            status_code=413,
                            detail=(
                                f"{file.filename} exceeds 50 MB."
                            )
                        )

                    output.write(chunk)

            if total_size == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Empty files are not allowed."
                )

            asset = {
                "id": file_id,
                "filename": file.filename,
                "media_type": media_type,
                "url": (
                    "http://127.0.0.1:8000/uploads/"
                    + saved_filename
                ),
                "mime_type": file.content_type,
                "size_bytes": total_size,
                "saved_filename": saved_filename
            }

            new_assets.append(asset)

        # Commit only after every file succeeds
        for asset in new_assets:
            MEDIA_STORE[asset["id"]] = asset

        return {
            "assets": [
                public_asset(asset)
                for asset in new_assets
            ]
        }

    except Exception:
        for path in saved_paths:
            path.unlink(missing_ok=True)
        raise

    finally:
        for file in files:
            await file.close()


# ==========================================
# 9. AI CONTENT GENERATION API
# ==========================================

@app.post("/api/v1/content/generate")
async def generate_content(payload: GenerateContentRequest):

    media_assets = []
    parts = []
    video_count = 0

    for media_id in payload.media_ids:

        asset = MEDIA_STORE.get(media_id)

        if not asset:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Media ID {media_id} not found. "
                    "Please upload the file again."
                )
            )

        media_assets.append(public_asset(asset))

        if asset["media_type"] == "image":

            file_path = UPLOAD_DIR / asset["saved_filename"]

            if not file_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail="Uploaded image is missing."
                )

            parts.append(
                types.Part.from_bytes(
                    data=file_path.read_bytes(),
                    mime_type=asset["mime_type"]
                )
            )

        else:
            video_count += 1

    prompt = build_prompt(payload, video_count)

    parts.insert(
        0,
        types.Part.from_text(text=prompt)
    )

    try:
        response = client.models.generate_content(
            model=GEMMA_MODEL,
            contents=parts
        )

        raw_text = response.text or ""

        ai_result = json.loads(
            clean_json_response(raw_text)
        )

        if not isinstance(ai_result, dict):
            raise ValueError("Expected a JSON object.")

    except (json.JSONDecodeError, ValueError):
        raise HTTPException(
            status_code=502,
            detail="AI returned invalid JSON. Please retry."
        )

    except Exception:
        raise HTTPException(
            status_code=502,
            detail=(
                "AI generation failed. "
                "Check model access, quota or connection."
            )
        )

    content_id = str(uuid4())

    content_item = {
        "id": content_id,
        "status": "draft",
        "media": media_assets,
        "product_name": payload.product_name,
        "post_type": payload.post_type,
        "caption": ai_result.get("caption") or "",
        "hashtags": ai_result.get("hashtags") or [],
        "cta": ai_result.get("cta") or "",
        "content_rationale": (
            ai_result.get("content_rationale") or ""
        ),
        "reel_hook": ai_result.get("reel_hook"),
        "reel_script": ai_result.get("reel_script"),
        "carousel_slides": (
            ai_result.get("carousel_slides") or []
        ),
        "preview_url": (
            media_assets[0]["url"]
            if media_assets else None
        ),
        "scheduled_at": None,
        "published_at": None,
        "created_at": datetime.now(
            timezone.utc
        ).isoformat()
    }

    CONTENT_STORE[content_id] = content_item

    return {
        "content": content_item
    }


# ==========================================
# 10. SWAGGER FILE PICKER COMPATIBILITY FIX
# ==========================================

def custom_openapi():

    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes
    )

    # Swagger UI compatibility for file arrays
    components = schema.get(
        "components", {}
    ).get("schemas", {})

    for component in components.values():
        properties = component.get("properties", {})

        for prop in properties.values():

            # Single file
            if prop.get("contentMediaType") == (
                "application/octet-stream"
            ):
                prop.pop("contentMediaType", None)
                prop["type"] = "string"
                prop["format"] = "binary"

            # Multiple files
            items = prop.get("items")

            if isinstance(items, dict):
                if items.get("contentMediaType") == (
                    "application/octet-stream"
                ):
                    items.pop("contentMediaType", None)
                    items["type"] = "string"
                    items["format"] = "binary"

    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi
