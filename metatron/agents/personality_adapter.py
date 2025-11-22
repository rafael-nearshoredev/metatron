# personality_adapter.py
"""
Takes an input response and rewrites it to match the personality described
in a hardcoded persona profile.

It uses a lightweight OpenAI model (gpt-4o-mini or equivalent).
"""

import logging
from openai import OpenAI
from utils.logger import logger
from utils.file_reader import get_salesman_context
from config import settings


PERSONALITY_PROFILE = get_salesman_context()

# Groq model configuration
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MODEL_NAME = "openai/gpt-oss-120b"



class PersonalityAdapter:
    """
    Takes raw model text and adapts it to the personality profile.
    """

    def __init__(self, openai_api_key: str):
        logging.info("Initializing Personality Adapter with Groq")
        self.client = OpenAI(
            base_url=GROQ_BASE_URL,
            api_key=openai_api_key
        )

    def adapt(self, original_text: str) -> str:
        """
        Rewrite the original text into the desired persona style.
        Optimized for prompt caching: static content in system message, dynamic in user message.
        """
        logging.info("Starting personality adaptation process")

        # STATIC content (will be cached across requests)
        system_message = f"""Adapta el siguiente texto a la personalidad descrita.

### PERSONALIDAD ###
{PERSONALITY_PROFILE}

### INSTRUCCIONES ###
- Mantén el significado original.
- Cambia únicamente estilo, tono y forma de expresarse.
- NO inventes datos.
- Responde solamente con el texto final adaptado.
- Manten los textos consisos"""

        # DYNAMIC content (user-specific, changes each request)
        user_message = f"""### TEXTO ORIGINAL ###
{original_text}

Texto final:"""

        logging.info("Sending request to Groq for rewriting (optimized for caching)")
        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.8,
        )

        # Log cache usage
        if hasattr(response, 'usage') and response.usage:
            prompt_tokens = response.usage.prompt_tokens
            cached_tokens = getattr(response.usage.prompt_tokens_details, 'cached_tokens', 0) if hasattr(response.usage, 'prompt_tokens_details') else 0
            cache_hit_rate = (cached_tokens / prompt_tokens * 100) if prompt_tokens > 0 else 0
            logging.info(f"Cache usage: {cached_tokens}/{prompt_tokens} tokens cached ({cache_hit_rate:.1f}% hit rate)")

        logging.info("Received personality-adapted response")
        return response.choices[0].message.content.strip()

 