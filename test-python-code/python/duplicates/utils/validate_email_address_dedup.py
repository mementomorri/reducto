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
