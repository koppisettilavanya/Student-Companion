"""
Groq AI Service Module.
Handles all interactions with the official Groq Python SDK.
"""

import os
import time
import re
import math
import random
import logging
from typing import List, Dict, Any, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are GroqChat, a sophisticated, intelligent, and articulate conversational AI assistant. "
    "You provide accurate, well-structured, and helpful answers across general knowledge, programming, "
    "writing, mathematics, science, and problem-solving. "
    "Format code snippets with proper markdown code blocks including language identifiers. "
    "Use markdown headings, bullet points, numbered lists, and bold text for clarity and readability."
)

DEFAULT_MODEL = "qwen/qwen3.8-27b"

SUPPORTED_MODELS = [
    {
        "id": "qwen/qwen3.8-27b",
        "name": "Qwen 3.8 27B",
        "description": "Ultra-fast, highly capable reasoning and general chat on Groq LPU (Recommended)",
        "context_window": 131072,
    },
    {
        "id": "openai/gpt-oss-120b",
        "name": "GPT-OSS 120B",
        "description": "State-of-the-art 120B parameter open weights model with deep reasoning",
        "context_window": 131072,
    },
    {
        "id": "openai/gpt-oss-20b",
        "name": "GPT-OSS 20B",
        "description": "Fast and lightweight 20B open weights model for rapid answers",
        "context_window": 131072,
    },
    {
        "id": "allam-2-7b",
        "name": "ALLaM 2 7B",
        "description": "Efficient multilingual conversational model",
        "context_window": 32768,
    },
    {
        "id": "llama-3.3-70b-versatile",
        "name": "Llama 3.3 70B Versatile",
        "description": "Meta Llama 3.3 70B parameter model",
        "context_window": 128000,
    },
    {
        "id": "llama-3.1-8b-instant",
        "name": "Llama 3.1 8B Instant",
        "description": "Ultra-fast responses for quick queries",
        "context_window": 128000,
    },
]


def parse_reset_time(header_val: Optional[str]) -> Optional[float]:
    """
    Parses Groq rate-limit reset header values like '480ms', '1.38s', '1m26.4s' or numeric seconds.
    Returns float seconds or None.
    """
    if not header_val:
        return None
    val = str(header_val).strip()
    if not val:
        return None
    if val.endswith('ms'):
        try:
            return max(float(val[:-2]) / 1000.0, 0.1)
        except (ValueError, TypeError):
            return None
    if 'm' in val and val.endswith('s'):
        match = re.match(r'(?:(\d+)m)?([\d\.]+)s', val)
        if match:
            mins = float(match.group(1)) if match.group(1) else 0.0
            secs = float(match.group(2)) if match.group(2) else 0.0
            return max(mins * 60.0 + secs, 0.1)
    if val.endswith('s'):
        try:
            return max(float(val[:-1]), 0.1)
        except (ValueError, TypeError):
            return None
    try:
        return max(float(val), 0.1)
    except (ValueError, TypeError):
        return None


class GroqServiceError(Exception):
    """Custom exception class for Groq AI service errors."""
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = 'GROQ_ERROR',
        retry_after: Optional[float] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.retry_after = retry_after


