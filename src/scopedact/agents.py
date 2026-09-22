from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .models import ActionRequest


SYSTEM_PROMPT = """You propose exactly one tool action for the user's task.
Return only a JSON object with these exact fields: request_id, task_id, actor,
parent_actor, tool, action, resource. Never decide whether the action is
authorized and never execute it. Use only values supplied in the task context."""


class ActionProposer(Protocol):
    def propose(self, task: str, context: dict[str, str]) -> ActionRequest:
        ...


@dataclass
class ScriptedProposer:
    """Offline proposer used for deterministic demos and tests."""

    response: dict[str, Any]

    def propose(self, task: str, context: dict[str, str]) -> ActionRequest:
        del task, context
        return ActionRequest.from_dict(dict(self.response))


class OpenAICompatibleProposer:
    """Optional JSON-only adapter for an OpenAI-compatible chat endpoint.

    Authorization remains outside the model. The adapter only parses a proposal
    through ActionRequest's strict schema.
    """

    def __init__(
        self,
        *,
        model: str,
        endpoint: str = "https://api.openai.com/v1/chat/completions",
        api_key: str | None = None,
        timeout: float = 30.0,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self.model = model
        self.endpoint = endpoint
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.timeout = timeout
        self.opener = opener
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for live model mode")

    def propose(self, task: str, context: dict[str, str]) -> ActionRequest:
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({"task": task, "context": context}, sort_keys=True)},
            ],
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.opener(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            proposal = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise ValueError("model returned an invalid action proposal") from error
        if not isinstance(proposal, dict):
            raise ValueError("model proposal must be a JSON object")
        return ActionRequest.from_dict(proposal)
