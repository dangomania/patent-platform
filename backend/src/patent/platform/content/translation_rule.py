from plone.dexterity.content import Item
from plone.supermodel import model
from zope import schema
from zope.interface import implementer


class ITranslationRule(model.Schema):
    pattern = schema.TextLine(
        title="パターン",
        required=True,
    )
    replacement = schema.TextLine(
        title="置換後",
        required=True,
    )
    rule_type = schema.Choice(
        title="ルール種別",
        values=["exact", "regex"],
        default="exact",
        required=True,
    )
    enabled = schema.Bool(
        title="有効",
        default=True,
    )
    sort_order = schema.Int(
        title="順序",
        default=0,
        required=False,
    )


@implementer(ITranslationRule)
class TranslationRule(Item):
    """User-specific translation substitution rule."""
