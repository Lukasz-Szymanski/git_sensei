import sys
import re
import os

def parse_diff(diff_content):
    """
    Analizuje diff i zwraca listę zmienionych plików oraz wskazówki co do typu zmian.
    """
    files = []
    is_fix = False
    is_test = False
    
    # Prosty parser diffa
    # Szukamy linii: diff --git a/ścieżka/plik b/ścieżka/plik
    file_pattern = re.compile(r"diff --git a/(.*) b/(.*)")
    
    for line in diff_content.splitlines():
        # Wykrywanie plików
        match = file_pattern.match(line)
        if match:
            files.append(match.group(1))
        
        # Heurystyka dla treści (szukamy słów kluczowych w dodanych liniach)
        if line.startswith("+") and not line.startswith("+++"):
            content_lower = line.lower()
            if "fix" in content_lower or "bug" in content_lower or "błąd" in content_lower:
                is_fix = True
            if "test" in content_lower:
                is_test = True

    return files, is_fix, is_test

def determine_type(files, is_fix_content):
    """Ustala typ commita na podstawie rozszerzeń plików."""
    if not files:
        return "chore"

    # Priorytety
    if is_fix_content:
        return "fix"

    extensions = [os.path.splitext(f)[1] for f in files]
    
    # Mapowanie rozszerzeń na typy
    if any(ext in ['.md', '.txt', '.rst'] for ext in extensions):
        return "docs"
    if any(ext in ['.css', '.scss', '.less', '.styl'] for ext in extensions):
        return "style"
    if any('test' in f.lower() for f in files):
        return "test"
    if any(f in ['.gitignore', 'requirements.txt', 'Dockerfile', 'package.json', '.env.example'] for f in files):
        return "chore"
    if any(ext in ['.py', '.js', '.ts', '.go', '.rs', '.java', '.c', '.cpp'] for ext in extensions):
        return "feat"
    
    return "chore"

def generate_message(diff_content):
    files, is_fix, is_test = parse_diff(diff_content)
    
    if not files:
        return "chore: minor update"

    commit_type = determine_type(files, is_fix)
    
    # Scope: nazwa głównego pliku (bez ścieżki i rozszerzenia)
    main_file = os.path.basename(files[0])
    scope = os.path.splitext(main_file)[0]
    
    if len(files) > 1:
        scope = f"{scope}+" # Sygnalizacja, że zmieniono więcej plików

    # Description
    action = "fix" if commit_type == "fix" else "update"
    if commit_type == "feat":
        action = "implement"
    elif commit_type == "docs":
        action = "document"
    elif commit_type == "test":
        action = "add tests for"

    description = f"{action} logic in {main_file}"
    if len(files) > 1:
         description += f" and {len(files)-1} other files"

    return f"{commit_type}({scope}): {description}"

if __name__ == "__main__":
    # Tryb nieinteraktywny: czytamy stdin, piszemy stdout
    try:
        # Wymuszenie kodowania UTF-8 dla stdin/stdout
        if sys.stdin.encoding.lower() != 'utf-8':
            sys.stdin.reconfigure(encoding='utf-8')
        if sys.stdout.encoding.lower() != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
            
        input_diff = sys.stdin.read()
        if not input_diff.strip():
            # Fallback dla pustego wejścia
            print("chore: empty commit")
        else:
            message = generate_message(input_diff)
            print(message)
            
    except Exception as e:
        # Fallback w razie błędu parsowania
        print(f"chore: manual check required (error: {str(e)})")
