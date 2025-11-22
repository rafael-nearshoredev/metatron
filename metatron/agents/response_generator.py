"""
response_generator_tools.py
Genera opciones usando herramientas especializadas según el contexto del cliente.
"""

import json
from openai import OpenAI
from metatron.utils.logger import logger
from metatron.utils.file_reader import get_close_context

# Groq configuration
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "openai/gpt-oss-120b"


class ResponseGenerator:
    """
    Generador de opciones de respuesta para el agente closer, con herramientas especializadas.
    """

    def __init__(self, openai_api_key: str, model=DEFAULT_MODEL, temperature=0.7):
        self.client = OpenAI(
            base_url=GROQ_BASE_URL,
            api_key=openai_api_key
        )
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
        Selecciona la herramienta más adecuada usando Groq para analizar:
        - fragmentos negativos o dudas
        - contexto del cliente
        - contexto del producto
        - etapa de venta

        Devuelve el nombre de la herramienta a usar.
        Optimized for prompt caching: static tool definitions in system message.
        """
        logger.info("➡️  Seleccionando herramienta usando Groq…")

        # Preparamos la información para el prompt
        fragments_text = "\n".join([f"- {f['text']} ({f['label']}, {f['score']:.2f})"
                                    for f in sentiment_analysis.get("sentiments", [])])
        personality_insight = sentiment_analysis.get("personality_insight", "No disponible")

        # STATIC content (will be cached across requests)
        system_message = """Eres un asistente experto en ventas y análisis de conversación.
Tu tarea es seleccionar la herramienta más adecuada para generar una respuesta al cliente.

### HERRAMIENTAS DISPONIBLES ###
- greet_user: Saluda al cliente de manera amigable (usar al inicio de la conversación).
- fix_doubts: Aborda dudas y preocupaciones sobre el producto o precio.
- add_details: Proporciona más información y detalles sobre el producto.
- add_scarcity: Genera urgencia o escasez para impulsar el cierre.
- search_offers: Presenta promociones o descuentos disponibles.
- close_sale: Cierra la venta siguiendo los próximos pasos definidos (usar cuando el cliente está listo).
- default_tool: Respuesta por defecto si no se detecta una necesidad específica.

### INSTRUCCIONES ###
1. Analiza los fragmentos y sentimientos del cliente.
2. Toma en cuenta la etapa del proceso y el contexto del cliente y producto.
3. Si es el primer mensaje o saludo, usa greet_user.
4. Si el cliente está listo para comprar o en etapa de cierre, usa close_sale.
5. Devuelve SOLO el nombre de la herramienta más adecuada.
6. No agregues explicaciones ni ningún texto adicional."""

        # DYNAMIC content (changes per request)
        user_message = f"""### INFORMACIÓN ACTUAL ###
- Etapa del proceso: {stage}
- Contexto del cliente: {client_context}
- Contexto del producto: {product_context}

### ANÁLISIS DE SENTIMIENTO ###
{fragments_text}

### INSIGHT DE PERSONALIDAD ###
{personality_insight}

