"""Browser interaction layer using Playwright."""

from __future__ import annotations

from dataclasses import dataclass, field
from playwright.async_api import async_playwright, Browser, Page


@dataclass
class Element:
    """A simplified representation of an interactive page element."""
    index: int
    tag: str
    text: str
    href: str | None = None
    type: str | None = None
    name: str | None = None
    placeholder: str | None = None


@dataclass
class PageState:
    """Snapshot of the current page state sent to the LLM."""
    url: str
    title: str
    text_content: str
    elements: list[Element] = field(default_factory=list)

    def to_prompt(self) -> str:
        lines = [
            f"## Current Page",
            f"URL: {self.url}",
            f"Title: {self.title}",
            f"",
            f"## Page Content (trimmed)",
            self.text_content[:3000],
            f"",
            f"## Interactive Elements",
        ]
        for el in self.elements:
            parts = [f"[{el.index}] <{el.tag}>"]
            if el.type:
                parts.append(f'type="{el.type}"')
            if el.name:
                parts.append(f'name="{el.name}"')
            if el.placeholder:
                parts.append(f'placeholder="{el.placeholder}"')
            if el.href:
                parts.append(f'href="{el.href}"')
            if el.text:
                parts.append(f'"{el.text}"')
            lines.append(" ".join(parts))
        return "\n".join(lines)


class BrowserController:
    """Wraps Playwright to provide high-level browser actions."""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self._pw = None
        self._browser: Browser | None = None
        self.page: Page | None = None

    async def start(self, url: str = "https://quotes.toscrape.com"):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=self.headless)
        self.page = await self._browser.new_page()
        await self.page.goto(url, wait_until="domcontentloaded")

    async def stop(self):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    async def get_state(self) -> PageState:
        """Extract current page state for the LLM."""
        page = self.page

        url = page.url
        title = await page.title()
        text = await page.inner_text("body")

        # Collect interactive elements: links, buttons, inputs
        elements: list[Element] = []
        selector = "a, button, input, textarea, select, [role='button']"
        handles = await page.query_selector_all(selector)

        for i, handle in enumerate(handles):
            tag = await handle.evaluate("el => el.tagName.toLowerCase()")
            text_content = (await handle.inner_text()).strip() if tag != "input" else ""
            href = await handle.get_attribute("href")
            input_type = await handle.get_attribute("type")
            name = await handle.get_attribute("name")
            placeholder = await handle.get_attribute("placeholder")

            elements.append(Element(
                index=i,
                tag=tag,
                text=text_content[:80],
                href=href,
                type=input_type,
                name=name,
                placeholder=placeholder,
            ))

        return PageState(url=url, title=title, text_content=text[:3000], elements=elements)

    async def execute_action(self, action: dict) -> str:
        """Execute an action returned by the LLM. Returns a status message."""
        action_type = action.get("action")
        page = self.page

        try:
            if action_type == "click":
                idx = action["element_index"]
                selector = "a, button, input, textarea, select, [role='button']"
                handles = await page.query_selector_all(selector)
                if 0 <= idx < len(handles):
                    await handles[idx].click()
                    await page.wait_for_load_state("domcontentloaded")
                    return f"Clicked element [{idx}]."
                return f"Element [{idx}] not found (only {len(handles)} elements on page)."

            elif action_type == "type":
                idx = action["element_index"]
                text = action["text"]
                selector = "a, button, input, textarea, select, [role='button']"
                handles = await page.query_selector_all(selector)
                if 0 <= idx < len(handles):
                    await handles[idx].fill(text)
                    return f"Typed '{text}' into element [{idx}]."
                return f"Element [{idx}] not found."

            elif action_type == "navigate":
                url = action["url"]
                await page.goto(url, wait_until="domcontentloaded")
                return f"Navigated to {url}."

            elif action_type == "back":
                await page.go_back(wait_until="domcontentloaded")
                return "Went back."

            elif action_type == "scroll":
                direction = action.get("direction", "down")
                pixels = 500
                if direction == "up":
                    pixels = -500
                await page.evaluate(f"window.scrollBy(0, {pixels})")
                return f"Scrolled {direction}."

            elif action_type == "extract":
                return f"Data noted: {action.get('data', '')}"

            elif action_type == "done":
                return "DONE"

            else:
                return f"Unknown action: {action_type}"

        except Exception as e:
            return f"Action failed: {e}"
