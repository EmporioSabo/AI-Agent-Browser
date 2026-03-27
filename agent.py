"""Main agentic browsing loop."""

from __future__ import annotations

import argparse
import asyncio

from browser import BrowserController
from llm import LLMAgent


async def run_agent(goal: str, start_url: str, max_steps: int, headless: bool, model: str):
    browser = BrowserController(headless=headless)
    llm = LLMAgent(model=model)

    print(f"\n{'='*60}")
    print(f"  Browser Agent")
    print(f"  Goal: {goal}")
    print(f"  Start: {start_url}")
    print(f"  Model: {model}")
    print(f"{'='*60}\n")

    await browser.start(start_url)
    last_result = None
    collected_data: list[str] = []

    try:
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
                print(f"\n{'='*60}")
                print(f"  Agent finished!")
                print(f"  Summary: {action.get('result', 'No summary')}")
                if collected_data:
                    print(f"\n  Collected Data:")
                    for i, d in enumerate(collected_data, 1):
                        print(f"    {i}. {d}")
                print(f"{'='*60}\n")
                break
        else:
            print(f"\nMax steps ({max_steps}) reached.")

    finally:
        await browser.stop()


def main():
    parser = argparse.ArgumentParser(description="Agentic web browser powered by LLM")
    parser.add_argument(
        "goal",
        nargs="?",
        default="Browse the quotes website. Find all quotes by Albert Einstein and extract them. Also find his biography details.",
        help="The goal for the agent to accomplish",
    )
    parser.add_argument("--url", default="https://quotes.toscrape.com", help="Starting URL")
    parser.add_argument("--max-steps", type=int, default=20, help="Maximum number of agent steps")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument(
        "--model",
        default="google/gemini-2.0-flash-001",
        help="OpenRouter model ID (default: google/gemini-2.0-flash-001)",
    )
    args = parser.parse_args()
    asyncio.run(run_agent(args.goal, args.url, args.max_steps, args.headless, args.model))


if __name__ == "__main__":
    main()
