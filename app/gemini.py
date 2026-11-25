"""Gemini provider (Google AI Studio free tier) — used for testing when no Claude key is set.

Key: set GEMINI_API_KEY (or GOOGLE_API_KEY) in the server environment.
Note: on Google's free tier, prompts may be used to improve Google's models — test with example data only.
"""
import os, json
from pydantic import BaseModel

_client = None


def available():
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


def client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client()
    return _client


def generate_json(system: str, user: str, model_cls: type[BaseModel], model: str):
    """Ask Gemini for JSON matching model_cls and return a validated instance."""
    from google.genai import types
    try:
        resp = client().models.generate_content(
            model=model, contents=user,
            config=types.GenerateContentConfig(system_instruction=system, response_mime_type="application/json",
                                               response_schema=model_cls))
        if getattr(resp, "parsed", None) is not None:
            return resp.parsed if isinstance(resp.parsed, model_cls) else model_cls.model_validate(resp.parsed)
        return model_cls.model_validate_json(resp.text)
    except Exception as first:
        # Some schema features may be rejected: retry with the JSON schema written into the prompt.
        schema = json.dumps(model_cls.model_json_schema(), ensure_ascii=False)
        resp = client().models.generate_content(
            model=model, contents=f"{user}\n\nReturn only JSON matching this JSON schema:\n{schema}",
            config=types.GenerateContentConfig(system_instruction=system, response_mime_type="application/json"))
        try:
            return model_cls.model_validate_json(resp.text)
        except Exception:
            raise first
