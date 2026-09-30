# Zmiany wykonane w backendzie SoundCraft

Ten dokument opisuje zmiany funkcjonalne i architektoniczne wprowadzone podczas
integracji backendu z orkiestratorem i środowiskiem WCSS. Nie jest instrukcją
implementacyjną i nie zawiera fragmentów kodu.

## Cel zmian

Backend został przekształcony z prostego serwera obsługującego upload w warstwę
łączącą interfejs użytkownika na laptopie z asynchronicznym pipeline'em audio
działającym na WCSS. Odpowiada teraz za utworzenie zlecenia, transfer plików,
oczekiwanie na zakończenie, pobranie rezultatów i poinformowanie interfejsu.

## Konfiguracja

- Dodano obsługę wspólnego lokalnego pliku konfiguracyjnego YAML.
- Konfiguracja obejmuje host WCSS, login, katalog zdalny, klucz SSH, port,
  token callbacku oraz limity czasu przetwarzania.
- Sekrety i konfiguracja konkretnego użytkownika są wyłączone z repozytorium.
- Dodano osobny tryb demonstracyjny, który nie wymaga połączenia z WCSS ani GPU.
- Lista dozwolonych originów frontendu jest konfigurowalna zamiast być trwale
  związana z jednym adresem.

## Przyjmowanie zleceń

- Rozdzielono wysyłanie audio od wysyłania promptu.
- Każde zlecenie otrzymuje unikalny identyfikator UUID.
- Backend przygotowuje strukturę katalogów zgodną z kontraktem workera WCSS.
- Plik wejściowy jest normalizowany do formatu WAV wymaganego przez pipeline.
- Prompt jest zapisywany razem z identyfikatorem, czasem utworzenia i terminem
  wygaśnięcia zlecenia.
- Dodano walidację identyfikatorów oraz pustych promptów.

## Transfer laptop–WCSS

- Podstawowym transportem jest SSH/rsync.
- Dodano automatyczny fallback do SFTP, gdy rsync lub SSH nie działa.
- Klucz prywatny i port SSH są pobierane z konfiguracji.
- Po awarii obu transportów uruchamiany jest cooldown. Backend nie ponawia wtedy
  połączeń przy każdym odpytywaniu interfejsu i nie bombarduje serwera WCSS.
- Skrócono ścieżkę gniazda współdzielonego połączenia SSH, aby działała w
  ograniczeniach długości ścieżek systemu macOS.
- Nieudany transfer nie powoduje dodatkowych prób usuwania danych na WCSS.

## Informacja o zakończeniu przetwarzania

- Dodano wewnętrzny callback wysyłany przez worker po zakończeniu pipeline'u.
- Callback zawiera identyfikator zlecenia, status wykonania i informację, czy
  plik audio jest gotowy.
- Callback jest zabezpieczony wspólnym tokenem Bearer.
- Token jest porównywany w sposób odporny na analizę czasu porównania.
- Niepoprawny identyfikator, brak konfiguracji i błędny token są odrzucane.

## Publiczny gateway callbacku

- Dodano osobny, minimalny serwer przeznaczony do wystawienia przez Cloudflare.
- Gateway nie udostępnia uploadu, plików wynikowych ani całego API backendu.
- Udostępnia jedynie kontrolę stanu oraz przyjęcie informacji o zakończeniu.
- Po odebraniu poprawnego żądania przekazuje je lokalnie do właściwego backendu.
- Dzięki temu publicznie dostępna powierzchnia aplikacji jest ograniczona.

## WebSocket i aktualizacja UI

- Dodano WebSocket oczekujący na zakończenie konkretnego requestu.
- Callback budzi oczekujące połączenie i natychmiast przekazuje status do UI.
- Informacja o ukończeniu jest przechowywana przez ograniczony czas, dlatego
  później otwarty WebSocket również może otrzymać wynik.
- Oczekiwanie ma konfigurowalny timeout i nie trwa bez końca.
- Zastąpiono częste odpytywanie WCSS pojedynczym callbackiem po zakończeniu.

## Pobieranie rezultatów

- Backend wyszukuje najnowszą odpowiedź agenta dla danego requestu.
- Po sukcesie pobiera najnowszy końcowy plik audio z WCSS.
- Audio jest pobierane dopiero wtedy, gdy interfejs o nie poprosi; callback nie
  przenosi dużych plików.
- Wynik z WCSS jest przekazywany do przeglądarki jako plik WAV.
- Dla nieudanego pipeline'u UI otrzymuje informację o błędzie bez pliku audio.
- Zachowano możliwość usunięcia danych związanych z konkretnym requestem.

## Obsługa błędów

- Błąd callbacku nie zmienia poprawnego rezultatu pipeline'u na wynik
  nieudany.
- Plik WAV i raport pozostają na WCSS nawet wtedy, gdy laptop jest chwilowo
  niedostępny.
- Rozróżniono błędy uwierzytelnienia, brak rezultatu, timeout oraz awarie
  transportu.
- Ograniczono liczbę ponowień oraz całkowity czas prób callbacku.
- Backend nie uruchamia dodatkowych operacji SSH podczas sprzątania po błędzie
  uploadu.

## Tryb demonstracyjny

- Dodano lokalny przebieg demonstracyjny bez WCSS i modeli GPU.
- Tryb demo korzysta z tego samego kontraktu uploadu, odpowiedzi, WebSocketu i
  pobierania rezultatu co tryb produkcyjny.
- Umożliwia sprawdzenie integracji frontend–backend przed testami klastra.

## Testy

- Dodano testy autoryzacji callbacku.
- Dodano testy callbacku połączonego z WebSocketem.
- Sprawdzono przypadek, w którym callback pojawia się przed połączeniem UI.
- Dodano testy gatewaya i przekazywania żądania do backendu.
- Dodano testy przełączania z rsync na SFTP.
- Dodano test cooldownu po całkowitej awarii transportu.
- Sprawdzono użycie skonfigurowanego klucza i portu SSH.
- Dodano test pełnego lokalnego przebiegu demo.

## Zmiany przygotowane na gałęzi SoundCraftWindows

Osobna gałąź Windows rozszerza backend o następujące zachowania:

- lokalne pliki tymczasowe trafiają do systemowego katalogu TEMP zamiast do
  katalogu charakterystycznego dla systemów Unix;
- brak funkcji identyfikatora użytkownika z systemów Unix nie blokuje startu;
- gdy rsync nie jest zainstalowany, backend przechodzi bezpośrednio do SFTP;
- awaria samego SFTP nadal uruchamia cooldown;
- launcher rozpoznaje windowsowe polecenie npm i zamyka całe drzewo procesów;
- dodano testy regresyjne dla zachowania backendu na Windows.

## Ograniczenia obecnego rozwiązania

- Rejestr ukończonych callbacków jest przechowywany w pamięci procesu i znika
  po restarcie backendu.
- Worker używa jednego globalnego adresu callbacku, dlatego jednocześnie może
  aktywnie powiadamiać tylko jeden backend/laptop.
- Adres szybkiego tunelu Cloudflare zmienia się po ponownym uruchomieniu tunelu.
- Pliki wynikowe pozostają na WCSS do momentu jawnego usunięcia requestu.
- Pełna współbieżna obsługa wielu laptopów wymaga callbacku przypisanego osobno
  do każdego requestu albo wspólnego, stale dostępnego backendu.
