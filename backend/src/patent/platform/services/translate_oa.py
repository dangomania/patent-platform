import json
from plone.restapi.services import Service
from Products.CMFCore.utils import getToolByName
from patent.platform.ai.translator import translate_oa


class TranslateOAService(Service):
    """POST {oa}/@translate-oa  — AI-translate original_text, persist result."""

    def reply(self):
        oa = self.context
        if not oa.original_text:
            self.request.response.setStatus(400)
            return {"error": "翻訳するテキストがありません"}

        user = self.request.get("AUTHENTICATED_USER").getUserName()
        rules = _load_user_rules(self.context, user)

        try:
            translation = translate_oa(oa.original_text, rules)
            oa.translation = translation
            oa._p_changed = True
            return {"translation": translation}
        except Exception as e:
            self.request.response.setStatus(500)
            return {"error": str(e)}


class SaveTranslationService(Service):
    """POST {oa}/@save-translation  — save manually edited translation."""

    def reply(self):
        body = self.request.get("BODY", b"")
        try:
            data = json.loads(body)
        except (ValueError, TypeError):
            self.request.response.setStatus(400)
            return {"error": "Invalid JSON"}

        translation = data.get("translation", "")
        self.context.translation = translation
        self.context._p_changed = True
        return {"ok": True}


def _load_user_rules(context, username: str) -> list[dict]:
    catalog = getToolByName(context, "portal_catalog")
    brains = catalog(
        portal_type="TranslationRule",
        Creator=username,
        sort_on="sort_order",
    )
    rules = []
    for b in brains:
        obj = b.getObject()
        if obj.enabled:
            rules.append({
                "pattern": obj.pattern,
                "replacement": obj.replacement,
                "rule_type": obj.rule_type,
                "enabled": obj.enabled,
            })
    return rules
