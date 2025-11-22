"""
response_generator_tools.py
Genera opciones usando herramientas especializadas según el contexto del cliente.
"""

import json
from openai import OpenAI
from utils.logger import logger
from utils.file_reader import get_close_context


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
- greet_user: Saluda al cliente de manera amigable (usar al inicio de la conversación).
- fix_doubts: Aborda dudas y preocupaciones sobre el producto o precio.
- add_details: Proporciona más información y detalles sobre el producto.
- add_scarcity: Genera urgencia o escasez para impulsar el cierre.
- search_offers: Presenta promociones o descuentos disponibles.
- close_sale: Cierra la venta siguiendo los próximos pasos definidos (usar cuando el cliente está listo).
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
3. Si es el primer mensaje o saludo, usa greet_user.
4. Si el cliente está listo para comprar o en etapa de cierre, usa close_sale.
5. Devuelve SOLO el nombre de la herramienta más adecuada entre: greet_user, fix_doubts, add_details, add_scarcity, search_offers, close_sale, default_tool
6. No agregues explicaciones ni ningún texto adicional.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        tool_name = response.choices[0].message.content.strip()
        logger.info(f"   → Herramienta seleccionada por OpenAI: {tool_name}")

        # Validar que sea una herramienta conocida
        valid_tools = ["greet_user", "fix_doubts", "add_details", "add_scarcity", "search_offers", "close_sale", "default_tool"]
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

    def greet_user(self, sentiment_analysis, client_context, product_context, stage):
        """
        Saluda al cliente usando su nombre y un mensaje amigable.
        """
        client_name = client_context.get("name", "Cliente")
        prompt = f"""
Genera 3 opciones de saludo en formato JSON para un cliente llamado {client_name}:

[
  {{ "id": "directa", "intent": "saludo", "text": "..." }},
  {{ "id": "consultiva", "intent": "saludo", "text": "..." }},
  {{ "id": "empatica", "intent": "saludo", "text": "..." }}
]

- directa: saludo profesional y breve
- consultiva: saludo interactivo preguntando cómo se encuentra
- empatica: saludo cálido y cercano
Devuelve JSON EXACTO. No agregues texto adicional fuera del JSON.
"""
        return self._call_openai(prompt)

    def close_sale(self, sentiment_analysis, client_context, product_context, stage):
        """
        Genera 3 opciones de cierre basadas en los próximos pasos definidos en close_context,
        manteniendo un tono conversacional y persuasivo.
        """
        close_context = get_close_context()  # Debe devolver los pasos próximos que queremos sugerir
        fragments = [f['text'] for f in sentiment_analysis.get('sentiments', [])]

        prompt = f"""
El cliente está interesado y en etapa de cierre. Genera 3 opciones de respuesta
basadas EXCLUSIVAMENTE en los próximos pasos indicados en el close_context:
{close_context}

Considera:
- Producto: {product_context}
- Contexto del cliente: {client_context}
- Fragmentos detectados del cliente: {fragments}

Instrucciones:
1. Mantén un estilo conversacional y cercano.
2. Persuade al cliente a seguir los próximos pasos definidos en close_context.
3. Devuelve exactamente 3 opciones en formato JSON con IDs:
   - directa: cierre contundente
   - consultiva: cierre preguntando si quiere avanzar
   - empatica: cierre mostrando comprensión y seguridad
4. No inventes pasos que no estén en close_context.
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
        
        # Log the raw response for debugging
        logger.debug(f"Raw OpenAI response: {result_text[:200]}...")

        try:
            # Try to extract JSON if it's wrapped in markdown code blocks
            if result_text.startswith("```"):
                # Remove markdown code blocks
                result_text = result_text.strip("`").strip()
                if result_text.startswith("json"):
                    result_text = result_text[4:].strip()
            
            options = json.loads(result_text)
            
            # Validate structure
            if not isinstance(options, list):
                raise ValueError(f"Expected list, got {type(options).__name__}")
            if len(options) != 3:
                raise ValueError(f"Expected 3 options, got {len(options)}")
            
            # Validate each option has required fields
            for opt in options:
                if not isinstance(opt, dict):
                    raise ValueError(f"Option is not a dict: {opt}")
                if "id" not in opt or "intent" not in opt or "text" not in opt:
                    raise ValueError(f"Option missing required fields: {opt}")
            
            logger.debug(f"Successfully parsed {len(options)} options from OpenAI")
            return options
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}")
            logger.warning(f"Response text was: {result_text}")
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            logger.warning(f"Response text was: {result_text}")
        except Exception as e:
            logger.warning(f"Unexpected error parsing OpenAI response: {e}")
            logger.warning(f"Response text was: {result_text}")
        
        # Fallback options
        logger.warning("Using fallback options due to parsing error")
        return [
            {"id": "directa", "intent": "cierre", "text": "Podemos avanzar con la compra ahora mismo."},
            {"id": "consultiva", "intent": "pregunta", "text": "¿Puedes contarme más sobre tus prioridades?"},
            {"id": "empatica", "intent": "confianza", "text": "Entiendo tus preocupaciones, estoy aquí para ayudarte."}
        ]