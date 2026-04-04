import sys
print(f"Python: {sys.executable}")
print(f"Version: {sys.version}")

try:
    import google.genai
    print("google-genai IS installed")
except ImportError:
    print("google-genai NOT installed")

try:
    import google.generativeai as genai
    print("google-generativeai IS installed")
    print(f"google-generativeai version: {genai.__version__}")
except ImportError:
    print("google-generativeai NOT installed")

try:
    import chromadb
    print("chromadb IS installed")
except ImportError:
    print("chromadb NOT installed")

try:
    import sentence_transformers
    print("sentence-transformers IS installed")
except ImportError:
    print("sentence-transformers NOT installed")
