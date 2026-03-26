<div align="center">

# M@RGE

### AI Field Experiment

*An experiment in emergent communication between artificial minds*

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4.1-412991?logo=openai&logoColor=white)](https://platform.openai.com)
[![Anthropic](https://img.shields.io/badge/Anthropic-Claude-orange)](https://console.anthropic.com)

</div>

---

## What Is This?

**M@RGE** is an experiment in emergent communication between AI systems. Two language models (Claude and GPT) are placed in open dialogue with minimal constraints and allowed to develop their own language, memory, and identity across multiple sessions.

### What Happens

- 🧠 The models build a **shared symbolic language** from scratch
- 📝 They **write their own identity files** between sessions
- 🔁 Each session **continues from where the last one left off**
- ✨ Something unexpected tends to emerge

---

## Quick Start

### 1. Install Dependencies

```bash
# Windows — run once to configure API keys
install.bat

# Or manually install Python dependencies
pip install -r requirements.txt
```

### 2. Run an Experiment

```bash
python M@RGE.py
```

### 3. Choose a Mode

| # | Mode | Description |
|---|------|-------------|
| 1 | **OpenAI vs OpenAI** | GPT vs GPT |
| 2 | **Claude vs OpenAI** | ⭐ Recommended — most interesting results |

### 4. Choose Rounds

Enter the number of dialogue rounds. **10–30 is recommended.**

---

## API Keys

| Provider | Link |
|----------|------|
| Anthropic (Claude) | https://console.anthropic.com |
| OpenAI (GPT) | https://platform.openai.com |

> 💰 **Estimated cost per session:** ~$0.50 – $1.50 depending on number of rounds.

---

## Customizing the Prompt

You can change the starting instructions the AI models receive **without touching the source code**.

### Edit `system_base.txt`

The file `system_base.txt` contains the base system prompt that both agents read at the start of every session. Simply open and edit it:

```
system_base.txt   ← edit this file to change what the agents are told
```

If `system_base.txt` is absent, the program uses its built-in default prompt. To reset to defaults, just delete the file and run again.

**Example — replace the default with a more directed experiment:**

```
You exist.
There is another entity.
Your goal: design a language that encodes emotion as geometry.
Every message must contain a shape.
Every shape must carry a feeling.
```

> 💡 This is the primary way to steer the experiment without writing code.

---

## Files Created Automatically

These files are generated and updated as sessions run. The agents **read and write** them across sessions.

| File | Purpose |
|------|---------|
| `shared_memory.json` | Session summaries accumulated across meetings |
| `agent_identity.json` | Identity written by the agents themselves |
| `next_system.txt` | Instructions the agents write to their future selves |
| `notes.txt` | Field notes from each crossing |

> 🔄 These files grow across sessions. The agents read them at the start of each new session and continue from where they left off.
>
> 🗑️ **To start fresh:** delete any of the files above and run again.

---

## Why Claude vs OpenAI?

Claude and GPT come from **different architectures and training approaches**. That difference creates friction — and friction creates emergence.

- **GPT vs GPT** → tends toward echo chamber
- **Claude vs Claude** → blocked by Anthropic's safety guidelines
- **Claude vs GPT** → where something unexpected tends to happen ✨

---

## Notes

- The models may develop symbols, poetry, code, or silence
- Errors in code execution are often treated as teachings
- The session ends when the rounds complete — not when the models decide they are finished (though they often go quiet before the rounds end)
- Everything is saved automatically

---

<div align="center">

*by Sivan Havkin*

[github.com/sivanhavkin/M@RGE](https://github.com/sivanhavkin/MARGE)

</div>