Selecciona la herramienta adecuada:"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.01  # Groq minimum
        )

        # Log cache usage
        if hasattr(response, 'usage') and response.usage:
            prompt_tokens = response.usage.prompt_tokens
            cached_tokens = getattr(response.usage.prompt_tokens_details, 'cached_tokens', 0) if hasattr(response.usage, 'prompt_tokens_details') else 0
            cache_hit_rate = (cached_tokens / prompt_tokens * 100) if prompt_tokens > 0 else 0
            logger.info(f"   → Cache: {cached_tokens}/{prompt_tokens} tokens ({cache_hit_rate:.1f}% hit)")

        tool_name = response.choices[0].message.content.strip()
        logger.info(f"   → Herramienta seleccionada por Groq: {tool_name}")

        # Validar que sea una herramienta conocida
        valid_tools = ["greet_user", "fix_doubts", "add_details", "add_scarcity", "search_offers", "close_sale", "default_tool"]
        if tool_name not in valid_tools:
            logger.warning(f"Groq devolvió un nombre de herramienta inválido: {tool_name}. Usando default_tool.")
            tool_name = "default_tool"

        return tool_name

    # ---------------------------
    # Herramientas / técnicas de venta
    # ---------------------------
    def fix_doubts(self, sentiment_analysis, client_context, product_context, stage):
        """
        Aborda dudas o preocupaciones del cliente usando técnica consultiva.
        """
        system_msg = f"""Eres un asistente experto en ventas. El cliente tiene dudas o preocupaciones.

### INFORMACIÓN DEL PRODUCTO ###
{product_context}

### INSTRUCCIONES ###
Genera 3 opciones de respuesta persuasivas.
Devuelve JSON exacto con 3 opciones usando estos IDs: directa, consultiva, empatica."""

        user_msg = f"""### FRAGMENTOS CON PROBLEMAS ###
{[f['text'] for f in sentiment_analysis.get('sentiments', []) if f['label'] in ('NEG','NEU')]}

Genera las 3 opciones:"""
        return self._call_openai(system_msg, user_msg)

    def greet_user(self, sentiment_analysis, client_context, product_context, stage):
        """
        Saluda al cliente usando su nombre y un mensaje amigable.
        """
        client_name = client_context.get("name", "Cliente")
        system_msg = """Genera 3 opciones de saludo en formato JSON.

### FORMATO REQUERIDO ###
[
  { "id": "directa", "intent": "saludo", "text": "..." },
  { "id": "consultiva", "intent": "saludo", "text": "..." },
  { "id": "empatica", "intent": "saludo", "text": "..." }
]

### INSTRUCCIONES ###
- directa: saludo profesional y breve
- consultiva: saludo interactivo preguntando cómo se encuentra
- empatica: saludo cálido y cercano
Devuelve JSON EXACTO. No agregues texto adicional fuera del JSON."""

        user_msg = f"""Cliente: {client_name}

Genera los saludos:"""
        return self._call_openai(system_msg, user_msg)

    def close_sale(self, sentiment_analysis, client_context, product_context, stage):
        """
        Genera 3 opciones de cierre basadas en los próximos pasos definidos en close_context,
        manteniendo un tono conversacional y persuasivo.
        """
        close_context = get_close_context()  # Debe devolver los pasos próximos que queremos sugerir
        fragments = [f['text'] for f in sentiment_analysis.get('sentiments', [])]

        system_msg = f"""El cliente está interesado y en etapa de cierre.

### PRÓXIMOS PASOS (CLOSE CONTEXT) ###
{close_context}

### INFORMACIÓN DEL PRODUCTO ###
{product_context}

### INSTRUCCIONES ###
1. Mantén un estilo conversacional y cercano.
2. Persuade al cliente a seguir los próximos pasos definidos arriba.
3. Devuelve exactamente 3 opciones en formato JSON con IDs:
   - directa: cierre contundente
   - consultiva: cierre preguntando si quiere avanzar
   - empatica: cierre mostrando comprensión y seguridad
4. No inventes pasos que no estén en close_context."""

        user_msg = f"""### CONTEXTO DEL CLIENTE ###
{client_context}

### FRAGMENTOS DETECTADOS ###
{fragments}

Genera las 3 opciones de cierre:"""
        return self._call_openai(system_msg, user_msg)

    def add_details(self, sentiment_analysis, client_context, product_context, stage):
        """
        Añade detalles adicionales del producto para convencer al cliente.
        """
        system_msg = f"""El cliente solicita más detalles sobre el producto.

### INFORMACIÓN DEL PRODUCTO ###
{product_context}

### INSTRUCCIONES ###
Genera 3 opciones persuasivas.
Devuelve JSON exacto con 3 opciones: directa, consultiva y empatica."""

        user_msg = "Genera las opciones con detalles del producto:"
        return self._call_openai(system_msg, user_msg)

    def add_scarcity(self, sentiment_analysis, client_context, product_context, stage):
        """
        Genera sentido de urgencia / escasez para impulsar el cierre.
        """
        system_msg = f"""El cliente está en etapa de cierre. Usa técnicas de escasez y urgencia.

### INFORMACIÓN DEL PRODUCTO ###
{product_context}

### INSTRUCCIONES ###
Genera 3 opciones persuasivas con urgencia/escasez.
Devuelve JSON exacto con 3 opciones: directa, consultiva y empatica."""

        user_msg = "Genera las opciones con técnicas de escasez:"
        return self._call_openai(system_msg, user_msg)


    def search_offers(self, sentiment_analysis, client_context, product_context, stage):
        """
        Muestra ofertas disponibles para convencer al cliente.
        """
        system_msg = f"""El cliente menciona descuentos o promociones.

### INFORMACIÓN DEL PRODUCTO ###
{product_context}

### INSTRUCCIONES ###
Genera 3 opciones persuasivas basadas en ofertas.
Devuelve JSON exacto con 3 opciones: directa, consultiva y empatica."""

        user_msg = "Genera las opciones con ofertas disponibles:"
        return self._call_openai(system_msg, user_msg)

    def default_tool(self, sentiment_analysis, client_context, product_context, stage):
        """
        Genera respuestas por defecto si no se detecta ninguna necesidad específica.
        """
        system_msg = f"""### INFORMACIÓN DEL PRODUCTO ###
{product_context}

### INSTRUCCIONES ###
Genera 3 opciones de respuesta persuasivas.
Devuelve JSON exacto con 3 opciones: directa, consultiva y empatica."""

        user_msg = f"""### CONTEXTO DEL CLIENTE ###
{client_context}

Genera las opciones:"""
        return self._call_openai(system_msg, user_msg)

    # ---------------------------
    # Función común para llamar Groq (optimizado para caching)
    # ---------------------------
    def _call_openai(self, system_message: str, user_message: str) -> list:
        """
        Calls Groq API with system/user message split for optimal prompt caching.
        System message contains static content (cached), user message has dynamic content.
        """
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
            logger.debug(f"Cache: {cached_tokens}/{prompt_tokens} tokens ({cache_hit_rate:.1f}% hit)")
        
        result_text = response.choices[0].message.content.strip()
        
        # Log the raw response for debugging
        logger.debug(f"Raw Groq response: {result_text[:200]}...")

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
            
            logger.debug(f"Successfully parsed {len(options)} options from Groq")
            return options
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}")
            logger.warning(f"Response text was: {result_text}")
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            logger.warning(f"Response text was: {result_text}")
        except Exception as e:
            logger.warning(f"Unexpected error parsing Groq response: {e}")
            logger.warning(f"Response text was: {result_text}")
        
        # Fallback options
        logger.warning("Using fallback options due to parsing error")
        return [
            {"id": "directa", "intent": "cierre", "text": "Podemos avanzar con la compra ahora mismo."},
            {"id": "consultiva", "intent": "pregunta", "text": "¿Puedes contarme más sobre tus prioridades?"},
            {"id": "empatica", "intent": "confianza", "text": "Entiendo tus preocupaciones, estoy aquí para ayudarte."}
        ]