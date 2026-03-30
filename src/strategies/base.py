from backtesting import Strategy


class BaseStrategy(Strategy):
    """Base class for all autotrade strategies.

    Subclasses must set `description` and may set `keep = True` to mark
    the strategy as a keeper. The loader uses `keep` to filter strategies.
    """

    description: str = ""
    keep: bool = False

    def init(self) -> None:
        pass

    def next(self) -> None:
        pass
