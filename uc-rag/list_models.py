import os
import sys

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY environment variable not set.")
    sys.exit(1)

# 1. Try NEW SDK (google-genai)
try:
    from google import genai
    print("--- Using NEW SDK (google-genai) ---")
    client = genai.Client(api_key=api_key)
    print("Listing models...")
    for model in client.models.list():
        print(f"- {model.name} (supports: {model.supported_actions})")
except ImportError:
    print("google-genai not installed.")
except Exception as e:
    print(f"Error with NEW SDK: {e}")

print("\n" + "="*40 + "\n")

# 2. Try LEGACY SDK (google-generativeai)
try:
    import google.generativeai as genai
    print("--- Using LEGACY SDK (google-generativeai) ---")
    genai.configure(api_key=api_key)
    print("Listing models...")
    for model in genai.list_models():
        print(f"- {model.name} (supports: {model.supported_generation_methods})")
except ImportError:
    print("google-generativeai not installed.")
except Exception as e:
    print(f"Error with LEGACY SDK: {e}")
