# LLM Engineering Playground

A minimal but realistic starter project to experiment with **LLM tool-calling** and **multi-provider integrations** using both **OpenAI** and **Anthropic**.

The repo shows how to:

- Wire up environment-managed API keys via `.env`.
- Use **OpenAI's Responses API** with a custom **tool call** (`get_horoscope`).
- Call **Anthropic Claude** with a simple message flow.
- Structure a small project with `pyenv` + `pipenv` for reproducible environments.

---

## Project Structure

```text
llm-engineering/
├─ anthropic_llm.py      # Minimal Anthropic Claude call example
├─ open_ai_llm.py        # OpenAI Responses API + tool-calling demo (HoroscopeAgent)
├─ Pipfile               # pipenv dependencies and Python version (3.11.9)
├─ Pipfile.lock          # Locked dependency versions
├─ .env.sample           # Template for required environment variables
├─ .env                  # Local secrets (NOT committed; should be gitignored)
└─ .vscode/
   └─ launch.json        # VS Code debugging configuration (current file)
```

---

## Tech Stack

- **Language:** Python 3.11.9 (via `pyenv` + `pipenv`)
- **Environment:** `pipenv` for dependency and virtualenv management
- **LLM Providers:**
  - [OpenAI](https://platform.openai.com/) – Responses API, tool calling
  - [Anthropic Claude](https://console.anthropic.com/)
- **Config:** `.env` loaded via `python-dotenv`

---

## Prerequisites

- **Python:** installed and managed via [`pyenv`](https://github.com/pyenv/pyenv)
- **pipenv:** installed globally in your user environment

```bash
pip install --user pipenv
```

- OpenAI and Anthropic API keys from their respective dashboards.

---

## Environment Setup

### 1. Python version (pyenv)

Install and activate the exact Python version used by this project:

```bash
pyenv install 3.11.9       # if not already installed
pyenv shell 3.11.9         # or use a local env: pyenv local 3.11.9
```

### 2. Create / activate the pipenv environment

From the project root:

```bash
cd llm-engineering
pipenv --python 3.11.9
```

This will:

- Create a virtualenv managed by `pipenv`.
- Create a `Pipfile` pinned to Python 3.11.9.

Install project dependencies (runtime + dev):

```bash
pipenv install          # installs [packages] from Pipfile
pipenv install --dev pytest
```

The current `Pipfile` includes:

```toml
[packages]
python-dotenv = "*"
openai = "*"

[dev-packages]
pytest = "*"

[requires]
python_version = "3.11"
python_full_version = "3.11.9"
```

If you want to run the Anthropic example, also install:

```bash
pipenv install anthropic
```

### 3. Activate the virtual environment

Two equivalent options:

```bash
# Interactive shell
pipenv shell

# One-off command
pipenv run python anthropic_llm.py
```

When using VS Code, select the `pipenv` interpreter (something like):

```text
~/.local/share/virtualenvs/llm-engineering-*/bin/python
```

---

## Environment Variables

Configuration is read from a `.env` file in the project root using `python-dotenv`.

Template (`.env.sample`):

```bash
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

Create your own `.env` by copying the sample and filling in your real keys:

```bash
cp .env.sample .env
# edit .env and set your real keys
```

---

### Running the OpenAI example

From inside the `pipenv` shell:

```bash
pipenv shell         # if not already in the env
python open_ai_llm.py
```

The default main block runs:

```python
if __name__ == "__main__":
    agent = HoroscopeAgent()
    agent.run("What is my horoscope? I am an Aquarius.")
```

You can adapt this pattern to build more sophisticated tool-calling agents: database access, web search, internal APIs, etc.

---

## Anthropic: Minimal Claude Call (`anthropic_llm.py`)

This script shows a very compact way to call Anthropic Claude using the official `anthropic` client.

High-level flow:

1. Load environment variables from `.env`.
2. Instantiate `Anthropic` with `ANTHROPIC_API_KEY`.
3. Call `client.messages.create(...)` with a simple user message.
4. Print the first text block and the response ID.

### Running the Anthropic example

Ensure `anthropic` is installed in your `pipenv` environment:

```bash
pipenv install anthropic
```

Then run:

```bash
pipenv shell
python anthropic_llm.py
```

Expected behavior:

- Claude responds to `"Hello, Claude"`.
- The script prints the text response and the associated `response_id`.

You can modify the message payload to experiment with system prompts, multi-turn conversations, and longer outputs.

---

## Debugging & VS Code Integration

A simple `.vscode/launch.json` is provided to debug the **current file** using the selected interpreter:

```jsonc
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "debugpy",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "justMyCode": true,
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  ]
}
```

To debug with `pipenv`:

1. In VS Code, use **Python: Select Interpreter** and choose the `pipenv` virtualenv.
2. Open `open_ai_llm.py` or `anthropic_llm.py`.
3. Set breakpoints.
4. Run the **Python: Current File** configuration.
