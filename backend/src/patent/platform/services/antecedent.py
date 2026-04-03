from plone.restapi.services import Service
from patent.platform.ai.ja_parser import analyze


class AntecedentCheckService(Service):
    """POST @@antecedent-check  — run antecedent basis analysis on claim text."""

    def reply(self):
        body = self.request.get("BODY", b"")
        import json
        try:
            data = json.loads(body)
        except (ValueError, TypeError):
            self.request.response.setStatus(400)
            return {"error": "Invalid JSON"}

        text = data.get("text", "")
        if not text.strip():
            self.request.response.setStatus(400)
            return {"error": "テキストが空です"}

        try:
            return analyze(text)
        except Exception as e:
            self.request.response.setStatus(500)
            return {"error": str(e)}