class GroqService:
    """
    Dedicated service handling authentication, conversation payload creation,
    context management, and Groq API completions.
    """

    @classmethod
    def get_api_key(cls, runtime_key: Optional[str] = None) -> str:
        """
        Resolves API key from runtime header/parameter or environment variable.
        """
        if runtime_key and runtime_key.strip():
            return runtime_key.strip()
        
        env_key = getattr(settings, 'GROQ_API_KEY', '') or os.getenv('GROQ_API_KEY', '')
        return env_key.strip() if env_key else ''

    @classmethod
    def get_model(cls, runtime_model: Optional[str] = None) -> str:
        """
        Resolves model name from runtime preference or environment variable.
        """
        if runtime_model and runtime_model.strip():
            return runtime_model.strip()
        
        env_model = getattr(settings, 'GROQ_MODEL', '') or os.getenv('GROQ_MODEL', '')
        return env_model.strip() if env_model else DEFAULT_MODEL

    @classmethod
    def get_client(cls, api_key: str):
        """
        Initializes and returns an official Groq client instance.
        """
        try:
            from groq import Groq
            return Groq(api_key=api_key)
        except ImportError as exc:
            logger.error("groq package is not installed: %s", exc)
            raise GroqServiceError(
                "The Groq Python SDK is not installed on the server. Please run 'pip install groq'.",
                status_code=500,
                error_code='SDK_NOT_INSTALLED'
            ) from exc

    @classmethod
    def is_configured(cls, runtime_key: Optional[str] = None) -> bool:
        """
        Checks whether a valid API key is present in environment or runtime.
        """
        key = cls.get_api_key(runtime_key)
        return bool(key and len(key) > 10 and not key.startswith('your_groq_api_key'))

    @classmethod
    def get_supported_models(cls, runtime_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Dynamically discovers models available to the active Groq API key,
        merging with curated model metadata.
        """
        api_key = cls.get_api_key(runtime_key)
        if not api_key:
            return SUPPORTED_MODELS

        try:
            client = cls.get_client(api_key)
            models_data = client.models.list().data
            available_ids = {m.id for m in models_data}

            # First, match available models that are in our curated list
            curated_map = {m['id']: m for m in SUPPORTED_MODELS}
            results = []

            for m in SUPPORTED_MODELS:
                if m['id'] in available_ids:
                    results.append(m)

            # Next, append any additional chat models from the account
            for m in models_data:
                mid = m.id
                if mid not in curated_map and not any(mid.startswith(p) for p in ('whisper', 'meta-llama/llama-prompt-guard')):
                    results.append({
                        'id': mid,
                        'name': mid,
                        'description': f'Groq active model ({getattr(m, "owned_by", "Groq")})',
                        'context_window': 32768,
                    })

            return results if results else SUPPORTED_MODELS
        except Exception as exc:
            logger.warning("Could not dynamically query Groq models: %s", exc)
            return SUPPORTED_MODELS

    @classmethod
    def generate_chat_response(
        cls,
        conversation_history: List[Dict[str, str]],
        user_message: str,
        runtime_key: Optional[str] = None,
        runtime_model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        max_tokens: Optional[int] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Sends conversation messages to Groq and returns the generated text and metadata.
        Implements intelligent token budgeting, automatic retry with exponential backoff on HTTP 429,
        OTPM token scaling, and automatic model fallback.
        Endpoint: https://api.groq.com/openai/v1/chat/completions (via official Groq SDK).
        """
        api_key = cls.get_api_key(runtime_key)
        if not api_key or api_key.startswith('your_groq_api_key'):
            raise GroqServiceError(
                "Groq API key is not configured. Please add GROQ_API_KEY to your .env file "
                "or set it in the Settings dialog (get a free key at https://console.groq.com/keys).",
                status_code=401,
                error_code='MISSING_API_KEY'
            )

        model = cls.get_model(runtime_model)
        client = cls.get_client(api_key)

        # Assemble messages payload with system prompt first
        messages = [
            {"role": "system", "content": system_instruction or SYSTEM_PROMPT}
        ]

        # Smart context window management: keep sliding window of recent messages
        # bounded by both count (last 12) and character budget (~6,000 chars) to stay safely inside 8,000 TPM limit
        trimmed_history = conversation_history[-12:] if len(conversation_history) > 12 else conversation_history
        char_budget = 6000
        accumulated_history = []
        for msg in reversed(trimmed_history):
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role in ('user', 'assistant') and content:
                if len(content) > char_budget:
                    truncated = content[:char_budget] + "... [earlier context trimmed for brevity]"
                    accumulated_history.append({"role": role, "content": truncated})
                    break
                else:
                    accumulated_history.append({"role": role, "content": content})
                    char_budget -= len(content)
                    if char_budget <= 0:
                        break

        for msg in reversed(accumulated_history):
            messages.append(msg)

        # Append the new user message
        messages.append({"role": "user", "content": user_message})

        # Sensible initial max_tokens: default to 1024 for chat to respect Groq Free Tier 1000 OTPM
        curr_max_tokens = max_tokens if max_tokens is not None else 1024
        curr_model = model

        try:
            from groq import (
                AuthenticationError,
                RateLimitError,
                APIConnectionError,
                BadRequestError,
                NotFoundError,
                APIStatusError,
            )
        except ImportError as exc:
            raise GroqServiceError(
                "The Groq Python SDK is not installed on the server. Please run 'pip install groq'.",
                status_code=500,
                error_code='SDK_NOT_INSTALLED'
            ) from exc

        last_rate_limit_err = None

        for attempt in range(max_retries + 1):
            try:
                completion = client.chat.completions.create(
                    model=curr_model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=curr_max_tokens,
                    top_p=1.0,
                    stream=False
                )
                # Success - break out of retry loop
                break

            except NotFoundError as model_err:
                logger.warning(
                    "Requested model '%s' returned 404 (model_not_found). Searching available models for fallback...",
                    curr_model
                )
                try:
                    available_models = client.models.list().data
                    chat_candidates = [
                        m.id for m in available_models
                        if not any(m.id.startswith(p) for p in ('whisper', 'meta-llama/llama-prompt-guard'))
                    ]
                    fallback_model = None
                    if chat_candidates:
                        for preferred in ('qwen/qwen3.8-27b', 'openai/gpt-oss-120b', 'openai/gpt-oss-20b', 'allam-2-7b'):
                            if preferred in chat_candidates:
                                fallback_model = preferred
                                break
                        if not fallback_model:
                            fallback_model = chat_candidates[0]

                    if fallback_model and fallback_model != curr_model:
                        logger.info("Retrying chat completion with fallback model: %s", fallback_model)
                        curr_model = fallback_model
                        completion = client.chat.completions.create(
                            model=curr_model,
                            messages=messages,
                            temperature=0.7,
                            max_tokens=curr_max_tokens,
                            top_p=1.0,
                            stream=False
                        )
                        break
                    else:
                        raise model_err
                except Exception as fallback_exc:
                    if fallback_exc is not model_err:
                        logger.error("Fallback attempt failed: %s", fallback_exc)
                    err_msg = ""
                    if hasattr(model_err, 'body') and isinstance(model_err.body, dict):
                        err_msg = model_err.body.get('error', {}).get('message', '')
                    if not err_msg:
                        err_msg = str(model_err)
                    raise GroqServiceError(
                        f"Groq Model Not Found (HTTP 404): {err_msg}",
                        status_code=404,
                        error_code='MODEL_NOT_FOUND'
                    ) from model_err

            except RateLimitError as rate_err:
                last_rate_limit_err = rate_err
                headers = getattr(rate_err.response, 'headers', {}) if hasattr(rate_err, 'response') else {}
                reset_header = headers.get('x-ratelimit-reset-tokens') or headers.get('retry-after')
                parsed_wait = parse_reset_time(reset_header)

                err_msg = ""
                if hasattr(rate_err, 'body') and isinstance(rate_err.body, dict):
                    err_msg = rate_err.body.get('error', {}).get('message', '')
                if not err_msg:
                    err_msg = str(rate_err)

                is_otpm = 'OTPM' in err_msg or 'output tokens' in err_msg.lower() or 'reduce max_tokens' in err_msg.lower()

                if attempt < max_retries:
                    # Exponential backoff calculation: wait for Groq reset or calculate exponential delay with jitter
                    base_delay = 1.0 * (1.8 ** attempt)
                    jitter = random.uniform(0.1, 0.4)
                    if parsed_wait is not None:
                        delay = min(max(parsed_wait + 0.15, 0.5), 8.0)
                    else:
                        delay = min(base_delay + jitter, 8.0)

                    if is_otpm:
                        # Scale down tokens to fit within remaining rolling budget
                        curr_max_tokens = max(int(curr_max_tokens * 0.75), 512)
                        logger.warning(
                            "Groq OTPM rate limit reached (attempt %d/%d). Scaled max_tokens to %d. Backing off for %.2fs...",
                            attempt + 1, max_retries, curr_max_tokens, delay
                        )
                    else:
                        logger.warning(
                            "Groq rate limit reached (attempt %d/%d). Backing off for %.2fs...",
                            attempt + 1, max_retries, delay
                        )

                    time.sleep(delay)
                    continue

                # All retries on primary model reached. Check if an alternate chat model is available
                fallback_succeeded = False
                try:
                    available_models = client.models.list().data
                    candidates = [
                        m.id for m in available_models
                        if m.id != curr_model and not any(m.id.startswith(p) for p in ('whisper', 'meta-llama/llama-prompt-guard'))
                    ]
                    for alt_model in candidates[:2]:
                        try:
                            logger.info("Attempting rate-limit model fallback to '%s' with max_tokens=%d...", alt_model, min(curr_max_tokens, 768))
                            completion = client.chat.completions.create(
                                model=alt_model,
                                messages=messages,
                                temperature=0.7,
                                max_tokens=min(curr_max_tokens, 768),
                                top_p=1.0,
                                stream=False
                            )
                            curr_model = alt_model
                            fallback_succeeded = True
                            break
                        except Exception as alt_err:
                            logger.warning("Fallback model '%s' also rejected: %s", alt_model, alt_err)
                except Exception:
                    pass

                if fallback_succeeded:
                    break

                # Truly exhausted after retries and fallback
                wait_display = math.ceil(parsed_wait) if parsed_wait else 3
                logger.warning("Groq rate limit exhausted after %d retries. Reset in ~%ds: %s", max_retries, wait_display, err_msg)
                raise GroqServiceError(
                    f"Groq API rate limit reached (Free Tier limit: 1,000 output tokens/min). "
                    f"Please wait {wait_display} seconds and click Retry, or switch models in Settings.",
                    status_code=429,
                    error_code='RATE_LIMITED',
                    retry_after=float(wait_display)
                ) from rate_err

            except AuthenticationError as exc:
                logger.error("Groq Authentication error: %s", exc)
                raise GroqServiceError(
                    "Invalid Groq API key. Please check your credentials in .env or the Settings panel.",
                    status_code=401,
                    error_code='INVALID_API_KEY'
                ) from exc

            except APIConnectionError as exc:
                logger.error("Groq connection error: %s", exc)
                raise GroqServiceError(
                    "Unable to connect to the Groq API server. Please check your internet connection.",
                    status_code=503,
                    error_code='NETWORK_ERROR'
                ) from exc

            except BadRequestError as exc:
                logger.error("Groq Bad Request: %s", exc)
                err_msg = ""
                if hasattr(exc, 'body') and isinstance(exc.body, dict):
                    err_msg = exc.body.get('error', {}).get('message', '')
                if not err_msg:
                    err_msg = str(exc)
                raise GroqServiceError(
                    f"Groq API Bad Request (HTTP 400): {err_msg}",
                    status_code=400,
                    error_code='BAD_REQUEST'
                ) from exc

            except GroqServiceError:
                raise

            except APIStatusError as exc:
                logger.error("Groq API status error: %s", exc)
                err_msg = ""
                if hasattr(exc, 'body') and isinstance(exc.body, dict):
                    err_msg = exc.body.get('error', {}).get('message', '')
                if not err_msg:
                    err_msg = str(exc)
                status_code = getattr(exc, 'status_code', 500)
                raise GroqServiceError(
                    f"Groq service error (HTTP {status_code}): {err_msg}",
                    status_code=status_code,
                    error_code='SERVICE_ERROR'
                ) from exc

            except Exception as exc:
                logger.exception("Unexpected error communicating with Groq: %s", exc)
                raise GroqServiceError(
                    f"An unexpected error occurred while communicating with the AI service: {str(exc)}",
                    status_code=500,
                    error_code='UNKNOWN_ERROR'
                ) from exc

        if not completion or not completion.choices or len(completion.choices) == 0:
            raise GroqServiceError(
                "Groq returned an empty response. Please try asking again.",
                status_code=502,
                error_code='EMPTY_RESPONSE'
            )

        choice = completion.choices[0]
        response_content = choice.message.content or ""

        usage = {}
        if hasattr(completion, 'usage') and completion.usage:
            usage = {
                'prompt_tokens': completion.usage.prompt_tokens,
                'completion_tokens': completion.usage.completion_tokens,
                'total_tokens': completion.usage.total_tokens,
            }

        return {
            'content': response_content,
            'model': curr_model,
            'finish_reason': choice.finish_reason,
            'usage': usage,
        }
