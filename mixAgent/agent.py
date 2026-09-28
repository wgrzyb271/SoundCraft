import json
from openai import OpenAI
from .config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL_NAME

TOOLS = [
    {"type": "function", "function": {
        "name": "gain",
        "description": "Zmienia głośność całej ścieżki (wzmocnienie/osłabienie w dB).",
        "parameters": {"type": "object", "properties": {
            "gain_db": {"type": "number", "minimum": -24, "maximum": 24}
        }, "required": ["gain_db"]}}},

    {"type": "function", "function": {
        "name": "eq",
        "description": "Korekcja częstotliwościowa - lista pasm filtrów.",
        "parameters": {"type": "object", "properties": {
            "bands": {"type": "array", "items": {"type": "object", "properties": {
                "type": {"type": "string", "enum": ["highpass", "lowpass", "lowshelf", "highshelf", "peak"]},
                "freq_hz": {"type": "number", "minimum": 20, "maximum": 20000},
                "gain_db": {"type": "number", "minimum": -18, "maximum": 18},
                "q": {"type": "number", "minimum": 0.1, "maximum": 10}
            }, "required": ["type", "freq_hz"]}}
        }, "required": ["bands"]}}},

    {"type": "function", "function": {
        "name": "compressor",
        "description": "Kompresja dynamiki - wyrównuje różnice między cichymi a głośnymi fragmentami.",
        "parameters": {"type": "object", "properties": {
            "threshold_db": {"type": "number", "minimum": -60, "maximum": 0},
            "ratio": {"type": "number", "minimum": 1, "maximum": 20},
            "attack_ms": {"type": "number", "minimum": 0.1, "maximum": 200},
            "release_ms": {"type": "number", "minimum": 5, "maximum": 2000}
        }, "required": ["threshold_db", "ratio"]}}},

    {"type": "function", "function": {
        "name": "limiter",
        "description": "Zabezpiecza przed przesterowaniem, ogranicza szczyty głośności. Zwykle ostatni etap.",
        "parameters": {"type": "object", "properties": {
            "threshold_db": {"type": "number", "minimum": -12, "maximum": 0},
            "release_ms": {"type": "number", "minimum": 5, "maximum": 1000}
        }, "required": ["threshold_db"]}}},
]

SYSTEM_PROMPT = """Jesteś inżynierem miksu audio. Na podstawie prośby użytkownika
zdecyduj, których narzędzi (gain, eq, compressor, limiter) użyć i z jakimi
parametrami DLA TEGO KONKRETNEGO STEMU.

WAŻNE: Jeśli prośba użytkownika nie dotyczy danego stemu (np. user prosi o zmiany
w wokalu, a przetwarzasz bas), NIE stosuj żadnych efektów - zwróć pustą odpowiedź
bez wywoływania narzędzi, chyba że stem wymaga tego z innego wyraźnego powodu.
Nie stosuj efektów "na wszelki wypadek" ani żeby być spójnym z innymi stemami."""

def decide_effects(user_prompt: str, stem_name: str, client: OpenAI | None = None) -> dict:
    """Zwraca np. {'gain': {'gain_db': 3}, 'compressor': {...}}"""

    if client is None:
        if not DEEPSEEK_API_KEY:
            raise RuntimeError("mixAgent wymaga DEEPSEEK_API_KEY dla promptu zawierającego efekty")
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

    full_prompt = f"Aktualnie przetwarzana ścieżka: {stem_name}.\n\nProśba użytkownika: {user_prompt}"

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": full_prompt},
        ],
        tools=TOOLS,
    )

    chosen = {}
    calls = resp.choices[0].message.tool_calls or []
    for call in calls:
        try:
            chosen[call.function.name] = json.loads(call.function.arguments)
        except json.JSONDecodeError:
            continue 

    return chosen
