import pedalboard as pb
from config import PARAM_LIMITS, EFFECT_ORDER


def _clamp(value: float, key: str) -> float:
    lo, hi = PARAM_LIMITS[key]
    return max(lo, min(hi, value))


def make_gain(gain_db: float) -> pb.Gain:
    return pb.Gain(gain_db=_clamp(gain_db, "gain_db"))


def make_eq(bands: list[dict]) -> list:
    plugins = []
    for b in bands:
        t = b["type"]
        f = _clamp(b["freq_hz"], "eq_freq_hz")
        g = _clamp(b.get("gain_db", 0), "eq_gain_db")
        q = _clamp(b.get("q", 0.707), "eq_q")

        if t == "highpass":
            plugins.append(pb.HighpassFilter(f))
        elif t == "lowpass":
            plugins.append(pb.LowpassFilter(f))
        elif t == "lowshelf":
            plugins.append(pb.LowShelfFilter(f, g, q))
        elif t == "highshelf":
            plugins.append(pb.HighShelfFilter(f, g, q))
        elif t == "peak":
            plugins.append(pb.PeakFilter(f, g, q))
        else:
            raise ValueError(f"Nieznany typ filtra EQ: {t}")
    return plugins


def make_compressor(threshold_db=-20, ratio=3, attack_ms=10, release_ms=100) -> pb.Compressor:
    return pb.Compressor(
        threshold_db=_clamp(threshold_db, "comp_threshold_db"),
        ratio=_clamp(ratio, "comp_ratio"),
        attack_ms=_clamp(attack_ms, "comp_attack_ms"),
        release_ms=_clamp(release_ms, "comp_release_ms"),
    )


def make_limiter(threshold_db=-1.0, release_ms=100) -> pb.Limiter:
    return pb.Limiter(
        threshold_db=_clamp(threshold_db, "limiter_threshold_db"),
        release_ms=_clamp(release_ms, "limiter_release_ms"),
    )


def build_pedalboard(chosen: dict) -> pb.Pedalboard:
    """chosen = {'eq': {...}, 'compressor': {...}, ...} - to, co zwrócił agent"""
    plugins = []
    for name in EFFECT_ORDER:
        if name not in chosen:
            continue
        if name == "eq":
            plugins.extend(make_eq(chosen["eq"]["bands"]))
        elif name == "compressor":
            plugins.append(make_compressor(**chosen["compressor"]))
        elif name == "gain":
            plugins.append(make_gain(chosen["gain"]["gain_db"]))
        elif name == "limiter":
            plugins.append(make_limiter(**chosen["limiter"]))
    return pb.Pedalboard(plugins)