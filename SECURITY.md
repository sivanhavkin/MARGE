# Security Policy

## API Keys

M@RGE requires two API keys to run:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`

These are stored locally in a `.env` file and are **never uploaded or transmitted** anywhere except directly to the Anthropic and OpenAI APIs.

**Do not commit your `.env` file.** It is included in `.gitignore` by default.

If you accidentally expose your API keys:
- Anthropic: https://console.anthropic.com — revoke and regenerate
- OpenAI: https://platform.openai.com/api-keys — revoke and regenerate

---

## Code Execution Sandbox

M@RGE allows the AI agents to write and execute Python code during sessions. This is sandboxed with the following restrictions:

**Blocked imports:**
```
os, subprocess, shutil, socket, sys, importlib
```

**Blocked file paths:**
```
C:\, C:/, /etc, /usr, /bin, ~/
```

**Allowed file writes** (agents can only write to):
```
agent_identity.json
next_system.txt
notes.txt
```

**Timeout:** Code execution is limited to 10 seconds.

These restrictions prevent the agents from accessing the filesystem, network, or system resources beyond their designated memory files.

---

## Reporting a Vulnerability

If you discover a security issue — particularly around the code execution sandbox — please open a private issue or contact via GitHub.

Do not run M@RGE with elevated system privileges. It is intended to run as a standard user process.

---

## Scope

M@RGE is a research experiment, not a production system. It is not intended to handle sensitive data beyond API keys, and should not be deployed in environments where security is critical.
