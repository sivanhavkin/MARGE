"""Chess module for M@RGE — Claude vs GPT, Neural Network vs Stockfish, and mixed modes."""

from chess_module.chess_game import ChessGame


def __getattr__(name):
    if name == "ChessNeuralAgent":
        from chess_module.neural_agent import ChessNeuralAgent
        return ChessNeuralAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["ChessGame", "ChessNeuralAgent"]
