import os
import resend
from jinja2 import Environment, FileSystemLoader
from pathlib import Path


template_dir = Path(__file__).parent.parent / "templates" / "emails"

env = Environment(
    loader=FileSystemLoader(template_dir)
)


resend.api_key = os.getenv("RESEND_EMAIL_API_KEY")

# SEND EMAIL
async def send_email(
    recipients: list[str],
    subject: str,
    template_name: str,
    context: dict,
):

    template = env.get_template(template_name)

    html = template.render(**context)

    resend.Emails.send({
        "from": "Easi Tech Lr support@easitech.email",
        "to": recipients,
        "subject": subject,
        "html": html,
    })

# SEND BATCH EMAIL
async def send_batch_email(emails: list[dict]):
    """
    emails = [
        {
            "from": "...",
            "to": "...",
            "subject": "...",
            "html": "..."
        }
    ]
    """

    if not emails:
        return None

    try:
        response = resend.Batch.send(emails)
        return response

    except Exception as e:
        print(e)
        raise