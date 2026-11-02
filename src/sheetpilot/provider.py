"""Official Meta Model API client. Never falls back to simulated AI."""
import json
import os
import random
import time

from dotenv import dotenv_values
import httpx
from pydantic import ValidationError

from .config import ROOT
from .store import Problem
from .models import Ping


class MetaError(Problem):
    def __init__(self, message, status=502):
        super().__init__(message, status)


class MetaProvider:
    def __init__(self, key=None, model=None, transport=None):
        values = dotenv_values(ROOT / ".env")
        self.key = key if key is not None else (os.getenv("MODEL_API_KEY") or values.get("MODEL_API_KEY") or "")
        self.model = model or os.getenv("META_MODEL") or values.get("META_MODEL") or "muse-spark-1.3"
        self.base = "https://api.meta.ai/v1"
        self.transport = transport

    def status(self):
        return {"configured": bool(self.key.strip()), "model": self.model, "base_url": self.base}

    def request(self, method, path, payload=None):
        if not self.key.strip():
            raise MetaError("Meta is not configured. Add MODEL_API_KEY to the server's .env file.", 503)
        for attempt in range(3):
            try:
                with httpx.Client(timeout=60, transport=self.transport) as client:
                    response = client.request(method, self.base + path,
                        headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}, json=payload)
            except httpx.TimeoutException:
                if attempt < 2:
                    time.sleep(.3 * (2 ** attempt))
                    continue
                raise MetaError("Meta request timed out. Please retry.")
            except httpx.HTTPError:
                raise MetaError("Could not reach the official Meta API.")
            if response.status_code in {429, 500, 502, 503} and attempt < 2:
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
        payload = {"model": self.model, "messages": messages, "max_completion_tokens": 6000}
        if schema:
            payload["response_format"] = {"type": "json_schema", "json_schema": {
                "name": schema.__name__, "schema": strict_schema(schema.model_json_schema()), "strict": True}}
        if tools:
            payload.update(tools=tools, tool_choice="auto", parallel_tool_calls=False)
        data = self.request("POST", "/chat/completions", payload)
        try:
            choice = data["choices"][0]
            if choice.get("finish_reason") not in {"stop", "tool_calls"}:
                raise MetaError("Meta response was incomplete; no changes were applied.")
            return choice["message"]
        except (KeyError, IndexError, TypeError):
            raise MetaError("Meta returned an unexpected response format.")

    def structured(self, messages, schema):
        message = self.completion(messages, schema=schema)
        try:
            return schema.model_validate_json(message["content"])
        except (KeyError, TypeError, ValueError, ValidationError):
            raise MetaError("Meta output failed schema validation; nothing was accepted.")

    def verify(self):
        catalog = self.request("GET", "/models")
        if self.model not in {m.get("id") for m in catalog.get("data", [])}:
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
