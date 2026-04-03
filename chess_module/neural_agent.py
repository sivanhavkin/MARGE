"""
Neural network chess agent using PyTorch.
Learns to play chess via policy gradient reinforcement learning against Stockfish.

Architecture:
  Input : 8×8×12 tensor (one plane per piece type / colour)
  Output: probability distribution over 4096 move indices (from_sq * 64 + to_sq)

Training loop:
  - Play full game vs Stockfish
  - +1 reward on win, -1 on loss, 0 on draw
  - Update weights with REINFORCE (policy gradient) after each game
  - Save model every 100 games
  - Increase Stockfish skill level when win-rate over last 50 games > 30 %
"""

import json
import os
import random
from datetime import datetime
from typing import Callable, Optional

import chess
import chess.engine
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_SAVE_PATH = os.path.join(_MODULE_DIR, "nn_chess_model.pt")
TRAINING_LOG_FILE = os.path.join(_MODULE_DIR, "nn_training_log.json")
NUM_PLANES = 12          # 6 piece types × 2 colours
# Action space: 4096 non-promotion indices (from_sq*64 + to_sq) +
# four additional tiers of 4096 each, one per promo piece (Q/R/B/N).
_NUM_BASE_MOVES = 64 * 64          # 4096
_NUM_PROMO_TYPES = 4               # queen, rook, bishop, knight
NUM_MOVES = _NUM_BASE_MOVES * (_NUM_PROMO_TYPES + 1)  # 20480

_PROMO_PIECES = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
_PROMO_PIECE_TO_IDX = {p: i for i, p in enumerate(_PROMO_PIECES)}


PIECE_TO_PLANE = {
    (chess.PAWN,   chess.WHITE): 0,
    (chess.KNIGHT, chess.WHITE): 1,
    (chess.BISHOP, chess.WHITE): 2,
    (chess.ROOK,   chess.WHITE): 3,
    (chess.QUEEN,  chess.WHITE): 4,
    (chess.KING,   chess.WHITE): 5,
    (chess.PAWN,   chess.BLACK): 6,
    (chess.KNIGHT, chess.BLACK): 7,
    (chess.BISHOP, chess.BLACK): 8,
    (chess.ROOK,   chess.BLACK): 9,
    (chess.QUEEN,  chess.BLACK): 10,
    (chess.KING,   chess.BLACK): 11,
}


# ---------------------------------------------------------------------------
# Board encoding
# ---------------------------------------------------------------------------
def board_to_tensor(board: chess.Board) -> torch.Tensor:
    """Encode a chess.Board as a (12, 8, 8) float32 tensor."""
    tensor = torch.zeros(NUM_PLANES, 8, 8, dtype=torch.float32)
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is not None:
            plane = PIECE_TO_PLANE[(piece.piece_type, piece.color)]
            row = sq // 8
            col = sq % 8
            tensor[plane, row, col] = 1.0
    return tensor


def move_to_index(move: chess.Move) -> int:
    """Encode a move as an integer index in [0, NUM_MOVES).

    Non-promotion: from_sq * 64 + to_sq  (range 0 – 4095)
    Promotion    : _NUM_BASE_MOVES + promo_idx * _NUM_BASE_MOVES
                   + from_sq * 64 + to_sq  (range 4096 – 20479)
    """
    base = move.from_square * 64 + move.to_square
    if move.promotion:
        promo_idx = _PROMO_PIECE_TO_IDX[move.promotion]
        return _NUM_BASE_MOVES + promo_idx * _NUM_BASE_MOVES + base
    return base


def index_to_move(idx: int) -> chess.Move:
    """Decode an integer index back to a chess.Move (inverse of move_to_index)."""
    if idx >= _NUM_BASE_MOVES:
        idx -= _NUM_BASE_MOVES
        promo_idx = idx // _NUM_BASE_MOVES
        base = idx % _NUM_BASE_MOVES
        from_sq = base // 64
        to_sq = base % 64
        return chess.Move(from_sq, to_sq, promotion=_PROMO_PIECES[promo_idx])
    from_sq = idx // 64
    to_sq = idx % 64
    return chess.Move(from_sq, to_sq)


