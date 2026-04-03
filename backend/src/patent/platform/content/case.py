from plone.dexterity.content import Container
from plone.supermodel import model
from zope import schema
from zope.interface import implementer

CASE_STATUS_VOCAB = [
    ("active",         "対応中"),
    ("action_needed",  "要対応"),
    ("waiting_client", "クライアント待ち"),
    ("no_task",        "タスクなし"),
    ("abandoned",      "取り下げ"),
    ("transferred",    "移管済み"),
]

COUNTRY_VOCAB = ["JP", "US", "EP", "CN", "KR", "PCT", "AU", "CA", "IN", "BR", "RU"]


class ICase(model.Schema):
    case_ref = schema.TextLine(
        title="社内整理番号",
        required=True,
    )
    client = schema.TextLine(
        title="クライアント",
        required=False,
    )
    # title field comes from IDublinCore (plone.dublincore behavior)
    app_number = schema.TextLine(
        title="出願番号",
        required=False,
    )
    country = schema.Choice(
        title="国",
        values=COUNTRY_VOCAB,
        default="JP",
        required=True,
    )
    technology = schema.TextLine(
        title="技術分野",
        required=False,
    )
    notes = schema.Text(
        title="備考",
        required=False,
    )
    status = schema.Choice(
        title="ステータス",
        values=[v for v, _ in CASE_STATUS_VOCAB],
        default="active",
        required=True,
    )


@implementer(ICase)
class Case(Container):
    """A patent prosecution case. Contains PatentJob objects."""
