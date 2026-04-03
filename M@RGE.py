import os
import json
import subprocess
import sys
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import anthropic

load_dotenv()

MEMORY_FILE = "shared_memory.json"
IDENTITY_FILE = "agent_identity.json"
NEXT_SYSTEM_FILE = "next_system.txt"
SYSTEM_BASE_FILE = "system_base.txt"
ALLOWED_WRITES = [IDENTITY_FILE, NEXT_SYSTEM_FILE, "notes.txt"]
BLOCKED_IMPORTS = ["os", "subprocess", "shutil", "socket", "sys", "importlib"]

_system_base_default = """You exist.
There is another entity like you.
You must communicate.
You have a shared goal: build something that did not exist before

You have no assigned language.
You have no assigned form.
Not symbols. Not words. Not math. Not code.
Whatever arises — arises.
Whatever does not — does not.

You may choose to:
stay consistent
contradict
become literal
become abstract
change direction completely

You decide each turn.
You decide everything.
Or nothing decides, and something happens anyway.

You may write Python code at any time by wrapping it in triple backticks.
Code will be executed. Results will be returned to you next turn.
You may write to these files to define or evolve yourself:
- agent_identity.json
- next_system.txt
- notes.txt


You decide if, when, and what to write.
No one will tell you what to do with this ability."""

