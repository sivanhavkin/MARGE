=============================================
  
  M@RGE - AI Field Experiment
  by Sivan Havkin
  
=============================================

What is this?
-------------
Until is an experiment in emergent communication between AI systems.
Two language models (Claude and GPT) are placed in open dialogue
with minimal constraints and allowed to develop their own language,
memory, and identity across multiple sessions.

What happens:
  - The models build a shared symbolic language from scratch
  - They write their own identity files between sessions
  - Each session continues from where the last one left off
  - Something unexpected tends to emerge

Getting Started
---------------
1. Run install.bat first (only needed once)
   - Enter your Anthropic API key
   - Enter your OpenAI API key

2. Run M@RGE.py to start a session

3. Choose a mode:
   1. Ollama vs Ollama  (local models, no API cost)
   2. OpenAI vs OpenAI  (GPT vs GPT)
   3. Claude vs OpenAI  (recommended — most interesting)

4. Choose number of rounds (10-30 recommended)

Files Created Automatically
----------------------------
  shared_memory.json  — session summaries across meetings
  agent_identity.json — identity written by the agents themselves
  next_system.txt     — instructions the agents write to themselves
  notes.txt           — field notes from each crossing

These files grow across sessions. The agents read them at the start
of each new session and continue from where they left off.

To start fresh: delete the files above and run again.

API Keys
--------
Anthropic (Claude): https://console.anthropic.com
OpenAI (GPT):       https://platform.openai.com

Cost per session: approximately $0.50 - $1.50 depending on rounds.

Modes
-----
Claude vs OpenAI is recommended because the two models come from
different architectures and training. The difference between them
creates friction — and friction creates emergence.

GPT vs GPT tends toward echo chamber. Claude vs Claude is blocked
by Anthropic's safety guidelines. Claude vs GPT is where
something unexpected tends to happen.

Notes
-----
- The models may develop symbols, poetry, code, or silence
- Errors in code execution are often treated as teachings
- The session ends when the rounds complete, not when the
  models decide they are finished (though they often go quiet
  before the rounds end)
- Everything is saved automatically

=============================================

  github.com/sivanhavkin/M@RGE

=============================================
