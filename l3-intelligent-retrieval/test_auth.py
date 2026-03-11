import time
import hmac
import hashlib
from app.auth import create_service_token

secret = "dev-secret-change-in-production-min-32-chars-xx"
token = create_service_token("l5-generation", "pipeline_reader", secret)
print(token)
