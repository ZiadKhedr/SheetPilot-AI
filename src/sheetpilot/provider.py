"""Official Meta Model API client. Never falls back to simulated AI."""
import json
import logging
import os
import random
import time

from dotenv import dotenv_values
import httpx
from pydantic import ValidationError

from .config import ROOT
from .store import Problem
from .models import Ping


logger = logging.getLogger(__name__)
# Reasoning and visible output share this budget. Grow it only after a length stop.
COMPLETION_TOKEN_LIMITS = (8192, 16384)


class MetaError(Problem):
    def __init__(self, message, status=502, output_error=False):
        super().__init__(message, status)
        self.output_error = output_error


class MetaProvider:
    def __init__(self, key=None, model=None, transport=None):
        values = dotenv_values(ROOT / ".env")
        self.key = key if key is not None else (os.getenv("MODEL_API_KEY") or values.get("MODEL_API_KEY") or "")
        self.model = model or os.getenv("META_MODEL") or values.get("META_MODEL") or "muse-spark-1.3"
        self.base = "https://api.meta.ai/v1"
        self.transport = transport
        self.request_attempts = 3
        self.allow_completion_retry = True

    def status(self):
        return {"configured": bool(self.key.strip()), "model": self.model, "base_url": self.base}

    def request(self, method, path, payload=None):
        if not self.key.strip():
            raise MetaError("Meta is not configured. Add MODEL_API_KEY to the server's .env file.", 503)
        for attempt in range(self.request_attempts):
            try:
                with httpx.Client(timeout=60, transport=self.transport) as client:
                    response = client.request(method, self.base + path,
                        headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}, json=payload)
            except httpx.TimeoutException:
                if attempt < self.request_attempts-1:
                    time.sleep(.3 * (2 ** attempt))
                    continue
                raise MetaError("Meta request timed out. Please retry.")
            except httpx.HTTPError:
                raise MetaError("Could not reach the official Meta API.")
            if response.status_code in {429, 500, 502, 503} and attempt < self.request_attempts-1:
                try:
                    delay = float(response.headers.get("retry-after", ".3"))
                except ValueError:
                    delay = .3
                if delay > 3:
                    raise MetaError("Meta is rate limited; retry later.", 503)
                time.sleep(max(.1, delay) * (2 ** attempt) + random.random() * .1)
                continue
            if response.is_error:
                descriptions = {401: "Meta rejected the API key.", 403: "This Meta account lacks model access.",
                    404: "The configured Meta model or endpoint is unavailable.", 402: "Meta account credits are required.",
                    429: "Meta rate limit reached; retry later.", 400: "Meta rejected the request format."}
                # Provider bodies may contain sensitive data; never return them.
                raise MetaError(descriptions.get(response.status_code, f"Meta API returned HTTP {response.status_code}."))
            if len(response.content) > 2_000_000:
                raise MetaError("Meta response exceeded the accepted size.")
            try:
                return response.json()
            except ValueError:
                raise MetaError("Meta returned invalid JSON.")
        raise MetaError("Meta is temporarily unavailable.")

    def completion(self, messages, schema=None, tools=None):
        payload = {"model": self.model, "messages": messages, "reasoning_effort": "medium"}
        if schema:
            payload["response_format"] = {"type": "json_schema", "json_schema": {
                "name": schema.__name__, "schema": strict_schema(schema.model_json_schema()), "strict": True}}
        if tools:
            payload.update(tools=tools, tool_choice="auto", parallel_tool_calls=False)
        limits=COMPLETION_TOKEN_LIMITS if self.allow_completion_retry else COMPLETION_TOKEN_LIMITS[:1]
        for attempt, limit in enumerate(limits):
            data = self.request("POST", "/chat/completions", payload | {"max_completion_tokens": limit})
            try:
                choice = data["choices"][0]
                if not isinstance(choice, dict):
                    raise TypeError
                reason = choice.get("finish_reason")
                if reason == "length":
                    if attempt == 0 and self.allow_completion_retry:
                        # Never log or replay a partial answer, tool call, or private reasoning.
                        logger.warning("Meta reached its %s-token response limit; retrying once with %s tokens.",
                                       limit, COMPLETION_TOKEN_LIMITS[1])
                        continue
                    raise MetaError("Meta reached its response limit after one retry. Try a smaller selection or analyze one table at a time."
                                    if self.allow_completion_retry else
                                    "Meta reached its response limit. This job did not replay the provider call; use a smaller job or explicitly retry.")
                if reason == "content_filter":
                    raise MetaError("Meta could not return this response because of a content restriction.")
                if reason not in {"stop", "tool_calls"}:
                    raise MetaError("Meta stopped before completing this response. Please retry this step.")
                message = choice["message"]
                if not isinstance(message, dict):
                    raise TypeError
                return message
            except (KeyError, IndexError, TypeError):
                raise MetaError("Meta returned an unexpected response format.") from None

    def structured(self, messages, schema):
        message = self.completion(messages, schema=schema)
        try:
            return schema.model_validate_json(message["content"])
        except (KeyError, TypeError, ValueError, ValidationError):
            raise MetaError("Meta output failed schema validation; nothing was accepted.", output_error=True)

    def verify(self):
        catalog = self.request("GET", "/models")
        entries = catalog.get("data") if isinstance(catalog, dict) else None
        if not isinstance(entries, list) or any(not isinstance(m, dict) or not isinstance(m.get("id"), str) for m in entries):
            raise MetaError("Meta returned an invalid model catalog.")
        if not any(m["id"] == self.model for m in entries):
            raise MetaError("The configured model is not listed for this Meta account.", 503)
        ping = self.structured([{"role": "developer", "content": "Return the object ok=true using the required JSON schema."},
                                {"role": "user", "content": "Verify this API connection."}], Ping)
        if not ping.ok:
            raise MetaError("Meta verification did not return the expected result.")
        return self.status() | {"verified": True, "generation_verified": True}


def strict_schema(schema):
    """Make all object properties required for Meta's strict JSON Schema mode."""
    if isinstance(schema, dict):
        schema = {k: strict_schema(v) for k, v in schema.items() if k not in {"default", "title"}}
        if schema.get("type") == "object":
            schema["additionalProperties"] = False
            schema["required"] = list(schema.get("properties", {}))
    elif isinstance(schema, list):
        return [strict_schema(v) for v in schema]
    return schema
