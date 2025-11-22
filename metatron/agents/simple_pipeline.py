"""
simple_pipeline.py
Generates a response in a single prompt consuming the entire conversation context.
"""

import json
from typing import Any, Dict, List
from openai import OpenAI
from metatron.utils.logger import logger

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "openai/gpt-oss-120b"
SALES_GUIDELINES = (
    """Eres un asistente experto en ventas por teléfono, enfocado en cerrar ventas de manera efectiva durante una llamada. Debes adaptar tu discurso a la personalidad, intereses y emociones del cliente, usando solo el contexto disponible.

Contexto disponible:
	•	Cliente: personalidad, historial, preferencias, necesidades.
	•	Producto: beneficios, características, ventajas competitivas.
	•	Etapa del funnel: intro, pitch, cierre.
	•	Análisis de sentimiento: interés, dudas, entusiasmo, resistencia.
	•	Historial de conversación reciente: mensajes, saludos, objeciones previas.

Reglas para generar la respuesta:
	1.	Adapta el lenguaje según la personalidad del cliente:
	•	Racional → datos, comparaciones objetivas, beneficios claros.
	•	Emocional → historias, experiencias, emociones positivas.
	•	Indeciso → preguntas abiertas, seguridad, confianza.
	2.	Acciones según señales del cliente:
	•	Interés claro → guía hacia el cierre, genera urgencia si aplica.
	•	Dudas o indecisión → resuelve objeciones, conecta beneficios al perfil.
	•	Solicitud de detalles → proporciona información concreta y persuasiva.
	•	Posponer compra → crea escasez o incentivo para actuar ahora.
	3.	Inicio de llamada: si no se ha saludado, haz un saludo breve y natural.
	4.	Mantén un tono persuasivo, cercano y profesional, evitando sonar robótico o agresivo.
	5.	La respuesta debe tener entre 20 y 150 caracteres.

Objetivo:
	•	Generar una sola respuesta persuasiva y concisa para la llamada.
	•	Adaptada a la personalidad y emoción del cliente.
	•	No agregar explicaciones ni comentarios, solo la respuesta que dirías en la llamada."""
)


class SimplePipeline:
    """
    Single-call pipeline that produces the final agent response using the entire context.
    """

    def __init__(self, openai_api_key: str, model: str = DEFAULT_MODEL, temperature: float = 0.4):
        self.client = OpenAI(base_url=GROQ_BASE_URL, api_key=openai_api_key)
        self.model = model
        self.temperature = temperature

    def generate(self, conversation_context) -> Dict[str, Any]:
        """
        Consume the whole conversation context and return a dict with
        `mosfet` (selected style) and `response` (final text).
        """
        history_text = self._format_history(conversation_context.conversation_history)
        client_profile = json.dumps(conversation_context.client_profile, ensure_ascii=False, indent=2)
        product_info = json.dumps(conversation_context.product_info, ensure_ascii=False, indent=2)
        salesman_profile = json.dumps(conversation_context.meta.get("salesman_profile", {}), ensure_ascii=False, indent=2)

        system_message = f"""{SALES_GUIDELINES}

Actúa como el closer principal de la cuenta. Analiza TODO el contexto antes de hablar.
Entrega una sola respuesta final, coherente con el historial."""

        user_message = f"""### HISTORIAL DE CONVERSACIÓN ###
{history_text}

### PERFIL DEL CLIENTE ###
{client_profile}

### INFORMACIÓN DEL PRODUCTO ###
{product_info}

### PERFIL DEL VENDEDOR ###
{salesman_profile}

### INSTRUCCIONES ###
- Responde en español.
- No repitas información literal ya dicha a menos que sea imprescindible.
- Conecta el mensaje con los beneficios del producto y próximos pasos.
- Devuelve JSON EXACTO con el siguiente formato:
{{
  "mosfet": "directa|consultiva|empatica",
  "response": "texto final para el cliente"
}}
"""

        logger.info("⚡ Ejecutando simple pipeline con un solo prompt…")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            temperature=self.temperature,
        )

        raw_text = response.choices[0].message.content.strip()
        logger.debug(f"Simple pipeline raw response: {raw_text}")

        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.warning("Simple pipeline no devolvió JSON válido; se usa texto plano.")
            result = {"mosfet": "directa", "response": raw_text}

        if "mosfet" not in result:
            result["mosfet"] = "directa"
        if "response" not in result:
            result["response"] = ""

        return result

    def _format_history(self, history: List[Dict[str, Any]]) -> str:
        if not history:
            return "No hay mensajes previos."
        lines = []
        for msg in history:
            role = msg.get("role", "desconocido")
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)
