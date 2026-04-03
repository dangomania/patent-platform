import json
from plone.restapi.services import Service
from Products.CMFCore.utils import getToolByName
from plone.api import content as api_content
from plone.api.portal import get as get_portal


class TranslationRulesGet(Service):
    """GET @@translation-rules  — list rules for the current user."""

    def reply(self):
        user = self.request.get("AUTHENTICATED_USER").getUserName()
        catalog = getToolByName(self.context, "portal_catalog")
        brains = catalog(
            portal_type="TranslationRule",
            Creator=user,
            sort_on="sort_order",
        )
        return {
            "rules": [
                {
                    "uid": b.UID,
                    "url": b.getURL(),
                    "pattern": b.getObject().pattern,
                    "replacement": b.getObject().replacement,
                    "rule_type": b.getObject().rule_type,
                    "enabled": b.getObject().enabled,
                    "sort_order": b.getObject().sort_order or 0,
                }
                for b in brains
            ]
        }


class TranslationRulesPost(Service):
    """POST @@translation-rules  — create a new rule for the current user."""

    def reply(self):
        body = self.request.get("BODY", b"")
        try:
            data = json.loads(body)
        except (ValueError, TypeError):
            self.request.response.setStatus(400)
            return {"error": "Invalid JSON"}

        portal = get_portal()
        rules_folder = portal.get("translation-rules")
        if rules_folder is None:
            rules_folder = api_content.create(
                container=portal,
                type="Folder",
                id="translation-rules",
                title="Translation Rules",
            )

        import uuid
        obj = api_content.create(
            container=rules_folder,
            type="TranslationRule",
            id=str(uuid.uuid4()),
            pattern=data.get("pattern", ""),
            replacement=data.get("replacement", ""),
            rule_type=data.get("rule_type", "exact"),
            enabled=data.get("enabled", True),
            sort_order=data.get("sort_order", 0),
        )
        self.request.response.setStatus(201)
        return {"uid": obj.UID(), "url": obj.absolute_url()}


class TranslationRulePatch(Service):
    """PATCH {rule}/@update  — update fields of an existing rule."""

    def reply(self):
        body = self.request.get("BODY", b"")
        try:
            data = json.loads(body)
        except (ValueError, TypeError):
            self.request.response.setStatus(400)
            return {"error": "Invalid JSON"}

        obj = self.context
        for field in ("pattern", "replacement", "rule_type", "enabled", "sort_order"):
            if field in data:
                setattr(obj, field, data[field])
        obj._p_changed = True
        return {"ok": True}


class TranslationRuleDelete(Service):
    """DELETE {rule}/@delete  — remove a translation rule."""

    def reply(self):
        api_content.delete(obj=self.context)
        self.request.response.setStatus(204)
        return {}
