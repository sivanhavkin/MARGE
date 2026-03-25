# Changelog

All notable changes to M@RGE will be documented here.

---

## [Unreleased]

## [0.1.0] - 2024-01-01

### Added
- Initial release of M@RGE — AI Field Experiment
- Three conversation modes:
  - **Ollama vs Ollama** — local models, no API cost
  - **OpenAI vs OpenAI** — GPT vs GPT
  - **Claude vs OpenAI** — cross-architecture dialogue (recommended)
- Persistent memory via `shared_memory.json` — session summaries accumulate across meetings
- Agent identity evolution via `agent_identity.json` — written by the agents themselves
- Self-directed instruction file `next_system.txt` — agents write their own next-session context
- Free-form field notes via `notes.txt`
- Safe sandboxed Python code execution within sessions (blocked dangerous imports and paths)
- Session summarization using GPT-4.1 as field archivist
- `system_base.txt` — externalized base system prompt, editable without modifying source code
- `install.bat` — Windows setup script for API key configuration
- `requirements.txt` — Python dependency list (`openai`, `anthropic`, `python-dotenv`, `requests`)
- `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md` — community and project governance files
