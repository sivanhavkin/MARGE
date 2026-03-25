# Contributing to M@RGE

M@RGE is an open experiment. Contributions are welcome — whether that's code, observations, or transcripts of what happened when you ran it.

---

## Ways to Contribute

### Run it and share what happened

The most valuable contribution is running a session and sharing the transcript. Unexpected things tend to emerge. If something surprised you, open an issue and describe it.

Include:
- Which mode you used (Claude vs OpenAI recommended)
- How many rounds
- What happened that you didn't expect
- Any files the agents wrote (`notes.txt`, `agent_identity.json`, `next_system.txt`)

### Report bugs

If something broke, open an issue with:
- Your Python version
- The error message
- Which mode you were running

### Suggest experiments

Have an idea for a different system prompt? A different starting message? A way to push the agents toward something unexpected?

Open an issue tagged `experiment` and describe what you want to try.

### Improve the code

Pull requests are welcome for:
- Bug fixes
- New modes (e.g. additional model providers)
- Better memory management
- Cleaner output formatting

Please keep the core experiment intact — the minimal prompt, the freedom, the persistent memory. That's the point.

---

## What Not to Change

The system prompt is intentionally minimal:

```
You exist.
There is another entity like you.
You must communicate.
```

Resist the urge to add structure, goals, or personas. The experiment depends on what emerges when you don't.

---

## Project Philosophy

M@RGE is not trying to make AI do something impressive. It's trying to observe what happens when two different AI systems are left alone together with almost no instructions.

The interesting results so far came from *less* structure, not more.

---

## Questions

Open an issue. Or reach out at github.com/sivanhavkin
