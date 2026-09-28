import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
STORAGE_ROOT = os.environ["STORAGE_ROOT"]

MODEL_NAME = "deepseek-v4-flash"

EFFECT_ORDER = ["eq", "compressor", "gain", "limiter"]

SAFETY_LIMITER_THRESHOLD_DB = -0.3
SAFETY_LIMITER_RELEASE_MS = 100

PARAM_LIMITS = {
    "gain_db": (-24, 24),
    "eq_freq_hz": (20, 20000),
    "eq_gain_db": (-18, 18),
    "eq_q": (0.1, 10),
    "comp_threshold_db": (-60, 0),
    "comp_ratio": (1, 20),
    "comp_attack_ms": (0.1, 200),
    "comp_release_ms": (5, 2000),
    "limiter_threshold_db": (-12, 0),
    "limiter_release_ms": (5, 1000),
}