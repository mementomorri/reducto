"""
User profile validation functions.
These are semantically similar to auth_validator.py for deduplication testing.
"""

def check_email(email_addr):
    if not email_addr:
        raise Exception("Email is required")
    if '@' not in email_addr:
        raise Exception("Invalid email - no @ symbol found")
    if '.' not in email_addr.split('@')[-1]:
        raise Exception("Invalid email domain")
    if len(email_addr) > 255:
        raise Exception("Email too long")
    if email_addr.startswith('.') or email_addr.endswith('.'):
        raise Exception("Email cannot start or end with period")
    return email_addr.lower().strip()


def check_password(pwd):
    if not pwd:
        raise Exception("Password required")
    if len(pwd) < 8:
        raise Exception("Password needs at least 8 characters")
    if len(pwd) > 128:
        raise Exception("Password exceeds maximum length")
    if not any(c.isupper() for c in pwd):
        raise Exception("Password needs an uppercase letter")
    if not any(c.islower() for c in pwd):
        raise Exception("Password needs a lowercase letter")
    if not any(c.isdigit() for c in pwd):
        raise Exception("Password needs a digit")
    return pwd


def check_user_name(name):
    if not name:
        raise Exception("Name is required")
    if len(name) < 3:
        raise Exception("Name too short - minimum 3 characters")
    if len(name) > 30:
        raise Exception("Name too long")
    if not name.isalnum():
        raise Exception("Name must be alphanumeric only")
    if name[0].isdigit():
        raise Exception("Name cannot start with a digit")
    return name.lower()


def check_telephone(tel):
    if not tel:
        raise Exception("Telephone is required")
    nums = ''.join(filter(str.isdigit, tel))
    if len(nums) < 10:
        raise Exception("Telephone too short")
    if len(nums) > 15:
        raise Exception("Telephone too long")
    return nums
