"""Email verification utilities"""
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt

from app.config import settings


def create_email_verification_token(email: str) -> str:
    """
    Create a JWT token for email verification.

    Args:
        email: User's email address

    Returns:
        JWT token for email verification
    """
    expire = datetime.utcnow() + timedelta(hours=24)  # Token valid for 24 hours
    payload = {
        "sub": email.lower(),
        "type": "email_verification",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return token


def verify_email_token(token: str) -> Optional[str]:
    """
    Verify an email verification token.

    Args:
        token: JWT token to verify

    Returns:
        Email address if valid, None otherwise
    """
    try:
        from jose import JWTError
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])

        # Check token type
        if payload.get("type") != "email_verification":
            return None

        # Return email
        return payload.get("sub")
    except JWTError:
        return None
    except Exception:
        return None


def send_verification_email(email: str, token: str) -> bool:
    """
    Send verification email to user.

    NOTE: This is a placeholder implementation.
    In production, this would use an email service like SendGrid, SES, etc.

    Args:
        email: User's email address
        token: Verification token

    Returns:
        True if email sent successfully
    """
    # TODO: Implement actual email sending
    # For now, just log the verification link
    verification_url = f"http://localhost:8000/api/v1/auth/verify-email/{token}"
    print(f"📧 [EMAIL NOTIFICATION] Verification link for {email}: {verification_url}")
    print(f"📧 [EMAIL NOTIFICATION] Token: {token}")

    # In production, this would be:
    # from sendgrid import SendGridAPIClient
    # from sendgrid.helpers.mail import Mail
    #
    # message = Mail(
    #     from_email="noreply@arcade.local",
    #     to_emails=email,
    #     subject="Verify Your Email",
    #     html_content=f"""
    #         <h2>Welcome to Arcade Management System!</h2>
    #         <p>Please verify your email address by clicking the link below:</p>
    #         <p><a href="{verification_url}">Verify Email</a></p>
    #         <p>This link will expire in 24 hours.</p>
    #     """
    # )
    #
    # sg = SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
    # response = sg.send(message)
    # return response.status_code == 202

    return True