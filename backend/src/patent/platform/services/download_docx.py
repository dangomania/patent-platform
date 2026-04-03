import io
from plone.restapi.services import Service
from patent.platform.ai.doc_generator import generate_oa_docx


class DownloadDocxService(Service):
    """GET {oa}/@download-docx  — generate and return Word document."""

    def reply(self):
        oa = self.context

        if not oa.translation:
            self.request.response.setStatus(400)
            return {"error": "翻訳がありません"}

        try:
            buf = io.BytesIO()
            generate_oa_docx(oa.original_text or "", oa.translation, buf)
            buf.seek(0)
            data = buf.read()
        except Exception as e:
            self.request.response.setStatus(500)
            return {"error": str(e)}

        response = self.request.response
        response.setHeader(
            "Content-Type",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response.setHeader(
            "Content-Disposition",
            f'attachment; filename="OA-translation.docx"',
        )
        response.setHeader("Content-Length", str(len(data)))
        return data
