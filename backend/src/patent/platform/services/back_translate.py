import json
import os
import httpx
from plone.restapi.services import Service


class BackTranslateService(Service):
    """POST @@back-translate  — Google Translate JA→EN for accuracy checking."""

    def reply(self):
        body = self.request.get("BODY", b"")
        try:
            data = json.loads(body)
        except (ValueError, TypeError):
            self.request.response.setStatus(400)
            return {"error": "Invalid JSON"}

        text = data.get("text", "")
        if not text:
            self.request.response.setStatus(400)
            return {"error": "No text"}

        api_key = os.environ.get("GOOGLE_TRANSLATE_API_KEY", "")
        if not api_key:
            self.request.response.setStatus(503)
            return {"error": "Google Translate not configured"}

        try:
            r = httpx.post(
                "https://translation.googleapis.com/language/translate/v2",
                params={"key": api_key},
                json={"q": text, "source": "ja", "target": "en", "format": "text"},
                timeout=30,
            )
            r.raise_for_status()
            back = r.json()["data"]["translations"][0]["translatedText"]
            return {"back_translation": back}
        except Exception as e:
            self.request.response.setStatus(500)
            return {"error": str(e)}
