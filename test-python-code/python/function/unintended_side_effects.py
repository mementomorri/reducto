#Bad Code
def process_data(data):
    # Perform data processing
    processed_data = perform_computation(data)

    # Store data in a database
    store_data_in_database(processed_data)

    # Send a notification email
    send_notification_email()

    # Return the processed data
    return processed_data

  #Good Code
  def process_data(data):
    # Perform data processing
    processed_data = perform_computation(data)

    return processed_data

def store_data(data):
    # Store data in a database
    store_data_in_database(data)

def send_notification():
    # Send a notification email
    send_notification_email()