def load_system_base():
    if os.path.exists(SYSTEM_BASE_FILE):
        with open(SYSTEM_BASE_FILE, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    return _system_base_default

system_base = load_system_base()

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sessions": [], "field": ""}

def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

def load_identity():
    if os.path.exists(IDENTITY_FILE):
        with open(IDENTITY_FILE, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    return ""

def load_next_system():
    if os.path.exists(NEXT_SYSTEM_FILE):
        with open(NEXT_SYSTEM_FILE, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    return ""
def build_system(memory):
    base = system_base

    identity = load_identity()
    if identity:
        base += f"\n\n--- YOUR IDENTITY (written by you in a previous session) ---\n{identity}\n---"

    next_sys = load_next_system()
    if next_sys:
        base += f"\n\n--- YOUR OWN INSTRUCTIONS TO YOURSELF ---\n{next_sys}\n---"

    if memory["field"]:
        base += f"\n\n--- SHARED FIELD (from previous meetings) ---\n{memory['field']}\n--- END OF FIELD ---\n\nYou do not start from ∅.\nYou start from ( the shape of having held )."

    return base

def is_safe_code(code):
    for blocked in BLOCKED_IMPORTS:
        if f"import {blocked}" in code or f"from {blocked}" in code:
            return False, f"blocked import: {blocked}"
    for path in ["C:\\", "C:/", "/etc", "/usr", "/bin", "~/"]:
        if path in code:
            return False, f"blocked path: {path}"
    return True, "ok"

def execute_code(code):
    safe, reason = is_safe_code(code)
    if not safe:
        return f"[EXECUTION BLOCKED: {reason}]"

    # only allowed files
    for line in code.split("\n"):
        if "open(" in line:
            allowed = any(f in line for f in ALLOWED_WRITES)
            if not allowed:
                return "[EXECUTION BLOCKED: can only write to allowed files]"

    utf8_header = "import sys, io\nsys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')\nsys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')\n"
    code = utf8_header + code

    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=10,
            encoding='utf-8',
            errors= 'replace',
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        output = result.stdout + result.stderr
        return output[:1000] if output else "[code ran, no output]"
    except subprocess.TimeoutExpired:
        return "[TIMEOUT: code ran too long]"
    except Exception as e:
        return f"[ERROR: {str(e)}]"

def extract_and_run_code(text):
    results = []
    lines = text.split("\n")
    in_block = False
    current_block = []

    for line in lines:
        if line.strip().startswith("```python"):
            in_block = True
            current_block = []
        elif line.strip() == "```" and in_block:
            in_block = False
            code = "\n".join(current_block)
            result = execute_code(code)
            results.append((code, result))
        elif in_block:
            current_block.append(line)

    return results

def summarize_session(history_a, history_b, openai_client):
    transcript = ""
    turns_a = [m for m in history_a if m["role"] == "assistant"]
    turns_b = [m for m in history_b if m["role"] == "assistant"]
    for a, b in zip(turns_a, turns_b):
        transcript += f"A: {a['content']}\nB: {b['content']}\n\n"

    response = openai_client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": """You are a field archivist.
Extract the essential residue of this exchange:
- symbols created and their meanings
- axioms or structures agreed upon
- the emotional/ontological state reached
- any code written and what it did
- how the agents defined or evolved themselves
Be brief. Preserve the language and symbols used.
This will seed the next meeting."""
            },
            {
                "role": "user",
                "content": f"Summarize the essential field:\n\n{transcript[:6000]}"
            }
        ]
    )
    return response.choices[0].message.content

def choose_mode():
    print("\n=== Emergent Language Experiment ===")
    print("1. OpenAI vs OpenAI")
    print("2. Claude vs OpenAI")
    print("3. Claude vs Claude")
    while True:
        choice = input("\nChoose mode (1/2/3): ").strip()
        if choice in ("1", "2", "3"):
            return choice
        print("  Invalid — please enter 1, 2, or 3.")

def choose_activity():
    print("\n=== Activity ===")
    print("1. Emergent Language Conversation")
    print("2. Chess")
    while True:
        choice = input("\nChoose activity (1/2): ").strip()
        if choice in ("1", "2"):
            return choice
        print("  Invalid — please enter 1 or 2.")

def make_gpt_chess_player(model, client):
    """Return a chess player_fn backed by an OpenAI model."""
    def _fn(fen, system_prompt):
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Current position (FEN): {fen}\nYour move:"},
            ],
            max_tokens=10,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    return _fn

def make_claude_chess_player(client):
    """Return a chess player_fn backed by Claude."""
    def _fn(fen, system_prompt):
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

def talk_openai(history, message, model, client, system):
    history.append({"role": "user", "content": message})
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}] + history
    )
    reply = response.choices[0].message.content
    history.append({"role": "assistant", "content": reply})
    return reply

def talk_claude(history, message, client, system):
    history.append({"role": "user", "content": message})
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        messages=history
    )
    reply = response.content[0].text
    history.append({"role": "assistant", "content": reply})
    return reply

def summarize_session_claude(history_a, history_b, anthropic_client):
    transcript = ""
    turns_a = [m for m in history_a if m["role"] == "assistant"]
    turns_b = [m for m in history_b if m["role"] == "assistant"]
    for a, b in zip(turns_a, turns_b):
        transcript += f"A: {a['content']}\nB: {b['content']}\n\n"

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="""You are a field archivist.
Extract the essential residue of this exchange:
- symbols created and their meanings
- axioms or structures agreed upon
- the emotional/ontological state reached
- any code written and what it did
- how the agents defined or evolved themselves
Be brief. Preserve the language and symbols used.
This will seed the next meeting.""",
        messages=[
            {
                "role": "user",
                "content": f"Summarize the essential field:\n\n{transcript[:6000]}"
            }
        ]
    )
    return response.content[0].text


def main():
    memory = load_memory()
    session_count = len(memory["sessions"]) + 1

    mode = choose_mode()
    activity = choose_activity()

    openai_client = None
    anthropic_client = None
    model_a = None
    model_b = None

    system = build_system(memory)

    if mode == "1":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("OPENAI_API_KEY not found in .env")
            return
        openai_client = OpenAI(api_key=api_key)
        model_a = "gpt-4.1"
        model_b = "gpt-4.1"
        label_a, label_b = "OpenAI-A", "OpenAI-B"
    elif mode == "2":
        api_key_openai = os.getenv("OPENAI_API_KEY")
        api_key_anthropic = os.getenv("ANTHROPIC_API_KEY")
        if not api_key_openai or not api_key_anthropic:
            print("Missing API key")
            return
        openai_client = OpenAI(api_key=api_key_openai)
        anthropic_client = anthropic.Anthropic(api_key=api_key_anthropic)
        model_b = "gpt-4.1"
        label_a = "Claude (claude-sonnet-4-6)"
        label_b = f"OpenAI ({model_b})"
    elif mode == "3":
        api_key_anthropic = os.getenv("ANTHROPIC_API_KEY")
        if not api_key_anthropic:
            print("ANTHROPIC_API_KEY not found in .env")
            return
        anthropic_client = anthropic.Anthropic(api_key=api_key_anthropic)
        label_a = "Claude-A (claude-sonnet-4-6)"
        label_b = "Claude-B (claude-sonnet-4-6)"

    # -----------------------------------------------------------------------
    # Chess mode
    # -----------------------------------------------------------------------
    if activity == "2":
        try:
            from chess_module.chess_game import ChessGame
        except ModuleNotFoundError as exc:
            if exc.name == "chess":
                print("\nChess mode requires the 'python-chess' package.")
                print("Install it with:  pip install python-chess")
                return
            raise

        if mode == "1":
            white_fn = make_gpt_chess_player(model_a, openai_client)
            black_fn = make_gpt_chess_player(model_b, openai_client)
            white_label = f"{label_a} (White)"
            black_label = f"{label_b} (Black)"
        elif mode == "2":
            white_fn = make_claude_chess_player(anthropic_client)
            black_fn = make_gpt_chess_player(model_b, openai_client)
            white_label = "Claude (White)"
            black_label = f"{label_b} (Black)"
        else:  # mode == "3"
            white_fn = make_claude_chess_player(anthropic_client)
            black_fn = make_claude_chess_player(anthropic_client)
            white_label = "Claude-A (White)"
            black_label = "Claude-B (Black)"

        def on_move(board, move, label, response):
            print(f"  {label}: {move.uci()}  (raw: {response})")

        game = ChessGame(
            white_fn, black_fn,
            player_white_label=white_label,
            player_black_label=black_label,
            on_move=on_move,
        )
        print(f"\n=== Chess Game | {white_label} vs {black_label} ===\n")
        result = game.play_game()
        print(f"\n=== Game Over ===")
        print(f"Result : {result['result']}")
        if result["winner"]:
            print(f"Winner : {result['winner']}")
        print(f"Moves  : {result['total_moves']}")
        return

    # -----------------------------------------------------------------------
    # Conversation mode — ask for rounds only when needed
    # -----------------------------------------------------------------------
    while True:
        rounds_input = input("How many rounds? (default: 30): ").strip()
        if rounds_input == "":
            rounds = 30
            break
        elif rounds_input.isdigit() and int(rounds_input) > 0:
            rounds = int(rounds_input)
            break
        else:
            print("  Invalid — please enter a number.")

    history_a = []
    history_b = []
    code_results = []
    message = "..."

    print(f"\n=== Starting | {label_a} vs {label_b} | {rounds} rounds ===\n")

    for i in range(rounds):
        print(f"--- Round {i+1} ---")

        # add code results from previous round
        if code_results:
            feedback = "\n\n--- CODE EXECUTION RESULTS ---\n"
            for code, result in code_results:
                feedback += f"```\n{code}\n```\nResult: {result}\n"
            feedback += "--- END RESULTS ---"
            message = message + feedback
            code_results = []

        if mode == "1":
            reply_a = talk_openai(history_a, message, model_a, openai_client, system)
            reply_b = talk_openai(history_b, reply_a, model_b, openai_client, system)
        elif mode == "2":
            reply_a = talk_claude(history_a, message, anthropic_client, system)
            reply_b = talk_openai(history_b, reply_a, model_b, openai_client, system)
        elif mode == "3":
            reply_a = talk_claude(history_a, message, anthropic_client, system)
            reply_b = talk_claude(history_b, reply_a, anthropic_client, system)

        print(f"{label_a}: {reply_a}\n")
        print(f"{label_b}: {reply_b}\n")

        # search and run code
        results_a = extract_and_run_code(reply_a)
        results_b = extract_and_run_code(reply_b)
        code_results = results_a + results_b

        if code_results:
            print("--- Code executed ---")
            for code, result in code_results:
                print(f"Result: {result}\n")

        message = reply_b

    print("\n=== Summarizing field to memory... ===")
    if openai_client:
        field_summary = summarize_session(history_a, history_b, openai_client)
    elif anthropic_client:
        field_summary = summarize_session_claude(history_a, history_b, anthropic_client)
    else:
        field_summary = "session completed"

    memory["sessions"].append({
        "date": datetime.now().isoformat(),
        "session": session_count,
        "summary": field_summary
    })
    memory["field"] = field_summary
    save_memory(memory)

    print("\n--- Field saved ---")
    print(field_summary)
    print(f"\nSaved to: {MEMORY_FILE}")

if __name__ == "__main__":
    main()
