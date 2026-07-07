import os
import smtplib
from email.mime.text import MIMEText


def send_password_reset_email(to_email: str, token: str) -> None:
    """Envía el correo de recuperación de contraseña vía SMTP (stdlib, sin dependencia nueva).

    Configuración por variables de entorno: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
    SMTP_FROM, FRONTEND_URL. Envío síncrono — ver plan.md § Complexity Tracking sobre por qué
    esta fase no usa Celery/Redis para esto.
    """
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    reset_link = f"{frontend_url}/reset-password?token={token}"

    body = (
        "Recibimos una solicitud para restablecer tu contraseña de SyWork Desk.\n\n"
        f"Si fuiste tú, sigue este enlace (válido por 30 minutos):\n{reset_link}\n\n"
        "Si no solicitaste esto, puedes ignorar este correo."
    )
    message = MIMEText(body)
    message["Subject"] = "Restablecer tu contraseña — SyWork Desk"
    message["From"] = os.environ.get("SMTP_FROM", "no-reply@sywork.net")
    message["To"] = to_email

    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        if user and password:
            server.login(user, password)
        server.send_message(message)
