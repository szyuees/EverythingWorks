import os
from dotenv import load_dotenv

load_dotenv()

print("AWS_ACCESS_KEY_ID:", os.environ.get("AWS_ACCESS_KEY_ID"))
print("AWS_SECRET_ACCESS_KEY:", os.environ.get("AWS_SECRET_ACCESS_KEY"))
print("AWS_REGION:", os.environ.get("AWS_REGION"))