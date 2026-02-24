"""
High complexity functions to trigger complexity hotspot detection.
Target: Cyclomatic Complexity >= 10
"""

def process_order(order_type, customer_tier, region, amount, is_rush, is_weekend):
    if order_type == "standard":
        if customer_tier == "gold":
            if region == "north":
                if amount > 1000:
                    if is_rush:
                        return "priority_gold_north_rush"
                    else:
                        if is_weekend:
                            return "gold_north_weekend_standard"
                        else:
                            return "gold_north_weekday_standard"
                else:
                    if is_rush:
                        return "gold_north_small_rush"
                    else:
                        return "gold_north_small_standard"
            elif region == "south":
                if amount > 1000:
                    if is_rush:
                        return "priority_gold_south_rush"
                    else:
                        return "gold_south_standard"
                else:
                    return "gold_south_small"
            elif region == "east":
                return "gold_east"
            elif region == "west":
                return "gold_west"
        elif customer_tier == "silver":
            if region == "north":
                return "silver_north"
            elif region == "south":
                if amount > 500:
                    return "silver_south_large"
                else:
                    return "silver_south_small"
        elif customer_tier == "bronze":
            return "bronze_standard"
    elif order_type == "express":
        if customer_tier == "gold":
            if is_rush:
                return "express_gold_rush"
            else:
                return "express_gold"
        elif customer_tier == "silver":
            return "express_silver"
    elif order_type == "overnight":
        if region == "north" or region == "south":
            if amount > 2000:
                return "overnight_large"
            else:
                return "overnight_standard"
        else:
            return "overnight_other"
    return "default"


def validate_user_registration(username, email, password, age, country, terms_accepted, privacy_accepted, marketing_opt_in):
    errors = []
    
    if not username:
        errors.append("Username required")
    elif len(username) < 3:
        errors.append("Username too short")
    elif len(username) > 20:
        errors.append("Username too long")
    elif not username.isalnum():
        errors.append("Username must be alphanumeric")
    
    if not email:
        errors.append("Email required")
    elif '@' not in email:
        errors.append("Invalid email format")
    elif '.' not in email.split('@')[-1]:
        errors.append("Invalid email domain")
    elif len(email) > 255:
        errors.append("Email too long")
    
    if not password:
        errors.append("Password required")
    elif len(password) < 8:
        errors.append("Password too short")
    elif len(password) > 128:
        errors.append("Password too long")
    elif not any(c.isupper() for c in password):
        errors.append("Password needs uppercase")
    elif not any(c.islower() for c in password):
        errors.append("Password needs lowercase")
    elif not any(c.isdigit() for c in password):
        errors.append("Password needs digit")
    
    if age is not None:
        if age < 13:
            errors.append("Too young")
        elif age > 120:
            errors.append("Invalid age")
    
    if country not in ["US", "CA", "UK", "EU", "AU"]:
        if country:
            errors.append("Unsupported country")
    
    if not terms_accepted:
        errors.append("Terms must be accepted")
    
    if not privacy_accepted:
        errors.append("Privacy policy must be accepted")
    
    return errors if errors else None


def calculate_shipping_cost(weight, dimensions, origin_country, dest_country, service_level, insurance, signature_required):
    base_cost = 5.0
    
    if weight > 0:
        if weight <= 1:
            base_cost += 2.0
        elif weight <= 5:
            base_cost += 5.0
        elif weight <= 10:
            base_cost += 10.0
        elif weight <= 20:
            base_cost += 20.0
        else:
            base_cost += weight * 1.5
    
    if dimensions:
        volume = dimensions.get('length', 0) * dimensions.get('width', 0) * dimensions.get('height', 0)
        if volume > 1000:
            base_cost += volume / 100
    
    if origin_country != dest_country:
        if dest_country in ["US", "CA", "MX"]:
            base_cost += 10
        elif dest_country in ["UK", "FR", "DE", "IT", "ES"]:
            base_cost += 25
        elif dest_country in ["AU", "NZ", "JP"]:
            base_cost += 40
        else:
            base_cost += 50
    
    if service_level == "express":
        base_cost *= 2.0
    elif service_level == "overnight":
        base_cost *= 3.5
    elif service_level == "same_day":
        base_cost *= 5.0
    
    if insurance:
        base_cost += 5.0
    
    if signature_required:
        base_cost += 2.5
    
    return round(base_cost, 2)