# ---------------------------------------------------------------------------
# Neural network model
# ---------------------------------------------------------------------------
class ChessNet(nn.Module):
    """Convolutional policy network for chess."""

    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(NUM_PLANES, 64, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(128, 128, kernel_size=3, padding=1)
        self.fc1 = nn.Linear(128 * 8 * 8, 1024)
        self.fc2 = nn.Linear(1024, NUM_MOVES)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = x.view(x.size(0), -1)
        x = F.relu(self.fc1(x))
        return self.fc2(x)  # raw logits — softmax applied during move selection


# ---------------------------------------------------------------------------
# Training log helpers
# ---------------------------------------------------------------------------
def load_training_log() -> dict:
    if os.path.exists(TRAINING_LOG_FILE):
        with open(TRAINING_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "stockfish_level": 1,
        "history": [],
    }


def save_training_log(log: dict) -> None:
    os.makedirs(os.path.dirname(TRAINING_LOG_FILE), exist_ok=True)
    with open(TRAINING_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class ChessNeuralAgent:
    """Policy-gradient RL agent that plays chess and trains against Stockfish."""

    def __init__(
        self,
        stockfish_path: Optional[str] = None,
        lr: float = 1e-4,
        device: Optional[str] = None,
    ):
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model = ChessNet().to(self.device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr)
        self.stockfish_path = stockfish_path
        self.log = load_training_log()
        self._load_model()

    # ------------------------------------------------------------------
    # Model persistence
    # ------------------------------------------------------------------
    def _load_model(self) -> None:
        if os.path.exists(MODEL_SAVE_PATH):
            state = torch.load(MODEL_SAVE_PATH, map_location=self.device)
            self.model.load_state_dict(state)

    def save_model(self) -> None:
        os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
        torch.save(self.model.state_dict(), MODEL_SAVE_PATH)

    # ------------------------------------------------------------------
    # Move selection (inference)
    # ------------------------------------------------------------------
    def select_move(self, board: chess.Board) -> chess.Move:
        """Select a legal move using the policy network."""
        self.model.eval()
        with torch.no_grad():
            tensor = board_to_tensor(board).unsqueeze(0).to(self.device)
            logits = self.model(tensor).squeeze(0)  # shape (4096,)

        legal_moves = list(board.legal_moves)
        legal_indices = [move_to_index(m) for m in legal_moves]

        # Mask illegal moves
        mask = torch.full((NUM_MOVES,), float("-inf"), device=self.device)
        for idx in legal_indices:
            mask[idx] = 0.0

        masked_logits = logits + mask
        probs = F.softmax(masked_logits, dim=0)

        chosen_idx = torch.multinomial(probs, 1).item()
        chosen_move = index_to_move(chosen_idx)

        # Ensure the selected move is actually legal (handles promotion edge-cases)
        if chosen_move not in board.legal_moves:
            chosen_move = random.choice(legal_moves)

        return chosen_move

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------
    def _collect_episode(
        self,
        stockfish_engine: chess.engine.SimpleEngine,
        stockfish_level: int,
        nn_color: chess.Color,
    ) -> tuple[list[torch.Tensor], list[torch.Tensor], float]:
        """
        Play one full game. Returns (log_probs, entropies, reward).
        Neural net plays as nn_color, Stockfish plays the other side.
        """
        board = chess.Board()
        log_probs: list[torch.Tensor] = []
        entropies: list[torch.Tensor] = []

        stockfish_engine.configure({"Skill Level": stockfish_level})

        while not board.is_game_over():
            if board.turn == nn_color:
                # NN's turn
                self.model.train()
                tensor = board_to_tensor(board).unsqueeze(0).to(self.device)
                logits = self.model(tensor).squeeze(0)

                legal_moves = list(board.legal_moves)
                legal_indices = [move_to_index(m) for m in legal_moves]

                mask = torch.full((NUM_MOVES,), float("-inf"), device=self.device)
                for idx in legal_indices:
                    mask[idx] = 0.0

                masked_logits = logits + mask
                probs = F.softmax(masked_logits, dim=0)

                chosen_idx = torch.multinomial(probs, 1)
                move_idx = chosen_idx.item()
                chosen_move = index_to_move(move_idx)
                # With correct promotion encoding every legal move has a unique
                # index, so the fallback should not trigger in practice.
                # It is kept as a guard against any future encoding edge-cases;
                # log_prob is recomputed for the actually executed move so the
                # REINFORCE gradient is always correct.
                if chosen_move not in board.legal_moves:
                    chosen_move = random.choice(legal_moves)
                    move_idx = move_to_index(chosen_move)
                log_prob = torch.log(probs[move_idx] + 1e-8)
                entropy = -(probs * torch.log(probs + 1e-8)).sum()

                log_probs.append(log_prob)
                entropies.append(entropy)

                board.push(chosen_move)
            else:
                # Stockfish's turn
                result = stockfish_engine.play(board, chess.engine.Limit(time=0.05))
                board.push(result.move)

        outcome = board.outcome()
        if outcome is None:
            reward = 0.0
        elif outcome.winner == nn_color:
            reward = 1.0
        elif outcome.winner is None:
            reward = 0.0
        else:
            reward = -1.0

        return log_probs, entropies, reward

    def _update_policy(
        self,
        log_probs: list[torch.Tensor],
        entropies: list[torch.Tensor],
        reward: float,
        entropy_coeff: float = 0.01,
    ) -> float:
        """REINFORCE policy gradient update. Returns scalar loss value."""
        if not log_probs:
            return 0.0

        policy_loss = torch.stack([-lp * reward for lp in log_probs]).sum()
        entropy_bonus = torch.stack(entropies).sum()
        loss = policy_loss - entropy_coeff * entropy_bonus

        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        self.optimizer.step()
        return loss.item()

    def train(
        self,
        num_games: int = 500,
        stockfish_path: Optional[str] = None,
        on_game_end: Optional[Callable] = None,
    ) -> dict:
        """
        Train the agent against Stockfish for num_games games.

        Args:
            num_games: number of training games to play
            stockfish_path: override path to stockfish binary
            on_game_end: optional callback(game_num, reward, log, loss) for UI updates

        Returns:
            final training log dict
        """
        sf_path = stockfish_path or self.stockfish_path
        if sf_path is None:
            raise ValueError("stockfish_path must be provided for training")

        engine = chess.engine.SimpleEngine.popen_uci(sf_path)
        try:
            for game_num in range(1, num_games + 1):
                # Alternate colours each game
                nn_color = chess.WHITE if game_num % 2 == 1 else chess.BLACK
                level = self.log["stockfish_level"]

                log_probs, entropies, reward = self._collect_episode(engine, level, nn_color)
                loss = self._update_policy(log_probs, entropies, reward)

                # Update statistics
                self.log["games_played"] += 1
                if reward > 0:
                    self.log["wins"] += 1
                elif reward < 0:
                    self.log["losses"] += 1
                else:
                    self.log["draws"] += 1

                self.log["history"].append({
                    "game": self.log["games_played"],
                    "reward": reward,
                    "loss": loss,
                    "level": level,
                    "date": datetime.now().isoformat(),
                })

                # Check win-rate over last 50 games to maybe increase difficulty
                recent = self.log["history"][-50:]
                if len(recent) == 50:
                    win_rate = sum(1 for e in recent if e["reward"] > 0) / 50
                    if win_rate > 0.30 and self.log["stockfish_level"] < 20:
                        self.log["stockfish_level"] += 1

                # Save model every 100 games
                if self.log["games_played"] % 100 == 0:
                    self.save_model()
                    save_training_log(self.log)

                if on_game_end:
                    on_game_end(game_num, reward, self.log, loss)

        finally:
            engine.quit()

        self.save_model()
        save_training_log(self.log)
        return self.log

    # ------------------------------------------------------------------
    # Inference wrapper (compatible with ChessGame player_fn signature)
    # ------------------------------------------------------------------
    def get_move_fn(self):
        """Return a callable compatible with ChessGame's player_fn interface."""
        def _fn(fen: str, _system_prompt: str) -> str:
            board = chess.Board(fen)
            move = self.select_move(board)
            return move.uci()
        return _fn
