"""
Streamlit chess UI for M@RGE.

Three game modes:
  1. Claude vs GPT
  2. Neural Network vs Stockfish (live training or inference)
  3. Claude/GPT vs Neural Network

Run with:
  streamlit run chess_module/streamlit_app.py
"""

import os
import random
import time
from typing import Optional

import chess
import chess.svg
import streamlit as st
from dotenv import load_dotenv

# Default Stockfish binary bundled with the project (Windows AVX2 build).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_STOCKFISH_PATH = os.path.join(
    _REPO_ROOT, "stockfish-windows-x86-64-avx2.exe"
)

load_dotenv()

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="M@RGE Chess", page_icon="♟️", layout="wide")


# ---------------------------------------------------------------------------
# Path validation helper
# ---------------------------------------------------------------------------
def _validated_stockfish_path(raw_path: str) -> Optional[str]:
    """
    Resolve and validate the Stockfish binary path provided by the user.
    Returns the sanitised absolute path, or None if the input is empty.
    Actual existence is verified by python-chess when the engine is opened.
    """
    if not raw_path or not raw_path.strip():
        return None
    # Resolve to an absolute, symlink-free path to prevent traversal attacks.
    # We intentionally do NOT call os.path.isfile here with the user value;
    # python-chess / subprocess will raise a clear error if the file is missing.
    return os.path.realpath(os.path.abspath(raw_path.strip()))

# ---------------------------------------------------------------------------
# Lazy imports (only loaded when needed)
# ---------------------------------------------------------------------------
@st.cache_resource
def get_openai_client():
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


@st.cache_resource
def get_anthropic_client():
    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


@st.cache_resource
def get_neural_agent():
    from chess_module.neural_agent import ChessNeuralAgent
    return ChessNeuralAgent()


# ---------------------------------------------------------------------------
# Player function factories
# ---------------------------------------------------------------------------
def make_gpt_player(label: str = "GPT"):
    """Return a player_fn that queries GPT for a chess move."""
    def _fn(fen: str, system_prompt: str) -> str:
        client = get_openai_client()
        if client is None:
            raise RuntimeError("OpenAI API key not configured")
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Current position (FEN): {fen}\nYour move:"},
            ],
            max_tokens=10,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    return _fn


def make_claude_player(label: str = "Claude"):
    """Return a player_fn that queries Claude for a chess move."""
    def _fn(fen: str, system_prompt: str) -> str:
        client = get_anthropic_client()
        if client is None:
            raise RuntimeError("Anthropic API key not configured")
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=20,
            system=system_prompt,
            messages=[
                {"role": "user", "content": f"Current position (FEN): {fen}\nYour move:"},
            ],
        )
        return response.content[0].text.strip()
    return _fn


@st.cache_resource
def _get_stockfish_engine(stockfish_path: str, skill_level: int):
    """Create (and cache) one Stockfish engine process per (path, skill) pair."""
    import chess.engine
    engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
    engine.configure({"Skill Level": skill_level})
    return engine


def make_stockfish_player(stockfish_path: str, skill_level: int = 5):
    """Return a player_fn backed by a cached (reused) Stockfish engine."""
    def _fn(fen: str, _system_prompt: str) -> str:
        engine = _get_stockfish_engine(stockfish_path, skill_level)
        board = chess.Board(fen)
        result = engine.play(board, chess.engine.Limit(time=0.1))
        return result.move.uci()
    return _fn


