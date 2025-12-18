# 🚀 Propozycje Rozwoju Git-Sensei

Lista planowanych ulepszeń, zaktualizowana o strategię "Universal AI Adapter".

Stan obecny: 2 zrealizowane, 12 w planach.

## 1. 🛡️ Bezpieczeństwo i Stabilność (Shift-Left)
*   **🕵️ Secrets Shield z Analizą Entropii (Priorytet Strategiczny):**
    *   *Problem:* Regexy nie wyłapią niestandardowych kluczy API.
    *   *Rozwiązanie:* Hybrydowy skaner pre-flight (Regex + Analiza Entropii). Blokuje wysłanie diffa do zewnętrznego CLI, jeśli wykryje sekrety.
*   **Obsługa dużych Diffów (Smart Truncation):**
    *   *Rozwiązanie:* Inteligentne filtrowanie plików (lockfiles, duże CSV) z potoku danych, aby nie przekroczyć limitów tokenów w CLI dostawcy.

## 2. 🧠 User Experience & AI (Augmented Dev)
*   ✅ **Tryb Edycji [E]dit (ZROBIONE):**
    *   *Rozwiązanie:* Inline'owa edycja wiadomości w terminalu.
*   **🎲 Interaktywne Przelosowanie ([R]etry):**
    *   *Nowość:* Opcja `Action? [r]etry`. Pozwala odrzucić propozycję i poprosić AI o inną wersję (np. "krócej", "po polsku").
*   **🔪 Atomic Commit Splitter:**
    *   *Metoda:* Wykorzystanie promptingu CoT. AI analizuje zależności i proponuje rozbicie jednego diffa na logiczne, atomowe commity (interaktywne `git add -p`).

## 3. Workflow i Integracje
*   ✅ **Smart Context & Traceability (ZROBIONE):**
    *   *Rozwiązanie:* Parsowanie ID zadania z brancha (`Refs: PROJ-123`).
*   **🪝 Native Git Hook:**
    *   *Nowość:* Komenda `sensei install-hook`. Podpina narzędzie pod `prepare-commit-msg`.
*   **📊 Sensei Audit:**
    *   *Nowość:* Analiza historii projektu i raportowanie jakości commitów.

## 4. 🔌 Architektura Uniwersalna (BYO-CLI) - ZREALIZOWANE
*✅ **⚙️ Konfiguracja Oparta na Szablonach (`.sensei.toml`):**
    *   *Zrealizowane:* Użytkownik definiuje własne komendy z placeholderem `{system}`.
*✅ **🔑 Bring Your Own Auth (BYOA):**
    *   *Zrealizowane:* Sensei korzysta z zalogowanych sesji zewnętrznych CLI.
*✅ **🩺 Sensei Doctor (`sensei doctor`):**
    *   *Zrealizowane:* Diagnostyka poprawności ścieżek i plików wykonywalnych.
*✅ **📘 Dynamiczny Help (`sensei --help`):**
    *   *Zrealizowane:* Opis Quick Start sugerujący `sensei commit`.
