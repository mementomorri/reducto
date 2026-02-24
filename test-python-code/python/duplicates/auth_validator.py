"""
Authentication validation functions.
These are semantically similar to user_validator.py for deduplication testing.
"""

def validate_email_address(email):
    if not email:
        raise ValueError("Email address is required")
    if '@' not in email:
        raise ValueError("Email format is invalid - missing @ symbol")
    if '.' not in email.split('@')[-1]:
        raise ValueError("Email domain is invalid")
    if len(email) > 255:
        raise ValueError("Email address is too long")
    if email.startswith('.') or email.endswith('.'):
        raise ValueError("Email cannot start or end with a dot")
    return email.lower().strip()


def validate_user_password(password):
    if not password:
        raise ValueError("Password is required")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(password) > 128:
        raise ValueError("Password is too long")
    if not any(char.isupper() for char in password):
        raise ValueError("Password must contain uppercase letter")
    if not any(char.islower() for char in password):
        raise ValueError("Password must contain lowercase letter")
    if not any(char.isdigit() for char in password):
        raise ValueError("Password must contain a number")
    return password


def validate_username_format(username):
    if not username:
        raise ValueError("Username is required")
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters")
    if len(username) > 30:
        raise ValueError("Username is too long")
    if not username.isalnum():
        raise ValueError("Username must be alphanumeric")
    if username[0].isdigit():
        raise ValueError("Username cannot start with a number")
    return username.lower()


def validate_phone_number(phone):
    if not phone:
        raise ValueError("Phone number is required")
    digits = ''.join(filter(str.isdigit, phone))
    if len(digits) < 10:
        raise ValueError("Phone number is too short")
    if len(digits) > 15:
        raise ValueError("Phone number is too long")
    return digits
