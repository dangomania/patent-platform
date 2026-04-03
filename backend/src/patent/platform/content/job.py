from decimal import Decimal
from plone.dexterity.content import Container
from plone.supermodel import model
from zope import schema
from zope.interface import implementer

JOB_CATEGORIES = {
    "OA対応": ["拒絶理由通知対応", "最終拒絶対応", "異議申立対応"],
    "出願": ["新規出願", "国内移行", "分割出願", "継続出願"],
    "登録・更新": ["登録料納付", "年金納付", "権利維持"],
    "調査": ["先行技術調査", "侵害調査", "無効調査"],
    "その他": ["翻訳", "クライアント対応", "内部会議", "その他"],
}

ALL_JOB_TYPES = [t for types in JOB_CATEGORIES.values() for t in types]

JOB_STATUS_VOCAB = ["pending", "in_progress", "done"]


class IJob(model.Schema):
    category = schema.Choice(
        title="カテゴリ",
        values=list(JOB_CATEGORIES.keys()),
        required=True,
    )
    job_type = schema.Choice(
        title="種別",
        values=ALL_JOB_TYPES,
        required=True,
    )
    description = schema.Text(
        title="説明",
        required=False,
    )
    deadline = schema.Date(
        title="期限",
        required=True,
    )
    estimated_hours = schema.Float(
        title="見積時間",
        default=2.0,
        required=False,
    )
    status = schema.Choice(
        title="ステータス",
        values=JOB_STATUS_VOCAB,
        default="pending",
        required=True,
    )
    priority = schema.Choice(
        title="優先度",
        values=[1, 2, 3],
        default=3,
        required=False,
    )
    notes = schema.Text(
        title="備考",
        required=False,
    )
    completed_at = schema.Datetime(
        title="完了日時",
        required=False,
    )


@implementer(IJob)
class Job(Container):
    """A work item within a Case. Contains one OfficeAction (optional)."""
