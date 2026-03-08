# apps/reports/services/pdf_generator.py

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.core.files.storage import default_storage
from django.template.loader import render_to_string


class EnhancedPDFGenerator:
    """
    HTML/CSS-based PDF generator using WeasyPrint.

    We import WeasyPrint lazily so the app and tests can load even when
    Windows native WeasyPrint dependencies are not installed yet.
    """

    def __init__(self):
        self.base_dir = Path(settings.BASE_DIR)
        self.static_dir = self.base_dir / "static"
        self.default_logo_path = self.static_dir / "images" / "school_logo.png"

    def _school_settings(self):
        try:
            from apps.school.models import SchoolSettings
            return SchoolSettings.get_settings()
        except Exception:
            return None

    def _image_to_base64(self, file_or_path, default_placeholder=False) -> str:
        try:
            if hasattr(file_or_path, "open"):
                with file_or_path.open("rb") as f:
                    raw = f.read()
            else:
                path = Path(file_or_path)
                if not path.exists():
                    raise FileNotFoundError(str(path))
                raw = path.read_bytes()

            return f"data:image/png;base64,{base64.b64encode(raw).decode()}"
        except Exception:
            if default_placeholder:
                return self._default_logo_base64()
            return self._default_logo_base64()

    def _default_logo_base64(self) -> str:
        img = Image.new("RGBA", (220, 220), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([10, 10, 210, 210], fill="#1a365d", outline="#3182ce", width=6)

        try:
            font = ImageFont.truetype("arial.ttf", 72)
        except Exception:
            font = ImageFont.load_default()

        draw.text((110, 110), "EP", fill="white", font=font, anchor="mm")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"

    def get_logo_as_base64(self) -> str:
        school_settings = self._school_settings()
        if school_settings and getattr(school_settings, "logo", None):
            return self._image_to_base64(school_settings.logo, default_placeholder=True)

        return self._image_to_base64(self.default_logo_path, default_placeholder=True)

    def get_watermark_as_base64(self) -> str:
        school_settings = self._school_settings()
        if school_settings and getattr(school_settings, "logo_watermark", None):
            return self._image_to_base64(school_settings.logo_watermark, default_placeholder=True)

        return self.get_logo_as_base64()

    def generate_qr_code(self, data: str) -> str:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"

    def generate_daily_report(self, report_data: dict, user) -> bytes:
        return self._render_report(
            report_data=report_data,
            user=user,
            template_name="reports/daily_report.html",
        )

    def generate_staff_report(self, report_data: dict, user) -> bytes:
        return self._render_report(
            report_data=report_data,
            user=user,
            template_name="reports/staff_report.html",
        )

    def _render_report(self, *, report_data: dict, user, template_name: str) -> bytes:
        school_settings = self._school_settings()

        logo_url = self.get_logo_as_base64()
        watermark_url = self.get_watermark_as_base64()
        verification_data = f"EP-REPORT-{report_data['title']}-{getattr(user, 'id', 'anon')}"
        qr_code_url = self.generate_qr_code(verification_data)

        context = {
            "report": report_data,
            "school_logo_url": logo_url,
            "watermark_url": watermark_url,
            "qr_code_url": qr_code_url,
            "show_admin_fee": str(getattr(user, "role", "")).upper() == "BURSAR",
            "school_name": getattr(school_settings, "school_name", "E.P Basic School Ashaiman") if school_settings else "E.P Basic School Ashaiman",
            "school_motto": getattr(school_settings, "school_motto", "Excellence Through Discipline") if school_settings else "Excellence Through Discipline",
            "school_address": getattr(school_settings, "school_address", "Ashaiman, Greater Accra Region, Ghana") if school_settings else "Ashaiman, Greater Accra Region, Ghana",
            "school_phone": getattr(school_settings, "school_phone", "") if school_settings else "",
            "school_email": getattr(school_settings, "school_email", "") if school_settings else "",
            "school_po_box": getattr(school_settings, "school_po_box", "") if school_settings else "",
        }

        html_content = render_to_string(template_name, context)

        try:
            from weasyprint import CSS, HTML
        except Exception as exc:
            raise RuntimeError(
                "WeasyPrint is installed but its native system libraries are missing or not available. "
                "PDF generation cannot run on this machine yet."
            ) from exc

        css = CSS(string=self._print_css())

        return HTML(
            string=html_content,
            base_url=str(settings.BASE_DIR),
        ).write_pdf(
            stylesheets=[css],
            optimize_images=True,
        )

    def generate_and_save(self, report_data: dict, user, filename: str | None = None) -> str:
        from django.utils import timezone

        pdf_bytes = self.generate_daily_report(report_data, user)

        if not filename:
            date_str = report_data["date_range"]["start"].strftime("%Y%m%d")
            filename = f"reports/daily_report_{date_str}_{timezone.now().strftime('%H%M%S')}.pdf"

        return default_storage.save(filename, BytesIO(pdf_bytes))

    def _print_css(self) -> str:
        return """
        @page {
            size: A4 portrait;
            margin: 1.5cm 2cm 2cm 2cm;

            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 9pt;
                color: #666;
            }
        }

        .watermark, .watermark img {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }

        * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }
        """