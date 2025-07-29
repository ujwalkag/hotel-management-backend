# apps/bills/utils.py
import os
from django.template.loader import get_template
from django.conf import settings
from xhtml2pdf import pisa

def render_to_pdf(template_src, context_dict, output_path):
    template = get_template(template_src)
    html = template.render(context_dict)
    with open(output_path, "wb") as f:
        pisa_status = pisa.CreatePDF(html, dest=f)
    return not pisa_status.err

