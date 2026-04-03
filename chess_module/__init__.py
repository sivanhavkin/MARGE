"""Chess module for M@RGE — Claude vs GPT, Neural Network vs Stockfish, and mixed modes."""

try:
    from chess_module.chess_game import ChessGame
except ModuleNotFoundError as exc:
    if exc.name == "chess":
        ChessGame = None  # python-chess not installed
    else:
        raise

__all__ = []

if ChessGame is not None:
    __all__.append("ChessGame")

try:
    from chess_module.neural_agent import ChessNeuralAgent
except ImportError:
    pass
else:
    __all__.append("ChessNeuralAgent")


def __getattr__(name):
    if name == "ChessGame":
        raise ImportError(
            "ChessGame is not available because 'python-chess' is not installed.\n"
            "Install it with:  pip install python-chess"
        )
    if name == "ChessNeuralAgent":
        from chess_module.neural_agent import ChessNeuralAgent
        globals()[name] = ChessNeuralAgent
        return ChessNeuralAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
