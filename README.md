# Browser Agent

An LLM-powered browser agent that autonomously navigates websites. Instead of pre-defined scraping scripts, the agent observes the current page state and lets an LLM decide what to do next — dynamically generating actions at each step.

Built with **Playwright** for browser automation and **Gemini 2.0 Flash** (via OpenRouter) for decision-making.

## How It Works

The agent runs in a loop:

1. **Observe** — Extract the current page URL, visible text, and all interactive elements (links, buttons, inputs)
2. **Think** — Send the page state to the LLM, which returns a JSON action
3. **Act** — Execute the action (click, type, navigate, scroll, extract data, etc.)
4. **Repeat** — Until the LLM decides the goal is achieved or the step limit is reached

```
User Goal
    │
    ▼
┌──────────────────────────────┐
│  Observe → Think → Act       │
│     ▲                 │      │
│     └─────────────────┘      │
│         until "done"         │
└──────────────────────────────┘
```

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

Set your OpenRouter API key:

```bash
export OPENROUTER_API_KEY="your-key-here"
```

Get a key at https://openrouter.ai/keys.

## Usage

```bash
# Default goal: find Albert Einstein quotes and biography
python agent.py

# Custom goal
python agent.py "Find all quotes tagged 'love' and extract them"

# With options
python agent.py "Log in with username 'admin' and password 'admin'" \
    --max-steps 15 \
    --headless \
    --model google/gemini-2.0-flash-001
```

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `goal` | Find Einstein quotes | The task for the agent to accomplish |
| `--url` | `https://quotes.toscrape.com` | Starting URL |
| `--max-steps` | `20` | Maximum number of observe/think/act iterations |
| `--headless` | `false` | Run browser without visible window |
| `--model` | `google/gemini-2.0-flash-001` | OpenRouter model ID |

## Available Actions

The LLM can choose from these actions at each step:

| Action | Description |
|--------|-------------|
| `click` | Click an interactive element by index |
| `type` | Type text into an input field |
| `navigate` | Go to a specific URL |
| `back` | Go back to the previous page |
| `scroll` | Scroll up or down |
| `extract` | Record/note data found on the page |
| `done` | Declare the task complete |

## Project Structure

```
browser-agent/
├── agent.py          # Main loop and CLI
├── browser.py        # Playwright wrapper (page state extraction + action execution)
├── llm.py            # OpenRouter LLM client (system prompt + JSON parsing)
└── requirements.txt  # Dependencies
```
