"""
evaluator.py
Evaluador de opciones para el agente closer usando OpenAI y contexto completo de la llamada.
La salida respeta exactamente el texto original de la opción seleccionada.
"""

import logging
import json
from openai import OpenAI
from utils.logger import logger
from utils.file_reader import get_lead_context, get_product_context
from config import settings


class Evaluator:
    """
    Evaluador que usa OpenAI para:
    - Revisar toda la conversación
    - Evaluar opciones generadas
    - Seleccionar la mejor opción sin alterar el texto original
    """

    def __init__(self, openai_api_key: str, model="gpt-4o-mini", temperature=0.7):
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model
        self.temperature = temperature

    def evaluate(
        self,
        conversation_history: list,
        options: list,
    ) -> dict:
        """
        conversation_history: lista de dicts {"role": "cliente"|"agente", "content": "..."}
        options: lista de dicts {"id": ..., "text": ..., "intent": ...}
        """

        logger.info("➡️  Etapa 4: Preparando contexto para OpenAI…")

        client_info = get_lead_context()
        product_info = get_product_context()

        history_text = "\n".join(
            [f"{m['role'].capitalize()}: {m['content']}" for m in conversation_history]
        )

        options_text = "\n".join(
            [f"{o['id']} ({o['intent']}): {o['text']}" for o in options]
        )

        # Prompt: solo pedir el ID de la mejor opción
        prompt = f"""
Eres un asistente experto en ventas.

Analiza la conversación completa del cliente, la información del cliente {client_info} y la información del producto {product_info}.
Luego, revisa estas opciones disponibles:

{options_text}

Indica cuál es la mejor opción para avanzar hacia el cierre. Solo devuelve el ID de la opción que consideres óptima en formato JSON:
{{"best_option_id": "<ID>"}}. No modifiques el texto de la opción.
"""

        logger.info("➡️  Etapa 4: Enviando solicitud a OpenAI…")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature
        )

        result_text = response.choices[0].message.content.strip()
        logger.info("   → Respuesta recibida de OpenAI")

        try:
            result_json = json.loads(result_text)
            best_option_id = result_json.get("best_option_id")
        except Exception:
            logger.warning("No se pudo parsear JSON de OpenAI. Se selecciona la primera opción por defecto.")
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