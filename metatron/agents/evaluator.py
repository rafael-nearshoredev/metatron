"""
evaluator.py
Evaluador de opciones para el agente closer.
"""

"""
evaluator_openai.py
Evaluador de opciones para el agente closer usando OpenAI y contexto completo de la llamada.
"""

import logging
from openai import OpenAI
from utils.logger import logger
from utils.file_reader import get_lead_context, get_product_context
from config import settings




class Evaluator:
    """
    Evaluador que usa OpenAI para:
    - Revisar toda la conversación
    - Evaluar opciones generadas
    - Decidir la mejor opción
    - Generar una respuesta concisa
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
        get_client_info_func(client_id) -> dict
        get_product_info_func(product_id) -> dict
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

        prompt = f"""
Eres un asistente experto en ventas. 
Tu tarea es:

1. Analizar toda la conversación de un cliente.
2. Revisar la información del cliente: {client_info}
3. Revisar la información del producto: {product_info}
4. Revisar las opciones disponibles: {options_text}
5. Evaluar cuál opción es la más adecuada para avanzar hacia el cierre.
6. Generar la respuesta final concisa para el cliente.
7. Devuelve la opción seleccionada en MOSFET (Most Optimal Selection For Effective Transaction) y un texto final conciso como respuesta.

Historial de conversación:
{history_text}

Instrucciones:
- Selecciona la mejor opción y explícala en MOSFET.
- Genera un texto conciso y persuasivo para el cliente.
- Responde solo con JSON con dos campos: "mosfet" y "response".

"""

        logger.info("➡️  Etapa 4: Enviando solicitud a OpenAI…")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature
        )

        result_text = response.choices[0].message["content"].strip()
        logger.info("   → Respuesta recibida de OpenAI")

        try:
            import json
            result_json = json.loads(result_text)
        except Exception:
            result_json = {"mosfet": "unknown", "response": result_text}

        logger.info(f"   → MOSFET: {result_json.get('mosfet')}")
        logger.info(f"   → Response: {result_json.get('response')}")

        return result_json
    