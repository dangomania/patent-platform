import json
from plone.restapi.services import Service
from patent.platform.ai.translator import draft_response as ai_draft


class DraftResponseService(Service):
    """POST {oa}/@draft-response — generate response draft using AI."""

    def reply(self):
        oa = self.context
        if not oa.original_text:
            self.request.response.setStatus(400)
            return {"error": "原文がありません"}

        try:
            draft = ai_draft(oa.original_text, oa.translation or "")
            oa.response_draft = draft
            oa._p_changed = True
            return {"response_draft": draft}
        except Exception as e:
            self.request.response.setStatus(500)
            return {"error": str(e)}
