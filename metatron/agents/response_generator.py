"""
response_generator_tools.py
Genera opciones usando herramientas especializadas según el contexto del cliente.
"""

import json
from openai import OpenAI
from utils.logger import logger


class ResponseGenerator:
    """
    Generador de opciones de respuesta para el agente closer, con herramientas especializadas.
    """

    def __init__(self, openai_api_key: str, model="gpt-4o-mini", temperature=0.7):
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model
        self.temperature = temperature

    def generate_response(self, sentiment_analysis: dict, client_context: dict, product_context: dict, stage: str) -> list:
        """
        Selecciona la herramienta adecuada según el contexto y genera 3 opciones.
        """
        logger.info("➡️  Etapa 3: Analizando contexto y seleccionando herramienta…")

        tool_to_use = self.select_tool(sentiment_analysis, client_context, product_context, stage)
        logger.info(f"   → Herramienta seleccionada: {tool_to_use}")

        # Llama a la herramienta correspondiente
        options = getattr(self, tool_to_use)(
            sentiment_analysis, client_context, product_context, stage
        )

        logger.info("   → Opciones generadas por la herramienta:")
        for o in options:
            logger.info(f"      * {o['id']} ({o['intent']}): {o['text']}")

        return options

    # ---------------------------
    # Selector de herramientas
    # ---------------------------
    def select_tool(
        self, sentiment_analysis, client_context, product_context, stage
    ) -> str:
        """
        Selecciona la herramienta más adecuada usando OpenAI para analizar:
        - fragmentos negativos o dudas
        - contexto del cliente
        - contexto del producto
        - etapa de venta

        Devuelve el nombre de la herramienta a usar:
        "fix_doubts", "add_details", "add_scarcity", "search_offers", "default_tool"
        """
        logger.info("➡️  Seleccionando herramienta usando OpenAI…")

        # Preparamos la información para el prompt
        fragments_text = "\n".join([f"- {f['text']} ({f['label']}, {f['score']:.2f})"
                                    for f in sentiment_analysis.get("sentiments", [])])
        personality_insight = sentiment_analysis.get("personality_insight", "No disponible")

        prompt = f"""
Eres un asistente experto en ventas y análisis de conversación.
Tu tarea es seleccionar la herramienta más adecuada para generar una respuesta al cliente.
Dispones de estas herramientas:
- fix_doubts: Aborda dudas y preocupaciones sobre el producto o precio.
- add_details: Proporciona más información y detalles sobre el producto.
- add_scarcity: Genera urgencia o escasez para impulsar el cierre.
- search_offers: Presenta promociones o descuentos disponibles.
- default_tool: Respuesta por defecto si no se detecta una necesidad específica.

Información disponible:
- Etapa del proceso: {stage}
- Contexto del cliente: {client_context}
- Contexto del producto: {product_context}
- Fragmentos y sentimientos detectados:
{fragments_text}
- Insight de personalidad: {personality_insight}

Instrucciones:
1. Analiza los fragmentos y sentimientos del cliente.
2. Toma en cuenta la etapa del proceso y el contexto del cliente y producto.
3. Devuelve SOLO el nombre de la herramienta más adecuada entre: fix_doubts, add_details, add_scarcity, search_offers, default_tool
4. No agregues explicaciones ni ningún texto adicional.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        tool_name = response.choices[0].message.content.strip()
        logger.info(f"   → Herramienta seleccionada por OpenAI: {tool_name}")

        # Validar que sea una herramienta conocida
        valid_tools = ["fix_doubts", "add_details", "add_scarcity", "search_offers", "default_tool"]
        if tool_name not in valid_tools:
            logger.warning(f"OpenAI devolvió un nombre de herramienta inválido: {tool_name}. Usando default_tool.")
            tool_name = "default_tool"

        return tool_name

    # ---------------------------
    # Herramientas / técnicas de venta
    # ---------------------------
    def fix_doubts(self, sentiment_analysis, client_context, product_context, stage):
        """
        Aborda dudas o preocupaciones del cliente usando técnica consultiva.
        """
        prompt = f"""
Eres un asistente experto en ventas. El cliente tiene dudas o preocupaciones.
Genera 3 opciones de respuesta persuasivas usando información del producto:
{product_context}
Basadas en los siguientes fragmentos con problemas:
{[f['text'] for f in sentiment_analysis.get('sentiments', []) if f['label'] in ('NEG','NEU')]}
Devuelve JSON exacto con 3 opciones: directa, consultiva y empatica.
"""
        return self._call_openai(prompt)


    def add_details(self, sentiment_analysis, client_context, product_context, stage):
        """
        Añade detalles adicionales del producto para convencer al cliente.
        """
        prompt = f"""
El cliente solicita más detalles sobre el producto. Usa la información del producto para generar 3 opciones persuasivas:
{product_context}
Devuelve JSON exacto con 3 opciones: directa, consultiva y empatica.
"""
        return self._call_openai(prompt)

    def add_scarcity(self, sentiment_analysis, client_context, product_context, stage):
        """
        Genera sentido de urgencia / escasez para impulsar el cierre.
        """
        prompt = f"""
El cliente está en etapa de cierre. Usa técnicas de escasez y urgencia para generar 3 opciones persuasivas:
{product_context}
Devuelve JSON exacto con 3 opciones: directa, consultiva y empatica.
"""
        return self._call_openai(prompt)


    def search_offers(self, sentiment_analysis, client_context, product_context, stage):
        """
        Muestra ofertas disponibles para convencer al cliente.
        """
        prompt = f"""
El cliente menciona descuentos o promociones. Genera 3 opciones persuasivas basadas en ofertas:
{product_context}
Devuelve JSON exacto con 3 opciones: directa, consultiva y empatica.
"""
        return self._call_openai(prompt)


    def default_tool(self, sentiment_analysis, client_context, product_context, stage):
        """
        Genera respuestas por defecto si no se detecta ninguna necesidad específica.
        """
        prompt = f"""
Genera 3 opciones de respuesta persuasivas basadas en la información del cliente y producto:
Cliente: {client_context}
Producto: {product_context}
Devuelve JSON exacto con 3 opciones: directa, consultiva y empatica.
"""
        return self._call_openai(prompt)

    # ---------------------------
    # Función común para llamar OpenAI
    # ---------------------------
    def _call_openai(self, prompt: str) -> list:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature
        )
        result_text = response.choices[0].message.content.strip()

        try:
            options = json.loads(result_text)
            if not isinstance(options, list) or len(options) != 3:
                raise ValueError("Formato inesperado de opciones")
        except Exception as e:
            logger.warning(f"No se pudo parsear JSON de OpenAI: {e}. Se generan opciones fallback.")
            options = [
                {"id": "directa", "intent": "cierre", "text": "Podemos avanzar con la compra ahora mismo."},
                {"id": "consultiva", "intent": "pregunta", "text": "¿Puedes contarme más sobre tus prioridades?"},
                {"id": "empatica", "intent": "confianza", "text": "Entiendo tus preocupaciones, estoy aquí para ayudarte."}
            ]
        return options