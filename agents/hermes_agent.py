"""
agents/hermes_agent.py
Hermes-compatible tool-calling agent powered by OpenRouter.

Implements the Hermes-2 function-calling convention:
  - Tools are declared as JSON schemas
  - The LLM decides which tool to call and with what arguments
  - Results are fed back to continue the loop
"""

from __future__ import annotations

import json
from typing import Any, Callable

import httpx

from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, LLM_MODEL


# ── Tool registry ─────────────────────────────────────────────────────────────

class Tool:
    def __init__(self, name: str, description: str, parameters: dict, fn: Callable):
        self.name        = name
        self.description = description
        self.parameters  = parameters
        self.fn          = fn

    def to_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name":        self.name,
                "description": self.description,
                "parameters":  self.parameters,
            },
        }

    def call(self, **kwargs) -> Any:
        return self.fn(**kwargs)


# ── Hermes Agent ─────────────────────────────────────────────────────────────

class HermesAgent:
    """
    A ReAct-style agent that:
      1. Receives a user goal.
      2. Selects and calls tools iteratively.
      3. Returns a final answer once sufficient information is gathered.
    """

    SYSTEM_PROMPT = """\
You are a weather prediction trading agent working on Polymarket.
Your goal is to find profitable opportunities on weather-related markets
by fetching real weather data, building predictions, and placing paper trades.
You have access to a set of tools. Use them step by step to:
1. Fetch current weather data for tracked cities.
2. Fetch open weather markets on Polymarket.
3. Run your prediction model to find edges.
4. Calculate Kelly-optimal position sizes.
5. Place paper trades on markets with positive edge (>3%).
6. Check for positions that should be hedged.
Always reason aloud before calling a tool. After completing all steps,
summarise the trades placed, expected value, and risk."""

    def __init__(self, tools: list[Tool], max_iterations: int = 10):
        self.tools          = {t.name: t for t in tools}
        self.max_iterations = max_iterations
        self._headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "https://github.com/crowdwisdomtrading/weather-agent",
            "X-Title":       "WeatherPredictionAgent",
        }

    def _chat(self, messages: list[dict]) -> dict:
        """Single OpenRouter API call."""
        payload = {
            "model":      LLM_MODEL,
            "messages":   messages,
            "tools":      [t.to_schema() for t in self.tools.values()],
            "tool_choice": "auto",
            "max_tokens": 1024,
        }
        r = httpx.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            json=payload,
            headers=self._headers,
            timeout=60,
        )
        r.raise_for_status()
        return r.json()

    def _extract_tool_calls(self, response: dict) -> list[dict]:
        choice  = response["choices"][0]
        message = choice["message"]
        return message.get("tool_calls") or []

    def _extract_text(self, response: dict) -> str:
        choice  = response["choices"][0]
        message = choice["message"]
        return message.get("content") or ""

    def run(self, goal: str) -> str:
        """
        Execute the agent loop for a given goal.

        Returns the final text response.
        """
        messages: list[dict] = [
            {"role": "system",  "content": self.SYSTEM_PROMPT},
            {"role": "user",    "content": goal},
        ]

        for iteration in range(self.max_iterations):
            print(f"\n[hermes] Iteration {iteration + 1}/{self.max_iterations}")

            response    = self._chat(messages)
            tool_calls  = self._extract_tool_calls(response)
            final_text  = self._extract_text(response)

            # Add assistant turn to history
            messages.append(response["choices"][0]["message"])

            if not tool_calls:
                # No more tool calls → we have the final answer
                print("[hermes] Agent completed.")
                return final_text

            # Execute each tool call
            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"].get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}

                tool = self.tools.get(fn_name)
                if tool:
                    print(f"[hermes] → calling tool: {fn_name}({args})")
                    try:
                        result = tool.call(**args)
                    except Exception as exc:
                        result = {"error": str(exc)}
                else:
                    result = {"error": f"Unknown tool: {fn_name}"}

                # Feed result back as a tool message
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc["id"],
                    "content":      json.dumps(result, default=str),
                })

        return "Agent reached maximum iterations without a final answer."
