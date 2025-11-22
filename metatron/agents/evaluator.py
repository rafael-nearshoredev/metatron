"""
evaluator.py
Evaluador de opciones para el agente closer usando OpenAI y contexto completo de la llamada.
La salida respeta exactamente el texto original de la opción seleccionada.
"""

import logging
import json
from openai import OpenAI
from metatron.utils.logger import logger
from metatron.utils.file_reader import get_lead_context, get_product_context
from metatron.config import settings

# Groq configuration
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "openai/gpt-oss-120b"


class Evaluator:
    """
    Evaluador que usa OpenAI para:
    - Revisar toda la conversación
    - Evaluar opciones generadas
    - Seleccionar la mejor opción sin alterar el texto original
    """

    def __init__(self, openai_api_key: str, model=DEFAULT_MODEL, temperature=0.5):
        self.client = OpenAI(
            base_url=GROQ_BASE_URL,
            api_key=openai_api_key
        )
        self.model = model
        self.temperature = temperature

    def evaluate(
        self,
        conversation_history: list,
        options: list,
        *,
        full_context: dict | None = None,
    ) -> dict:
        """
        conversation_history: lista de dicts {"role": "cliente"|"agente", "content": "..."}
        options: lista de dicts {"id": ..., "text": ..., "intent": ...}
        Optimized for prompt caching: static context in system message.
        """

        logger.info("➡️  Etapa 4: Preparando contexto para Groq…")

        client_info = get_lead_context()
        product_info = get_product_context()

        history_text = "\n".join(
            [f"{m.get('role', '').capitalize()}: {m.get('content', '')}" for m in conversation_history]
        )
        context_snapshot = self._format_context(full_context)

        options_text = "\n".join(
            [f"{o['id']} ({o['intent']}): {o['text']}" for o in options]
        )

        # STATIC content (will be cached across requests)
        system_message = f"""Eres un asistente experto en ventas.

### INFORMACIÓN DEL CLIENTE ###
{client_info}

### INFORMACIÓN DEL PRODUCTO ###
{product_info}

### INSTRUCCIONES ###
Tu tarea es analizar la conversación y las opciones de respuesta disponibles.
Indica cuál es la mejor opción para avanzar hacia el cierre.
Solo devuelve el ID de la opción que consideres óptima en formato JSON: {{"best_option_id": "<ID>"}}.
No modifiques el texto de la opción.

### CONTEXTO COMPLETO ###
{context_snapshot}
"""

        # DYNAMIC content (changes per request)
        user_message = f"""### CONVERSACIÓN ###
{history_text}

### OPCIONES DISPONIBLES ###
{options_text}

Selecciona la mejor opción:"""

        logger.info("➡️  Etapa 4: Enviando solicitud a Groq (optimizado para caching)…")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=self.temperature
        )

        # Log cache usage
        if hasattr(response, 'usage') and response.usage:
            prompt_tokens = response.usage.prompt_tokens
            cached_tokens = getattr(response.usage.prompt_tokens_details, 'cached_tokens', 0) if hasattr(response.usage, 'prompt_tokens_details') else 0
            cache_hit_rate = (cached_tokens / prompt_tokens * 100) if prompt_tokens > 0 else 0
            logger.info(f"   → Cache: {cached_tokens}/{prompt_tokens} tokens ({cache_hit_rate:.1f}% hit)")

        result_text = response.choices[0].message.content.strip()
        logger.info("   → Respuesta recibida de Groq")

        try:
            result_json = json.loads(result_text)
            best_option_id = result_json.get("best_option_id")
        except Exception:
            logger.warning("No se pudo parsear JSON de Groq. Se selecciona la primera opción por defecto.")
            best_option_id = options[0]["id"] if options else None

        # Buscar la opción original por ID
        best_option = next((o for o in options if o["id"] == best_option_id), options[0] if options else None)

        logger.info(f"   → Opción seleccionada (ID): {best_option_id}")
        if best_option:
            logger.info(f"   → Texto de la opción: {best_option['text']}")

        return {
            "mosfet": best_option_id,
            "response": best_option["text"] if best_option else ""
        }

    def _format_context(self, full_context: dict | None) -> str:
        if not full_context:
            return "No hay más contexto disponible."
        try:
            return json.dumps(full_context, indent=2, ensure_ascii=False)
        except Exception:
            return str(full_context)
