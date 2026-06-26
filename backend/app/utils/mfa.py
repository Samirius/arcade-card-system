"""Multi-Factor Authentication (MFA) utilities"""
import pyotp
import qrcode
from io import BytesIO
import base64

def generate_mfa_secret() -> str:
    """
    Generate a new MFA secret (TOTP secret key).

    Returns:
        Base32 encoded secret key
    """
    return pyotp.random_base32()

def generate_mfa_qr_code(email: str, secret: str, issuer_name: str = "Arcade Management") -> str:
    """
    Generate a QR code for MFA setup.

    Args:
        email: User's email
        secret: MFA secret key
        issuer_name: Name of the issuer

    Returns:
        Base64 encoded PNG image
    """
    # Create TOTP URI
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=email,
        issuer_name=issuer_name
    )

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    # Create image
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    return img_str

def verify_mfa_token(secret: str, token: str) -> bool:
    """
    Verify an MFA TOTP token.

    Args:
        secret: MFA secret key
        token: 6-digit TOTP token from authenticator app

    Returns:
        True if token is valid, False otherwise
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)  # Allow 1 step window

def generate_mfa_backup_codes(count: int = 10) -> list[str]:
    """
    Generate backup codes for MFA recovery.

    Args:
        count: Number of backup codes to generate

    Returns:
        List of backup codes
    """
    import secrets
    backup_codes = []

    for _ in range(count):
        code = secrets.token_hex(4).upper()
        backup_codes.append(code)

    return backup_codes

def format_backup_code(code: str) -> str:
    """
    Format a backup code for display.

    Args:
        code: Backup code

    Returns:
        Formatted backup code (XXXX-XXXX-XXXX-XXXX)
    """
    # Format as XXXX-XXXX-XXXX-XXXX
    return f"{code[:4]}-{code[4:8]}-{code[8:12]}-{code[12:16]}"