def make_nn_player():
    """Return a player_fn backed by the neural network agent."""
    agent = get_neural_agent()
    return agent.get_move_fn()


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------
def init_state():
    defaults = {
        "board": chess.Board(),
        "move_log": [],
        "game_over": False,
        "game_result": None,
        "last_move": None,
        "conversation": [],
        "running": False,
        "mode": None,
        "white_label": "White",
        "black_label": "Black",
        "white_fn": None,
        "black_fn": None,
        "training_log": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_game():
    st.session_state.board = chess.Board()
    st.session_state.move_log = []
    st.session_state.game_over = False
    st.session_state.game_result = None
    st.session_state.last_move = None
    st.session_state.conversation = []
    st.session_state.running = False


# ---------------------------------------------------------------------------
# Board rendering
# ---------------------------------------------------------------------------
def render_board(board: chess.Board, last_move: Optional[chess.Move] = None) -> str:
    return chess.svg.board(board, lastmove=last_move, size=400)


# ---------------------------------------------------------------------------
# Single-step move execution (called inside Streamlit loop)
# ---------------------------------------------------------------------------
def execute_one_move():
    """Execute the next half-move in the game and update session state."""
    board: chess.Board = st.session_state.board
    if board.is_game_over():
        st.session_state.game_over = True
        st.session_state.game_result = board.result()
        st.session_state.running = False
        return

    is_white = board.turn == chess.WHITE
    label = st.session_state.white_label if is_white else st.session_state.black_label
    player_fn = st.session_state.white_fn if is_white else st.session_state.black_fn

    from chess_module.chess_game import CHESS_SYSTEM_PROMPT
    fen = board.fen()
    raw_response = ""
    move = None

    for attempt in range(3):
        try:
            raw_response = player_fn(fen, CHESS_SYSTEM_PROMPT)
            uci_str = raw_response.strip().split()[0] if raw_response.strip() else ""
            candidate = chess.Move.from_uci(uci_str)
            if candidate in board.legal_moves:
                move = candidate
                break
        except Exception as exc:
            raw_response = f"[error attempt {attempt + 1}] {exc}"

    if move is None:
        legal = list(board.legal_moves)
        move = random.choice(legal)
        raw_response = f"[fallback random] {move.uci()}"

    board.push(move)
    st.session_state.last_move = move

    entry = {
        "move_number": len(st.session_state.move_log) + 1,
        "color": "white" if is_white else "black",
        "player": label,
        "move": move.uci(),
        "response": raw_response,
    }
    st.session_state.move_log.append(entry)
    st.session_state.conversation.append(f"**{label}** plays `{move.uci()}`  — _{raw_response}_")

    if board.is_game_over():
        st.session_state.game_over = True
        st.session_state.game_result = board.result()
        st.session_state.running = False

        from chess_module.chess_game import ChessGame, load_memory, save_memory
        from datetime import datetime
        memory = load_memory()
        if "chess_games" not in memory:
            memory["chess_games"] = []
        outcome = board.outcome()
        winner = None
        if outcome and outcome.winner is not None:
            winner = (
                st.session_state.white_label
                if outcome.winner == chess.WHITE
                else st.session_state.black_label
            )
        memory["chess_games"].append({
            "date": datetime.now().isoformat(),
            "white": st.session_state.white_label,
            "black": st.session_state.black_label,
            "result": board.result(),
            "winner": winner,
            "total_moves": len(st.session_state.move_log),
        })
        save_memory(memory)


# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------
def main():
    init_state()

    st.title("♟️ M@RGE Chess")
    st.markdown("Chess powered by M@RGE — AI vs AI, neural network vs Stockfish, and more.")

    # -----------------------------------------------------------------------
    # Sidebar — configuration
    # -----------------------------------------------------------------------
    with st.sidebar:
        st.header("⚙️ Configuration")

        mode = st.selectbox(
            "Game Mode",
            [
                "Claude vs GPT",
                "Neural Network vs Stockfish",
                "Claude vs Neural Network",
                "GPT vs Neural Network",
            ],
        )

        stockfish_path = None
        stockfish_skill = 5
        # Show Stockfish game controls only when Stockfish is used for actual play.
        if mode == "Neural Network vs Stockfish":
            raw_sf_path = st.text_input(
                "Stockfish binary path",
                value=os.getenv("STOCKFISH_PATH", _DEFAULT_STOCKFISH_PATH),
                help="Full path to the Stockfish executable",
            )
            stockfish_path = _validated_stockfish_path(raw_sf_path)
            stockfish_skill = st.slider("Stockfish Skill Level", 0, 20, 5)

        if "Neural Network" in mode:
            st.markdown("---")
            st.subheader("🧠 Neural Network Training")
            # For modes that don't use Stockfish for game play, provide a
            # separate path input so training can still be run.
            if mode != "Neural Network vs Stockfish":
                raw_sf_path_train = st.text_input(
                    "Stockfish path (for training)",
                    value=os.getenv("STOCKFISH_PATH", _DEFAULT_STOCKFISH_PATH),
                    help="Full path to the Stockfish executable used during NN training",
                )
                stockfish_path = _validated_stockfish_path(raw_sf_path_train)
            train_games = st.number_input("Training games", min_value=1, max_value=10000, value=100)
            train_btn = st.button("Train Neural Network")
            if train_btn:
                if not stockfish_path or not os.path.isfile(stockfish_path):
                    st.error("Valid Stockfish path required for training.")
                else:
                    agent = get_neural_agent()
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    def on_game_end(game_num, reward, log, loss):
                        pct = int(game_num / train_games * 100)
                        progress_bar.progress(pct)
                        result_str = "win" if reward > 0 else ("draw" if reward == 0 else "loss")
                        status_text.text(
                            f"Game {game_num}/{train_games} — {result_str} | "
                            f"Level: {log['stockfish_level']} | "
                            f"W/D/L: {log['wins']}/{log['draws']}/{log['losses']}"
                        )

                    agent.train(
                        num_games=int(train_games),
                        stockfish_path=stockfish_path,
                        on_game_end=on_game_end,
                    )
                    st.success("Training complete! Model saved.")
                    st.session_state.training_log = agent.log

            # Show training stats if available
            from chess_module.neural_agent import load_training_log
            tlog = load_training_log()
            if tlog["games_played"] > 0:
                st.metric("Games played", tlog["games_played"])
                total = tlog["games_played"]
                win_pct = tlog["wins"] / total * 100 if total else 0
                st.metric("Win rate", f"{win_pct:.1f}%")
                st.metric("Stockfish level", tlog["stockfish_level"])

        st.markdown("---")
        start_btn = st.button("▶️ Start / Reset Game", type="primary")
        step_btn = st.button("⏭️ Next Move (step)")
        auto_play = st.checkbox("Auto-play (continuous)")
        move_delay = st.slider("Delay between moves (s)", 0.0, 3.0, 0.5, 0.1)

    # -----------------------------------------------------------------------
    # Set up players on start
    # -----------------------------------------------------------------------
    if start_btn:
        reset_game()
        st.session_state.mode = mode

        if mode == "Claude vs GPT":
            st.session_state.white_fn = make_claude_player("Claude")
            st.session_state.black_fn = make_gpt_player("GPT")
            st.session_state.white_label = "Claude (White)"
            st.session_state.black_label = "GPT (Black)"

        elif mode == "Neural Network vs Stockfish":
            if not stockfish_path or not os.path.isfile(stockfish_path):
                st.error("Valid Stockfish path required.")
                st.stop()
            st.session_state.white_fn = make_nn_player()
            try:
                st.session_state.black_fn = make_stockfish_player(stockfish_path, stockfish_skill)
            except Exception as exc:
                st.error(f"Failed to start Stockfish: {exc}")
                st.stop()
            st.session_state.white_label = "Neural Network (White)"
            st.session_state.black_label = f"Stockfish L{stockfish_skill} (Black)"

        elif mode == "Claude vs Neural Network":
            st.session_state.white_fn = make_claude_player("Claude")
            st.session_state.black_fn = make_nn_player()
            st.session_state.white_label = "Claude (White)"
            st.session_state.black_label = "Neural Network (Black)"

        elif mode == "GPT vs Neural Network":
            st.session_state.white_fn = make_gpt_player("GPT")
            st.session_state.black_fn = make_nn_player()
            st.session_state.white_label = "GPT (White)"
            st.session_state.black_label = "Neural Network (Black)"

        st.session_state.running = True

    # -----------------------------------------------------------------------
    # Execute moves
    # -----------------------------------------------------------------------
    if st.session_state.white_fn is not None:
        if step_btn and not st.session_state.game_over:
            execute_one_move()

        if auto_play and st.session_state.running and not st.session_state.game_over:
            execute_one_move()
            time.sleep(move_delay)
            st.rerun()

    # -----------------------------------------------------------------------
    # Layout: board (left) + conversation (right)
    # -----------------------------------------------------------------------
    col_board, col_chat = st.columns([1, 1])

    with col_board:
        st.subheader("♟️ Board")
        svg = render_board(st.session_state.board, st.session_state.last_move)
        st.image(svg.encode(), use_container_width=False)

        if st.session_state.game_over:
            st.success(f"Game over! Result: **{st.session_state.game_result}**")

        turn_color = "White" if st.session_state.board.turn == chess.WHITE else "Black"
        if not st.session_state.game_over:
            st.caption(f"Turn: {turn_color} | Move {st.session_state.board.fullmove_number}")

    with col_chat:
        st.subheader("💬 Move Conversation")
        conversation_area = st.container()
        with conversation_area:
            if st.session_state.conversation:
                for line in reversed(st.session_state.conversation[-30:]):
                    st.markdown(line)
            else:
                st.info("Start a game to see the move conversation here.")

    # -----------------------------------------------------------------------
    # Move log (expandable)
    # -----------------------------------------------------------------------
    if st.session_state.move_log:
        with st.expander(f"📋 Move Log ({len(st.session_state.move_log)} moves)"):
            for entry in reversed(st.session_state.move_log):
                st.markdown(
                    f"**{entry['move_number']}.** {entry['player']}: `{entry['move']}` — {entry['response']}"
                )


if __name__ == "__main__":
    main()
