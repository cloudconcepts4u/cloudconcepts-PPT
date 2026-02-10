import base64
import json
import os
import secrets
import string
import logging
import functions_framework
from datetime import datetime, timezone, timedelta
from google.cloud import secretmanager
from googleapiclient import discovery

# Initialize clients
sm_client = secretmanager.SecretManagerServiceClient()

def generate_password(length=20):
    """Generates a strong random password."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for i in range(length))

def is_recently_rotated(secret_name):
    """
    Checks if the secret was already rotated in the last 5 minutes.
    Returns True if we should SKIP rotation.
    """
    try:
        # Get metadata for the 'latest' version
        latest_version_path = f"{secret_name}/versions/latest"
        response = sm_client.get_secret_version(name=latest_version_path)
        
        # Calculate how long ago it was created
        created_time = response.create_time
        now = datetime.now(timezone.utc)
        
        # Check the difference
        diff = now - created_time
        
        # If created less than 5 minutes ago (300 seconds), skip.
        if diff.total_seconds() < 300:
            print(f"✋ SKIP: Latest version was created only {diff.total_seconds()} seconds ago.")
            return True
            
        return False
    except Exception as e:
        # If 'latest' doesn't exist (first run ever), don't skip.
        print(f"Could not check latest version (normal for first run): {e}")
        return False

@functions_framework.cloud_event
def rotate_password(cloud_event):
    """
    Triggered from a message on a Cloud Pub/Sub topic.
    """
    
    # 1. Extract the Pub/Sub message data
    pubsub_message_data = cloud_event.data["message"]
    
    if 'data' in pubsub_message_data:
        message_body = base64.b64decode(pubsub_message_data['data']).decode('utf-8')
        print(f"Received message body: {message_body}")
        
    # 2. Extract Attributes
    attributes = pubsub_message_data.get('attributes', {})
    event_type = attributes.get('eventType')
    secret_resource_name = attributes.get('secretId') 

    # 3. Safety Check: Only run on Rotation events
    if event_type != 'SECRET_ROTATE':
        print(f"Skipping: Event type is '{event_type}', expected 'SECRET_ROTATE'.")
        return 

    # --- NEW CHECK: IDEMPOTENCY ---
    # This prevents the double-run issue.
    if is_recently_rotated(secret_resource_name):
        print("✅ Rotation already completed recently. Exiting cleanly.")
        return
    # ------------------------------

    print(f"Starting rotation for: {secret_resource_name}")

    # 4. Configuration
    project_id = os.environ.get('PROJECT_ID')
    instance_connection_name = os.environ.get('INSTANCE_CONNECTION_NAME')
    db_user = os.environ.get('DB_USER')

    # 5. Generate New Password
    new_password = generate_password()

    # 6. Update Cloud SQL Password
    try:
        service = discovery.build('sqladmin', 'v1beta4', cache_discovery=False)
        user_body = {"password": new_password}
        
        instance_name = instance_connection_name.split(':')[-1]
        
        # TARGETING EXISTING USER
        target_host = '%' 

        print(f"🔒 TARGETING EXISTING USER: {db_user} @ {target_host} on instance {instance_name}")
        
        request = service.users().update(
            project=project_id,
            instance=instance_name, 
            name=db_user,
            host=target_host,
            body=user_body
        )
        response = request.execute()
        print(f"✅ Cloud SQL update initiated. Operation: {response['operationType']}")
        
    except Exception as e:
        print(f"❌ Error updating Cloud SQL: {e}")
        raise e

    # 7. Update Secret Manager
    try:
        parent = secret_resource_name
        payload = new_password.encode('UTF-8')
        
        response = sm_client.add_secret_version(
            request={"parent": parent, "payload": {"data": payload}}
        )
        print(f"✅ Successfully added new password version to Secret Manager: {response.name}")
        
    except Exception as e:
        print(f"❌ Error updating Secret Manager: {e}")
        raise e
