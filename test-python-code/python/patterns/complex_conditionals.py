"""
Complex conditional logic that suggests design pattern opportunities.
Target: Strategy Pattern, Factory Pattern, State Pattern
"""


# STRATEGY PATTERN OPPORTUNITY: Payment processing with multiple payment types
def process_payment(payment_type, amount, currency, customer_info):
    if payment_type == "credit_card":
        if currency == "USD":
            if amount > 10000:
                fee = amount * 0.015
                result = charge_high_value_cc(amount, fee, customer_info)
            else:
                fee = amount * 0.025
                result = charge_standard_cc(amount, fee, customer_info)
        elif currency == "EUR":
            if amount > 9000:
                fee = amount * 0.018
                result = charge_high_value_cc_eur(amount, fee, customer_info)
            else:
                fee = amount * 0.028
                result = charge_standard_cc_eur(amount, fee, customer_info)
        elif currency == "GBP":
            fee = amount * 0.030
            result = charge_standard_cc_gbp(amount, fee, customer_info)
        else:
            raise ValueError("Unsupported currency for credit card")
    
    elif payment_type == "paypal":
        if currency in ["USD", "EUR"]:
            fee = amount * 0.029 + 0.30
            result = process_paypal(amount, fee, customer_info)
        else:
            raise ValueError("PayPal only supports USD and EUR")
    
    elif payment_type == "bank_transfer":
        if currency == "USD":
            if amount > 50000:
                result = process_wire_transfer(amount, customer_info)
            else:
                result = process_ach_transfer(amount, customer_info)
        elif currency == "EUR":
            result = process_sepa_transfer(amount, customer_info)
        else:
            raise ValueError("Unsupported currency for bank transfer")
    
    elif payment_type == "crypto":
        if currency in ["BTC", "ETH"]:
            fee = amount * 0.01
            result = process_crypto(amount, fee, currency, customer_info)
        else:
            raise ValueError("Only BTC and ETH supported")
    
    elif payment_type == "apple_pay" or payment_type == "google_pay":
        if currency in ["USD", "EUR", "GBP"]:
            fee = amount * 0.015
            result = process_mobile_payment(payment_type, amount, fee, customer_info)
        else:
            raise ValueError("Mobile payment currency not supported")
    
    else:
        raise ValueError(f"Unknown payment type: {payment_type}")
    
    return result


def charge_high_value_cc(amount, fee, customer_info):
    return {"status": "success", "amount": amount, "fee": fee}

def charge_standard_cc(amount, fee, customer_info):
    return {"status": "success", "amount": amount, "fee": fee}

def charge_high_value_cc_eur(amount, fee, customer_info):
    return {"status": "success", "amount": amount, "fee": fee}

def charge_standard_cc_eur(amount, fee, customer_info):
    return {"status": "success", "amount": amount, "fee": fee}

def charge_standard_cc_gbp(amount, fee, customer_info):
    return {"status": "success", "amount": amount, "fee": fee}

def process_paypal(amount, fee, customer_info):
    return {"status": "success", "amount": amount, "fee": fee}

def process_wire_transfer(amount, customer_info):
    return {"status": "success", "amount": amount, "fee": 25}

def process_ach_transfer(amount, customer_info):
    return {"status": "success", "amount": amount, "fee": 0.50}

def process_sepa_transfer(amount, customer_info):
    return {"status": "success", "amount": amount, "fee": 0}

def process_crypto(amount, fee, currency, customer_info):
    return {"status": "success", "amount": amount, "fee": fee}

def process_mobile_payment(payment_type, amount, fee, customer_info):
    return {"status": "success", "amount": amount, "fee": fee}


