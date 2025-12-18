# 🗺️ Git-Sensei: Plan Prac MVP

> **Cel:** Stworzenie działającego narzędzia CLI w Pythonie, które łączy Git z Gemini CLI.

---

## ETAP 1: Git Connector (Fundament)

- **Cel:** Skrypt potrafi sprawdzić środowisko i pobrać treść zmian ze stagingu.
- **Kroki:**
  1.  Zainicjuj aplikację `Typer` w `main.py`.
  2.  Stwórz funkcję `check_dependencies()`: użyj `shutil.which`, aby upewnić się, że `git` i `gemini-chat` są zainstalowane. Jeśli nie – przerwij działanie (`sys.exit`).
  3.  Stwórz funkcję `get_staged_diff()`: wykonaj `git diff --staged`.
- **Edge Cases:**
  - Brak zainstalowanego Gita/Gemini -> Wyświetl jasny błąd i instrukcję.
  - Uruchomienie poza repozytorium git -> Obsłuż `subprocess.CalledProcessError`.
- **Definicja Done:** Uruchomienie `python main.py` wyświetla na ekranie surowy tekst zmian (diff) lub błąd, jeśli brak zmian.
- **Test:** `git add .` -> `python main.py` -> Widzę tekst zmian.

---

## ETAP 2: AI Pipe Integration (Logika)

- **Cel:** Skrypt potrafi wysłać diff do Gemini i odebrać czystą wiadomość commita.
- **Kroki:**
  1.  Zdefiniuj stałą `SYSTEM_PROMPT` z zasadami **Conventional Commits** (wymuś brak markdowna).
  2.  Stwórz funkcję `generate_commit_message(diff)`:
      - Użyj `subprocess.Popen` z `stdin=subprocess.PIPE`.
      - Przekaż `diff` do procesu `gemini-chat --system "..."`.
  3.  Oczyść wynik (`.strip()`), usuwając ewentualne cudzysłowy lub backticki.
- **Edge Cases:**
  - Błąd procesu Gemini (np. brak konfiguracji API w systemie) -> Przechwyć `stderr` i wyświetl błąd na czerwono.
- **Definicja Done:** Program wyświetla jedną linię tekstu: np. `feat: add planned roadmap`.
- **Test:** Uruchomienie skryptu wyświetla propozycję commita wygenerowaną przez AI.

---

## ETAP 3: User Loop & Execution (Finał MVP)

- **Cel:** Użytkownik ma pełną kontrolę (Safety Net) i może zatwierdzić zmiany.
- **Kroki:**
  1.  Połącz etapy w głównej komendzie `@app.command()`.
  2.  Wyświetl propozycję w ramce (np. `--- PROPOZYCJA ---`).
  3.  Użyj `typer.confirm("Czy zrobić commit?")`.
  4.  **TAK:** Wykonaj `git commit -m "wiadomość"` i wyświetl sukces.
  5.  **NIE:** Wyświetl "Anulowano" i zakończ bez zmian w repozytorium.
- **Edge Cases:**
  - Pusty Stage (brak plików do commitowania) -> Wykryj to na początku (Etap 1) i nie pytaj AI o nic, tylko zakończ program.
- **Definicja Done:** Pełny proces: od diffa do nowego commita w historii Gita.
- **Test Integracyjny:**
  1. Zmień plik.
  2. `git add .`
  3. `python main.py`
  4. Wybierz 'y'.
  5. `git log` pokazuje nowy commit.

---

## ✅ Scenariusz Sukcesu (End-to-End)

1.  Użytkownik wprowadza zmiany w kodzie.
2.  Wpisuje w terminalu `sensei commit` (lub `python main.py`).
3.  Program sprawdza diff, wysyła do AI.
4.  Program wyświetla: `feat(core): implement main loop logic`.
5.  Użytkownik wciska `y`.
6.  Program commituje zmiany.

## ❌ Scenariusz Błędu (Safety Net)

1.  AI "halucynuje" i proponuje: `fix: repair database` (mimo że zmieniliśmy tylko CSS).
2.  Użytkownik widzi to i wciska `n`.
3.  Program kończy działanie. Żaden zły kod/opis nie trafia do historii projektu.
