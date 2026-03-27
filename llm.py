"""LLM interaction layer using OpenRouter (OpenAI-compatible API)."""

from __future__ import annotations

import json
import os

from openai import OpenAI

SYSTEM_PROMPT = """\
You are a web browsing agent. You observe the current state of a web page and decide \
what action to take next to accomplish the user's goal.

You MUST respond with a single JSON object (no markdown fences, no extra text). \
Choose one of these actions:

1. Click an element:
   {"action": "click", "element_index": <int>, "reason": "<why>"}

2. Type into an input field:
   {"action": "type", "element_index": <int>, "text": "<value>", "reason": "<why>"}

3. Navigate to a URL:
   {"action": "navigate", "url": "<full_url>", "reason": "<why>"}

4. Go back:
   {"action": "back", "reason": "<why>"}

5. Scroll the page:
   {"action": "scroll", "direction": "down"|"up", "reason": "<why>"}

6. Extract/note data you found:
   {"action": "extract", "data": "<the data you found>", "reason": "<why>"}

7. Task complete:
   {"action": "done", "result": "<summary of what you accomplished>"}

Guidelines:
- Use element indices from the Interactive Elements list to identify which element to click or type into.
- Always explain your reasoning in the "reason" field.
- If the goal involves collecting data, use "extract" actions to record findings, then "done" when finished.
- Be methodical: explore pages step by step, don't skip ahead.
- If you get stuck or loop, try a different approach.
"""


class LLMAgent:
    """Sends page state to an LLM via OpenRouter and parses the action response."""

    def __init__(self, model: str = "google/gemini-2.0-flash-001"):
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY environment variable is not set. "
                "Get your key at https://openrouter.ai/keys"
            )
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model = model
        self.messages: list[dict] = []

    def decide(self, goal: str, page_state_prompt: str, last_action_result: str | None = None) -> dict:
        """Given current page state, ask the LLM what to do next."""

        user_content = f"## Goal\n{goal}\n\n{page_state_prompt}"
        if last_action_result:
            user_content += f"\n\n## Result of Last Action\n{last_action_result}"

        self.messages.append({"role": "user", "content": user_content})

        # Keep conversation history bounded (last 20 exchanges = 40 messages)
        if len(self.messages) > 40:
            self.messages = self.messages[-40:]

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *self.messages,
            ],
        )

        text = response.choices[0].message.content.strip()
        self.messages.append({"role": "assistant", "content": text})

        # Parse JSON from response (handle markdown fences if present)
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"action": "done", "result": f"Failed to parse LLM response: {text}"}
