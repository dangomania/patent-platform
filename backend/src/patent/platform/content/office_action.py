from plone.dexterity.content import Item
from plone.supermodel import model
from zope import schema
from zope.interface import implementer


class IOfficeAction(model.Schema):
    oa_date = schema.Date(
        title="OA日付",
        required=False,
    )
    original_text = schema.Text(
        title="原文",
        required=False,
    )
    translation = schema.Text(
        title="翻訳",
        required=False,
    )
    response_draft = schema.Text(
        title="応答草案",
        required=False,
    )


@implementer(IOfficeAction)
class OfficeAction(Item):
    """Office Action document attached to a Job."""