# FACTORY PATTERN OPPORTUNITY: Object creation based on type
def create_database_connection(db_type, host, port, username, password, database):
    if db_type == "postgresql":
        connection = PostgresConnection()
        connection.set_host(host)
        connection.set_port(port or 5432)
        connection.set_credentials(username, password)
        connection.set_database(database)
        connection.set_ssl_mode("require")
        connection.set_timeout(30)
        return connection
    
    elif db_type == "mysql":
        connection = MySQLConnection()
        connection.set_host(host)
        connection.set_port(port or 3306)
        connection.set_credentials(username, password)
        connection.set_database(database)
        connection.set_charset("utf8mb4")
        return connection
    
    elif db_type == "mongodb":
        connection = MongoConnection()
        connection.set_host(host)
        connection.set_port(port or 27017)
        connection.set_credentials(username, password)
        connection.set_database(database)
        connection.set_auth_source("admin")
        connection.set_replica_set(None)
        return connection
    
    elif db_type == "redis":
        connection = RedisConnection()
        connection.set_host(host)
        connection.set_port(port or 6379)
        if password:
            connection.set_password(password)
        connection.set_database(database or 0)
        return connection
    
    elif db_type == "sqlite":
        connection = SQLiteConnection()
        connection.set_file_path(database)
        connection.set_timeout(5)
        return connection
    
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


class PostgresConnection:
    def set_host(self, host): pass
    def set_port(self, port): pass
    def set_credentials(self, username, password): pass
    def set_database(self, database): pass
    def set_ssl_mode(self, mode): pass
    def set_timeout(self, timeout): pass

class MySQLConnection:
    def set_host(self, host): pass
    def set_port(self, port): pass
    def set_credentials(self, username, password): pass
    def set_database(self, database): pass
    def set_charset(self, charset): pass

class MongoConnection:
    def set_host(self, host): pass
    def set_port(self, port): pass
    def set_credentials(self, username, password): pass
    def set_database(self, database): pass
    def set_auth_source(self, source): pass
    def set_replica_set(self, replica): pass

class RedisConnection:
    def set_host(self, host): pass
    def set_port(self, port): pass
    def set_password(self, password): pass
    def set_database(self, database): pass

class SQLiteConnection:
    def set_file_path(self, path): pass
    def set_timeout(self, timeout): pass


# STATE PATTERN OPPORTUNITY: Order status transitions
def update_order_status(order, new_status, metadata=None):
    current_status = order["status"]
    
    if current_status == "pending":
        if new_status == "confirmed":
            order["status"] = "confirmed"
            order["confirmed_at"] = metadata.get("timestamp")
        elif new_status == "cancelled":
            order["status"] = "cancelled"
            order["cancelled_at"] = metadata.get("timestamp")
            order["cancellation_reason"] = metadata.get("reason")
        else:
            raise ValueError(f"Cannot transition from pending to {new_status}")
    
    elif current_status == "confirmed":
        if new_status == "processing":
            order["status"] = "processing"
            order["processing_started_at"] = metadata.get("timestamp")
        elif new_status == "cancelled":
            order["status"] = "cancelled"
            order["cancelled_at"] = metadata.get("timestamp")
        else:
            raise ValueError(f"Cannot transition from confirmed to {new_status}")
    
    elif current_status == "processing":
        if new_status == "shipped":
            order["status"] = "shipped"
            order["shipped_at"] = metadata.get("timestamp")
            order["tracking_number"] = metadata.get("tracking")
        elif new_status == "on_hold":
            order["status"] = "on_hold"
            order["hold_reason"] = metadata.get("reason")
        else:
            raise ValueError(f"Cannot transition from processing to {new_status}")
    
    elif current_status == "on_hold":
        if new_status == "processing":
            order["status"] = "processing"
            order["hold_resolved_at"] = metadata.get("timestamp")
        elif new_status == "cancelled":
            order["status"] = "cancelled"
            order["cancelled_at"] = metadata.get("timestamp")
        else:
            raise ValueError(f"Cannot transition from on_hold to {new_status}")
    
    elif current_status == "shipped":
        if new_status == "delivered":
            order["status"] = "delivered"
            order["delivered_at"] = metadata.get("timestamp")
        elif new_status == "returned":
            order["status"] = "returned"
            order["returned_at"] = metadata.get("timestamp")
        else:
            raise ValueError(f"Cannot transition from shipped to {new_status}")
    
    elif current_status == "delivered":
        if new_status == "returned":
            order["status"] = "returned"
            order["returned_at"] = metadata.get("timestamp")
        else:
            raise ValueError(f"Cannot transition from delivered to {new_status}")
    
    elif current_status in ["cancelled", "returned"]:
        raise ValueError(f"Order is already {current_status} and cannot be modified")
    
    else:
        raise ValueError(f"Unknown status: {current_status}")
    
    return order
