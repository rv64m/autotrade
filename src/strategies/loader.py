"""
Strategy loader for autotrade.

Usage:
    from src.strategies.loader import load_strategy, load_kept_strategies

    # Load a specific strategy by filename
    cls = load_strategy("ema_crossover_4h.py")

    # Load all strategies marked keep=True
    kept = load_kept_strategies()
"""

import importlib
from pathlib import Path

from src.strategies.base import BaseStrategy

_GENERATED_PKG = "src.strategies.generated"
_GENERATED_DIR = Path(__file__).parent / "generated"


def load_strategy(filename: str) -> type[BaseStrategy]:
    """Load a strategy class from src/strategies/generated/<filename>.

    Expects exactly one BaseStrategy subclass in the file.
    """
    module_name = filename.removesuffix(".py")
    module = importlib.import_module(f"{_GENERATED_PKG}.{module_name}")

    candidates = [
        obj
        for name in dir(module)
        if not name.startswith("_")
        for obj in (getattr(module, name),)
        if isinstance(obj, type)
        and issubclass(obj, BaseStrategy)
        and obj is not BaseStrategy
    ]
    if not candidates:
        raise ValueError(f"No BaseStrategy subclass found in {filename}")
    if len(candidates) > 1:
        raise ValueError(
            f"Multiple BaseStrategy subclasses found in {filename}: "
            + ", ".join(c.__name__ for c in candidates)
        )
    return candidates[0]


def load_kept_strategies() -> list[type[BaseStrategy]]:
    """Return all strategy classes with keep=True from the generated directory."""
    strategies: list[type[BaseStrategy]] = []
    for path in sorted(_GENERATED_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        try:
            cls = load_strategy(path.name)
            if cls.keep:
                strategies.append(cls)
        except Exception:
            pass
    return strategies
