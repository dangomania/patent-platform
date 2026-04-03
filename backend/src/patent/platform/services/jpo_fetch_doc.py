from plone.restapi.services import Service
from patent.platform.ai.jpo_api import fetch_oa_text
from patent.platform.ai.text_cleaner import clean_linebreaks


class JpoFetchDocService(Service):
    """GET {case}/@jpo-fetch-doc?fetch_number=X — fetch and clean OA text."""

    def reply(self):
        fetch_number = self.request.form.get("fetch_number", "")
        if not fetch_number:
            self.request.response.setStatus(400)
            return {"error": "fetch_number is required"}
        try:
            raw = fetch_oa_text(fetch_number)
            cleaned = clean_linebreaks(raw)
            return {"text": cleaned}
        except Exception as e:
            self.request.response.setStatus(500)
            return {"error": str(e)}
