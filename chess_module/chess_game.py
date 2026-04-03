"""
Chess game between Claude and GPT (or mixed with Neural Network).
Uses python-chess for board management, move validation, and SVG rendering.
Logs all moves and responses to shared memory JSON.
"""

import json
import os
import re
import random
from datetime import datetime
from typing import Optional, Callable

import chess
import chess.svg

MEMORY_FILE = "shared_memory.json"

CHESS_SYSTEM_PROMPT = """You are playing chess. The board state will be given to you as a FEN string.

Chess rules reminder:
- Respond with a single legal UCI move in the format: source_square + destination_square.
- UCI format uses file (a-h) and rank (1-8), e.g. e2e4 means the piece on e2 moves to e4.
- For pawn promotion, append the piece letter: a7a8q (queen), a7a8r (rook), a7a8b (bishop), a7a8n (knight).
- Do NOT use algebraic notation like Nf3 or exd4 — always use the full source+destination form.
- Do not include any explanation — respond with ONLY the UCI move string.

Example responses: e2e4  |  d7d5  |  g1f3  |  e1g1  |  a7a8q
"""

# Regex that matches a UCI move substring anywhere in model output (lowercase text).
_UCI_RE = re.compile(r'\b([a-h][1-8][a-h][1-8][qrbn]?)\b')

# Characters commonly wrapping tokens in LLM output that are not part of a move.
_STRIP_CHARS = ".,!?;:()[]`'\""


def parse_move_from_response(board: chess.Board, raw: str) -> Optional[chess.Move]:
    """Extract the first legal move from a model response.

    Tries in order:
    1. First whitespace-separated token parsed as UCI (lowercased).
    2. Any UCI-looking substring found via regex on the lowercased text.
    3. Each token parsed as SAN (handles Nf3, exd4, etc.) after stripping
       surrounding punctuation, backticks, and quotes.

    Returns a chess.Move on success, or None if no legal move can be found.
    """
    text = raw.strip()
    if not text:
        return None

    # 1. First token as UCI (normalize to lowercase)
    first_token = text.split()[0].strip(_STRIP_CHARS).lower()
    try:
        return board.parse_uci(first_token)
    except (chess.InvalidMoveError, chess.IllegalMoveError, ValueError):
        pass

    # 2. Regex search for UCI-format substring (search on lowercased text)
    for m in _UCI_RE.finditer(text.lower()):
        try:
            return board.parse_uci(m.group(1).lower())
        except (chess.InvalidMoveError, chess.IllegalMoveError, ValueError):
            continue

    # 3. Try SAN parsing on each token (strip surrounding non-move characters)
    for token in text.split():
        token_clean = token.strip(_STRIP_CHARS)
        try:
            return board.parse_san(token_clean)
        except (chess.InvalidMoveError, chess.IllegalMoveError, ValueError):
            continue

    return None


def load_memory() -> dict:
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sessions": [], "field": "", "chess_games": []}


def save_memory(memory: dict) -> None:
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


class ChessGame:
    """Manages a chess game between two AI agents (Claude/GPT/Neural Network)."""

    def __init__(
        self,
        player_white_fn: Callable[[str, str], str],
        player_black_fn: Callable[[str, str], str],
        player_white_label: str = "White",
        player_black_label: str = "Black",
        on_move: Optional[Callable] = None,
    ):
        """
        Args:
            player_white_fn: callable(fen, system_prompt) -> uci_move_string
            player_black_fn: callable(fen, system_prompt) -> uci_move_string
            player_white_label: display name for white
            player_black_label: display name for black
            on_move: optional callback(board, move, label, response) called after each move
        """
        self.player_white_fn = player_white_fn
        self.player_black_fn = player_black_fn
        self.player_white_label = player_white_label
        self.player_black_label = player_black_label
        self.on_move = on_move
        self.board = chess.Board()
        self.move_log: list[dict] = []

    def _request_move(self, player_fn: Callable, label: str) -> tuple[chess.Move, str]:
        """Ask player for a move, retry up to 3 times, then fall back to random."""
        fen = self.board.fen()
        raw_response = ""
        for attempt in range(3):
            try:
                raw_response = player_fn(fen, CHESS_SYSTEM_PROMPT)
                move = parse_move_from_response(self.board, raw_response)
                if move is not None:
                    return move, raw_response
            except Exception as exc:
                raw_response = f"[error attempt {attempt + 1}] {exc}"
        # Fall back to a random legal move
        legal = list(self.board.legal_moves)
        move = random.choice(legal)
        raw_response = f"[fallback random] {move.uci()}"
        return move, raw_response

    def get_board_svg(self, last_move: Optional[chess.Move] = None) -> str:
        """Return SVG string for the current board state."""
        return chess.svg.board(
            self.board,
            lastmove=last_move,
            size=400,
        )

    def play_game(self) -> dict:
        """Play a full game. Returns game result dict."""
        self.board = chess.Board()
        self.move_log = []

        while not self.board.is_game_over():
            is_white = self.board.turn == chess.WHITE
            label = self.player_white_label if is_white else self.player_black_label
            player_fn = self.player_white_fn if is_white else self.player_black_fn

            move, response = self._request_move(player_fn, label)
            self.board.push(move)

            entry = {
                "move_number": len(self.move_log) + 1,
                "color": "white" if is_white else "black",
                "player": label,
                "move": move.uci(),
                "response": response,
                "fen_after": self.board.fen(),
            }
            self.move_log.append(entry)

            if self.on_move:
                self.on_move(self.board, move, label, response)

        result = self.board.result()
        outcome = self.board.outcome()
        winner = None
        if outcome and outcome.winner is not None:
            winner = self.player_white_label if outcome.winner == chess.WHITE else self.player_black_label

        game_record = {
            "date": datetime.now().isoformat(),
            "white": self.player_white_label,
            "black": self.player_black_label,
            "result": result,
            "winner": winner,
            "total_moves": len(self.move_log),
            "moves": self.move_log,
        }

        self._log_to_memory(game_record)
        return game_record

    def _log_to_memory(self, game_record: dict) -> None:
        """Append game record to shared memory JSON."""
        memory = load_memory()
        if "chess_games" not in memory:
            memory["chess_games"] = []
        memory["chess_games"].append(game_record)
        save_memory(memory)
