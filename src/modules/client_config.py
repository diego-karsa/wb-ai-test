from dotenv import load_dotenv
from openai import OpenAI
import os, ssl, certifi, httpx, sys

# Load environment variables from .env
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("OPENAI_API_KEY not set in environment")

CERTIFICATE_PATH = os.getenv("CERTIFICATE_PATH")
if not CERTIFICATE_PATH:
    CERTIFICATE_PATH = certifi.where()
    print(f"CERTIFICATE_PATH not set in environment, using default: {CERTIFICATE_PATH}", file=sys.stderr)

# Set up OpenAI client with custom HTTP settings
HTTP_TIMEOUT_SECS=30
_ctx = ssl.create_default_context(cafile=CERTIFICATE_PATH)
_http = httpx.Client(verify=_ctx, timeout=HTTP_TIMEOUT_SECS, follow_redirects=True)
client = OpenAI(api_key=API_KEY, http_client=_http)

def main():
    print("OpenAI client initialized:", client)

if __name__ == "__main__":
    main()