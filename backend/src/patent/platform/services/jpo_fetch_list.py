from plone.restapi.services import Service
from patent.platform.ai.jpo_api import fetch_oa_list


class JpoFetchListService(Service):
    """GET {case}/@jpo-fetch-list — fetch OA list from J-PlatPat."""

    def reply(self):
        case = self.context
        if not case.app_number:
            self.request.response.setStatus(400)
            return {"error": "出願番号がありません"}
        try:
            return {"items": fetch_oa_list(case.app_number)}
        except Exception as e:
            self.request.response.setStatus(500)
            return {"error": str(e)}
