from datetime import date, timedelta
from plone.restapi.services import Service
from Products.CMFCore.utils import getToolByName

DAILY_LIMIT = 6.0


class DashboardDataService(Service):
    """GET @@dashboard-data  — aggregated workload and upcoming jobs."""

    def reply(self):
        user = self.request.get("AUTHENTICATED_USER").getUserName()
        catalog = getToolByName(self.context, "portal_catalog")
        today = date.today()
        window_end = today + timedelta(days=28)

        brains = catalog(
            portal_type="PatentJob",
            Creator=user,
            review_state="published",
        )

        jobs_by_date: dict[str, float] = {}
        upcoming: list[dict] = []
        overdue: list[dict] = []

        for b in brains:
            obj = b.getObject()
            if obj.status == "done":
                continue
            dl = obj.deadline
            if dl is None:
                continue
            key = dl.isoformat()
            jobs_by_date[key] = jobs_by_date.get(key, 0.0) + (obj.estimated_hours or 2.0)

            info = {
                "uid": b.UID,
                "url": b.getURL(),
                "title": b.Title,
                "deadline": key,
                "status": obj.status,
                "priority": obj.priority or 3,
                "estimated_hours": obj.estimated_hours or 2.0,
                "case_ref": _get_case_ref(obj),
            }
            if dl < today:
                overdue.append(info)
            elif dl <= window_end:
                upcoming.append(info)

        upcoming.sort(key=lambda j: (j["deadline"], j["priority"]))
        overdue.sort(key=lambda j: j["deadline"])

        # Build 28-day calendar
        calendar = []
        for i in range(28):
            d = today + timedelta(days=i)
            hours = jobs_by_date.get(d.isoformat(), 0.0)
            if hours == 0:
                level = "empty"
            elif hours <= DAILY_LIMIT * 0.5:
                level = "low"
            elif hours <= DAILY_LIMIT:
                level = "medium"
            else:
                level = "high"
            calendar.append({"date": d.isoformat(), "hours": hours, "level": level})

        return {
            "today": today.isoformat(),
            "upcoming": upcoming[:20],
            "overdue": overdue,
            "calendar": calendar,
        }


def _get_case_ref(job_obj) -> str:
    try:
        case = job_obj.__parent__
        return getattr(case, "case_ref", "") or ""
    except Exception:
        return ""
