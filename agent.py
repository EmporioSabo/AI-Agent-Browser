"""Main agentic browsing loop with interactive chat interface."""

from __future__ import annotations

import argparse
import asyncio

from browser import BrowserController
from llm import LLMAgent


async def execute_goal(browser: BrowserController, llm: LLMAgent, goal: str, max_steps: int):
    """Run the observe→think→act loop for a single goal."""
    last_result = None
    collected_data: list[str] = []

    for step in range(1, max_steps + 1):
        # 1. Observe
        state = await browser.get_state()
        state_prompt = state.to_prompt()

        # 2. Think
        print(f"--- Step {step}/{max_steps} ---")
        print(f"  URL: {state.url}")
        action = llm.decide(goal, state_prompt, last_result)
        print(f"  Action: {action.get('action')}  |  Reason: {action.get('reason', '')}")

        # 3. Act
        last_result = await browser.execute_action(action)
        print(f"  Result: {last_result}")

        # Track extracted data
        if action.get("action") == "extract":
            collected_data.append(action.get("data", ""))

        # 4. Check termination
        if last_result == "DONE" or action.get("action") == "done":
            print(f"\n  Task complete: {action.get('result', 'No summary')}")
            if collected_data:
                print(f"\n  Collected Data:")
                for i, d in enumerate(collected_data, 1):
                    print(f"    {i}. {d}")
            print()
            return

    print(f"\n  Max steps ({max_steps}) reached.\n")


async def run_interactive(start_url: str, max_steps: int, headless: bool, model: str, initial_goal: str | None = None):
    browser = BrowserController(headless=headless)
    llm = LLMAgent(model=model)

    print(f"\n{'='*60}")
    print(f"  Browser Agent (interactive mode)")
    print(f"  Model: {model}")
    print(f"  Type 'quit' or 'exit' to stop")
    print(f"{'='*60}\n")

    await browser.start(start_url)

    try:
        # Run initial goal if provided via CLI
        if initial_goal:
            print(f"  Goal: {initial_goal}\n")
            await execute_goal(browser, llm, initial_goal, max_steps)

        # Interactive loop — wait for next prompt
        while True:
            try:
                goal = await asyncio.to_thread(input, "You > ")
            except (EOFError, KeyboardInterrupt):
                print()
                break

            goal = goal.strip()
            if not goal:
                continue
            if goal.lower() in ("quit", "exit"):
                break

            # Reset conversation history for each new goal
            llm.messages.clear()
            await execute_goal(browser, llm, goal, max_steps)

    finally:
        await browser.stop()
        print("Browser closed. Goodbye!")


def main():
    parser = argparse.ArgumentParser(description="Agentic web browser powered by LLM")
    parser.add_argument(
        "goal",
        nargs="?",
        default=None,
        help="Optional initial goal (agent will prompt for more after completing it)",
    )
    parser.add_argument("--url", default="https://quotes.toscrape.com", help="Starting URL")
    parser.add_argument("--max-steps", type=int, default=20, help="Maximum steps per goal")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument(
        "--model",
        default="google/gemini-2.0-flash-001",
        help="OpenRouter model ID (default: google/gemini-2.0-flash-001)",
    )
    args = parser.parse_args()
    asyncio.run(run_interactive(args.url, args.max_steps, args.headless, args.model, args.goal))


if __name__ == "__main__":
    main()
