import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db

import base64
from io import StringIO
import json

# Load environment variables from .env file
load_dotenv()

# Get the base64-encoded service account key from environment variables
credentials_base64 = os.getenv('FIREBASE_APPLICATION_CREDENTIALS')
if credentials_base64 is None:
    raise ValueError("Environment variable FIREBASE_APPLICATION_CREDENTIALS is not set")

# Decode the base64 string to JSON
try:
    service_account_key_json = base64.b64decode(credentials_base64).decode('utf-8')
    service_account_key = json.loads(service_account_key_json)
except Exception as e:
    raise ValueError("Error decoding or parsing service account key: " + str(e))

# Get the database URL from environment variables
database_url = os.getenv('DATABASE_URL')
if database_url is None:
    raise ValueError("Environment variable DATABASE_URL is not set")

# Initialize the app with a service account, granting admin privileges
try:
    cred = credentials.Certificate(service_account_key)
    firebase_admin.initialize_app(cred, {
        'databaseURL': database_url
    })
except Exception as e:
    raise ValueError("Error initializing Firebase app: " + str(e))

