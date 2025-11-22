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

MODEL_NAME = "gpt-4o-mini"
# Note: This global client is initialized at module load time
# Individual instances should use their own client (see PersonalityAdapter.__init__)



class PersonalityAdapter:
    """
    Takes raw model text and adapts it to the personality profile.
    """

    def __init__(self, openai_api_key: str):
        logging.info("Initializing Personality Adapter")
        self.client = OpenAI(api_key=openai_api_key)

    def adapt(self, original_text: str) -> str:
        """
        Rewrite the original text into the desired persona style.
        """
        logging.info("Starting personality adaptation process")

        prompt = f"""
Adapta el siguiente texto a la personalidad descrita.

### PERSONALIDAD ###
{PERSONALITY_PROFILE}

### TEXTO ORIGINAL ###
{original_text}

### INSTRUCCIONES ###
- Mantén el significado original.
- Cambia únicamente estilo, tono y forma de expresarse.
- NO inventes datos.
- Responde solamente con el texto final adaptado.
- Manten los textos consisos

Texto final:
"""

        logging.info("Sending request to the LLM for rewriting")
        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        logging.info("Received personality-adapted response")
        return response.choices[0].message.content.strip()

 