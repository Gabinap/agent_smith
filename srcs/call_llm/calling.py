"""The link between an agent and an OpenAI-compatible chat API."""

import datetime
import json
import os
import time
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
from openai.types.chat import ChatCompletion


class LLM:
    """Hold one conversation with the model and its API keys."""

    def __init__(self, api_url: str, model_name: str, env_keys: list[str],
                 system_content: str, tools: Any = None) -> None:
        """Resolve the API keys and open the chat with its system prompt.

        Args:
            api_url: Base url of the provider.
            model_name: Name of the model to call.
            env_keys: Names of the .env variables holding the API keys.
            system_content: System prompt opening the conversation.
            tools: Unused, kept until agent_swebench stops passing it.
        """
        self.api_url = api_url
        self.model_name = model_name
        self.log_file: str | None = "llm_responses.jsonl"
        self._system_content = system_content
        self._api_keys = self._load_keys(env_keys)
        self._key_index = 0
        self.client = self._load_llm()
        self.messages: list[Any] = [
            {"role": "system", "content": system_content},
        ]

    def _load_keys(self, env_keys: list[str]) -> list[str]:
        """Return the API keys the .env defines among `env_keys`."""
        load_dotenv()
        keys = [key for name in env_keys if (key := os.getenv(name))]
        if not keys:
            raise ValueError(
                f"No API key found in .env for: {', '.join(env_keys)}")
        return keys

    def _load_llm(self) -> OpenAI:
        """Return a client bound to the currently selected API key."""
        return OpenAI(
            api_key=self._api_keys[self._key_index],
            base_url=self.api_url,
            timeout=120.0,
        )

    def _next_key(self) -> bool:
        """Switch to the next API key, False when none is left."""
        if self._key_index + 1 >= len(self._api_keys):
            return False
        self._key_index += 1
        self.client = self._load_llm()
        return True

    def _append_prompt(self, prompt: str) -> None:
        """Queue `prompt` on the first call only."""
        if len(self.messages) <= 1:
            self.messages.append({"role": "user", "content": prompt})

    def _create_completion(self) -> tuple[ChatCompletion, int]:
        """Send the conversation, rotating keys while rate limited.

        Returns the completion and the retries it cost: one per
        rejected attempt, for this API call only. The counter is local,
        so it starts back at zero on the next call — unlike the key
        index, which keeps moving forward.
        """
        retries = 0
        while True:
            try:
                completion = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=self.messages,
                )
                return completion, retries
            except RateLimitError:
                if not self._next_key():
                    raise ValueError("Every API key is rate limited")
                retries += 1
            except Exception as error:
                raise ValueError(f"Api connection failed: {error}")

    @staticmethod
    def _split_thought(response: Any) -> tuple[str, str]:
        """Split a reply into its reasoning part and its answer."""
        content = getattr(response, "content", None) or ""
        reasoning = getattr(response, "reasoning", None)
        for tag in ("</think>", "</thought>"):
            if tag in content:
                parts = content.split(tag)
                return parts[0], parts[-1]
        return reasoning or "No thought found", response.content

    def log_response(self, completion: ChatCompletion) -> None:
        """Append one API response to the JSONL log file."""
        if not self.log_file:
            return
        entry = {
            "timestamp": datetime.datetime.now().isoformat(
                timespec="seconds"),
            "model_name": self.model_name,
            "completion": json.loads(completion.model_dump_json()),
        }
        with open(self.log_file, "a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def call(self, prompt: str) -> dict[str, Any]:
        """Call the LLM through the API and return its reply.

        Args:
            prompt: Prompt input, used on the first call only.

        Returns:
            The answer, its reasoning, and the metrics of this single
            API call. `retries` covers this call alone; the agent
            reports it in the StepMetrics of the loop step around it,
            which spans every call that step made.
        """
        self._append_prompt(prompt)

        start = time.perf_counter()
        completion, retries = self._create_completion()
        elapsed = time.perf_counter() - start
        self.log_response(completion)
        response = completion.choices[0].message
        self.messages.append(response)

        thought, answer = self._split_thought(response)
        usage = completion.usage  # some providers omit it

        return {
            "input_tokens": usage.prompt_tokens if usage else None,
            "output_tokens": usage.completion_tokens if usage else None,
            "model_name": self.model_name,
            "thought": thought,
            "answer": answer,
            "request_time": f"{elapsed:.3f}",
            "retries": retries,
            "tool_calls": None,  # TODO: drop with agent_swebench's branch
        }
