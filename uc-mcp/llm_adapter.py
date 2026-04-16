"""
llm_adapter.py — Swappable LLM Call
Default: Google Gemini (free tier)
Alternatives: Claude, OpenAI — uncomment the relevant section

SETUP (Gemini default):
  1. Get a free API key at https://aistudio.google.com/app/apikey
  2. Set environment variable:
       export GEMINI_API_KEY="your-key-here"   (Mac/Linux)
       set GEMINI_API_KEY=your-key-here        (Windows CMD)
  3. Install:
       pip3 install google-generativeai

ALTERNATIVE — Claude:
  export ANTHROPIC_API_KEY="your-key-here"
  pip3 install anthropic
  Uncomment the Claude section below and comment out the Gemini section.

ALTERNATIVE — OpenAI:
  export OPENAI_API_KEY="your-key-here"
  pip3 install openai
  Uncomment the OpenAI section below and comment out the Gemini section.
"""

import os

# ══════════════════════════════════════════════════════════════════════
# GEMINI (DEFAULT)
# ══════════════════════════════════════════════════════════════════════
def call_llm(prompt: str) -> str:
    """
    Call Gemini Flash with the given prompt.
    Returns the text response as a string.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return (
            "[LLM NOT CONFIGURED] Set GEMINI_API_KEY environment variable.\n"
            "Get a free key at https://aistudio.google.com/app/apikey\n\n"
            "Prompt that would have been sent:\n" + prompt[:500] + "..."
        )
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except ImportError:
        return "[ERROR] google-generativeai not installed. Run: pip3 install google-generativeai"
    except Exception as e:
        return f"[LLM ERROR] {str(e)}"


# ══════════════════════════════════════════════════════════════════════
# CLAUDE (ALTERNATIVE — uncomment to use)
# ══════════════════════════════════════════════════════════════════════
# def call_llm(prompt: str) -> str:
#     api_key = os.environ.get("ANTHROPIC_API_KEY")
#     if not api_key:
#         return "[LLM NOT CONFIGURED] Set ANTHROPIC_API_KEY environment variable."
#     try:
#         import anthropic
#         client = anthropic.Anthropic(api_key=api_key)
#         message = client.messages.create(
#             model="claude-3-haiku-20240307",
#             max_tokens=1024,
#             messages=[{"role": "user", "content": prompt}]
#         )
#         return message.content[0].text
#     except ImportError:
#         return "[ERROR] anthropic not installed. Run: pip3 install anthropic"
#     except Exception as e:
#         return f"[LLM ERROR] {str(e)}"


# ══════════════════════════════════════════════════════════════════════
# OPENAI (ALTERNATIVE — uncomment to use)
# ══════════════════════════════════════════════════════════════════════
# def call_llm(prompt: str) -> str:
#     api_key = os.environ.get("OPENAI_API_KEY")
#     if not api_key:
#         return "[LLM NOT CONFIGURED] Set OPENAI_API_KEY environment variable."
#     try:
#         from openai import OpenAI
#         client = OpenAI(api_key=api_key)
#         response = client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[{"role": "user", "content": prompt}]
#         )
#         return response.choices[0].message.content
#     except ImportError:
#         return "[ERROR] openai not installed. Run: pip3 install openai"
#     except Exception as e:
#         return f"[LLM ERROR] {str(e)}"


# ══════════════════════════════════════════════════════════════════════
# TEST
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Testing LLM adapter...")
    result = call_llm("Say 'LLM adapter working' and nothing else.")
    print(f"Response: {result}")
