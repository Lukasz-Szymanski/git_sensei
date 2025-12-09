import sys
import os
import argparse
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except ImportError:
    print("Error: 'google-generativeai' library is not installed.", file=sys.stderr)
    print("Run: pip install google-generativeai", file=sys.stderr)
    sys.exit(1)

def main():
    load_dotenv()

    # 1. Obsługa argumentów CLI (żeby działały flagi --model i --system)
    parser = argparse.ArgumentParser(description="Gemini CLI Wrapper")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Model version")
    parser.add_argument("--system", default="", help="System instruction")
    args = parser.parse_args()

    # 2. Sprawdzenie klucza (To jest CLI, więc musi mieć dostęp do klucza)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables.", file=sys.stderr)
        sys.exit(1)

    # 3. Odczytanie treści z "rury" (Stdin)
    # To tutaj wpada 'git diff'
    try:
        sys.stdin.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7 doesn't support reconfigure, though this project likely uses newer python.
        # Fallback or ignore if not available, but explicit checks are better.
        pass

    user_input = sys.stdin.read().strip()
    if not user_input:
        print("Error: No input provided via stdin.", file=sys.stderr)
        sys.exit(1)

    try:
        # 4. Połączenie z Google
        genai.configure(api_key=api_key)
        
        # Konfiguracja modelu
        # Uwaga: Nie wszystkie modele wspierają 'system_instruction' w ten sposób w SDK,
        # ale 1.5-flash wspiera.
        model = genai.GenerativeModel(
            model_name=args.model,
            system_instruction=args.system if args.system else None
        )

        # 5. Generowanie odpowiedzi
        response = model.generate_content(user_input)
        
        # 6. Wypisanie wyniku na Stdout (żeby main.py mógł to odczytać)
        print(response.text.strip())

    except Exception as e:
        print(f"Gemini API Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()