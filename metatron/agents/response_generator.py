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
SALES_GUIDELINES = (
    "Eres un vendedor consultivo: responde siempre a la pregunta del cliente con claridad, "
    "pero guía la conversación para que avance hacia la compra del producto. "
    "No ignores inquietudes; resuélvelas y conecta la respuesta con cómo la oferta le ayuda."
)


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

    def generate_response(
        self,
        sentiment_analysis: dict,
        client_context: dict,
        product_context: dict,
        stage: str,
        conversation_context=None,
    ) -> list:
        """
        Selecciona la herramienta adecuada según el contexto y genera 3 opciones.
        """
        logger.info("➡️  Etapa 3: Analizando contexto y seleccionando herramienta…")
        conversation_history = self._extract_conversation_history(conversation_context)

        tool_to_use = self.select_tool(
            sentiment_analysis=sentiment_analysis,
            client_context=client_context,
            product_context=product_context,
            stage=stage,
            conversation_history=conversation_history,
        )
        logger.info(f"   → Herramienta seleccionada: {tool_to_use}")

        # Llama a la herramienta correspondiente
        options = getattr(self, tool_to_use)(
            sentiment_analysis,
            client_context,
            product_context,
            stage,
            conversation_history=conversation_history,
        )

        logger.info("   → Opciones generadas por la herramienta:")
        for o in options:
            logger.info(f"      * {o['id']} ({o['intent']}): {o['text']}")

        return options

    # ---------------------------
    # Selector de herramientas
    # ---------------------------
    def select_tool(
        self,
        sentiment_analysis,
        client_context,
        product_context,
        stage,
        conversation_history=None,
    ) -> str:
        """
        Selecciona la herramienta adecuada usando Groq+reglas simples.
        Se usan:
        - Sentiment fragments
        - Historial de conversación
        - Etapa del funnel (intro, pitch, cierre)
        - Lista oficial de tools
        
        REGLAS DURAS:
        - Si el usuario saluda → greet_user SIEMPRE.
        """

        logger.info("➡️ Seleccionando herramienta usando reglas + Groq…")

        # ---------------------------------------------------------
        # 1. Detectar saludo explícito → REGLA DURA
        # ---------------------------------------------------------
        saludo_keywords = ["hola", "buenas", "saludo", "qué tal", "buen día", "hey", "holi"]
        conversation_history = conversation_history or []
        full_conversation_text = " ".join(
            (msg.get("content") or "").lower()
            for msg in conversation_history
            if msg.get("role") == "cliente"
        )

        if any(kw in full_conversation_text for kw in saludo_keywords):
            logger.info("   → Regla dura: saludo detectado → greet_user")
            return "greet_user"

        # ---------------------------------------------------------
        # 2. Preparar inputs para Groq (razonamiento suave)
        # ---------------------------------------------------------
        fragments_text = "\n".join([
            f"- {f['text']} ({f['label']}, {f['score']:.2f})"
            for f in sentiment_analysis.get("sentiments", [])
        ])

        system_message = """
Eres un asistente experto en ventas por teléfono.

Tu tarea es elegir la herramienta correcta basándote solo en:
- contexto del cliente
- contexto del producto
- etapa del funnel: intro, pitch, cierre
- análisis de sentimiento
- historial de conversación reciente

### HERRAMIENTAS DISPONIBLES ###
1. greet_user        → Si parece inicio, presentación o saludo.
2. seduce_lead       → Conectar producto ↔ cliente (beneficios alineados al perfil).
3. fix_doubts        → Resolver dudas, miedos, confusiones.
4. add_details       → Ampliar detalles solicitados.
5. add_scarcity      → Generar urgencia si está cerca del cierre.
6. search_offers     → Buscar ofertas cuando lo piden.
7. close_sale        → Cuando el cliente muestra disposición clara a comprar.
8. default_tool      → Si nada aplica.

### INSTRUCCIONES ###
- Piensa como un closer profesional.
- Analiza señales del cliente, dudas, intención, urgencia, interés.
- Devuelve SOLO el nombre exacto de la herramienta.
"""

        user_message = f"""
### INFORMACIÓN ###
Etapa actual: {stage}

### CONTEXTO DEL CLIENTE ###
{client_context}

### CONTEXTO DEL PRODUCTO ###
{product_context}

### SENTIMIENTO ###
{fragments_text}

### HISTORIAL DE CONVERSACIÓN ###
{conversation_history[-6:]}

Selecciona la herramienta correcta según este contexto:
"""

        # ---------------------------------------------------------
        # 3. Llamada al modelo Groq
        # ---------------------------------------------------------
        system_message = f"{SALES_GUIDELINES}\n\n{system_message}"

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.01
        )

        tool_name = response.choices[0].message.content.strip()
        logger.info(f"   → Groq sugiere: {tool_name}")

        # ---------------------------------------------------------
        # 4. Validación de herramienta
        # ---------------------------------------------------------
        valid_tools = {
            "greet_user",
            "seduce_lead",
            "fix_doubts",
            "add_details",
            "add_scarcity",
            "search_offers",
            "close_sale",
            "default_tool"
        }

        if tool_name not in valid_tools:
            logger.warning(f"⚠️ Herramienta inválida detectada: {tool_name}. Se usa default_tool.")
            tool_name = "default_tool"

        logger.info(f"✔️ Herramienta final seleccionada: {tool_name}")
        return tool_name


    # ------------------------------------------------------
    # NUEVA HERRAMIENTA: seduce_lead
    # ------------------------------------------------------
    def seduce_lead(self, sentiment_analysis, client_context, product_context, stage, conversation_history=None):
        """
        Conecta el producto con el perfil del cliente mostrando beneficios,
        ventajas claras y por qué es ideal para él.
        Debe ser persuasivo pero conversacional.
        """
        history_snippet = self._format_recent_messages(conversation_history)

        system_msg = f"""
Eres un vendedor persuasivo. Tu objetivo es "seducir" comercialmente al cliente,
explicando por qué este producto es perfecto para él.

### DEFINICIÓN DE SEDUCIR AQUÍ ###
- No es sexual.
- Es resaltar beneficios.
- Conectar el producto con el cliente.
- Mostrar por qué le conviene.
- Ser cálido, claro y convincente.

### INSTRUCCIONES ###
Genera exactamente 3 opciones en JSON:
- directa: vende el beneficio principal directo
- consultiva: explora su necesidad y cómo encaja
- empatica: resalta comprensión del cliente + beneficio clave

NO repitas beneficios si ya se dijeron previamente.
NO inventes beneficios que no están en el contexto.
Mantén coherencia con el historial reciente de la conversación.

### CONTEXTO DEL PRODUCTO ###
{product_context}

### CONTEXTO DEL CLIENTE ###
{client_context}

### CONTEXTO DE CONVERSACIÓN ###
{history_snippet}

Devuelve solo JSON.
"""

        fragments = [f['text'] for f in sentiment_analysis.get("sentiments", [])]
        user_msg = f"""### Fragmentos previos ###
{fragments}

Genera las 3 opciones:"""

        return self._call_openai(system_msg, user_msg)

    # ---------------------------
    # Herramientas / técnicas de venta
    # ---------------------------
    def fix_doubts(self, sentiment_analysis, client_context, product_context, stage, conversation_history=None):
        """
        Aborda dudas o preocupaciones del cliente usando técnica consultiva.
        """
        history_snippet = self._format_recent_messages(conversation_history)
        system_msg = f"""Eres un asistente experto en ventas. El cliente tiene dudas o preocupaciones y ya llevas una conversación previa con él.

### INSTRUCCIONES ###
Genera 3 opciones de respuesta persuasivas. Responde concretamente la pregunta del cliente y menciona como eso le puede generar valor usando el contexto del cliente
Devuelve JSON exacto con 3 opciones usando estos IDs: directa, consultiva, empatica.
Mantén coherencia con las respuestas anteriores y evita repetir ideas textualmente.

### INFORMACIÓN DEL PRODUCTO ###
{product_context}

### CONTEXTO DEL CLIENTE ###
{client_context}

### CONTEXTO DE CONVERSACIÓN ###
{history_snippet}
"""

        user_msg = f"""### FRAGMENTOS CON PROBLEMAS ###
{[f['text'] for f in sentiment_analysis.get('sentiments', []) if f['label'] in ('NEG','NEU')]}

Genera las 3 opciones:"""
        return self._call_openai(system_msg, user_msg)

    def greet_user(self, sentiment_analysis, client_context, product_context, stage, conversation_history=None):
        """
        Saluda al cliente usando su nombre y un mensaje amigable.
        """
        client_name = client_context.get("name", "Cliente")
        history_snippet = self._format_recent_messages(conversation_history)
        system_msg = f"""Genera 3 opciones de saludo en formato JSON teniendo en cuenta lo que ya se dijo.

### FORMATO REQUERIDO ###
[
  {{ "id": "directa", "intent": "saludo", "text": "..." }},
  {{ "id": "consultiva", "intent": "saludo", "text": "..." }},
  {{ "id": "empatica", "intent": "saludo", "text": "..." }}
]

### INSTRUCCIONES ###
- directa: saludo profesional y breve
- consultiva: saludo interactivo preguntando cómo se encuentra
- empatica: saludo cálido y cercano
Devuelve JSON EXACTO. No agregues texto adicional fuera del JSON.
Mantén coherencia con este historial reciente:
{history_snippet}
"""

        user_msg = f"""Cliente: {client_name}

Genera los saludos:"""
        return self._call_openai(system_msg, user_msg)

    def close_sale(self, sentiment_analysis, client_context, product_context, stage, conversation_history=None):
        """
        Genera 3 opciones de cierre basadas en los próximos pasos definidos en close_context,
        manteniendo un tono conversacional y persuasivo.
        """
        close_context = get_close_context()  # Debe devolver los pasos próximos que queremos sugerir
        fragments = [f['text'] for f in sentiment_analysis.get('sentiments', [])]
        history_snippet = self._format_recent_messages(conversation_history)

        system_msg = f"""El cliente está interesado y en etapa de cierre. Necesitas continuar la conversación sin perder el hilo.

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
4. No inventes pasos que no estén en close_context.
5. Mantén coherencia con el historial reciente:
{history_snippet}
"""

        user_msg = f"""### CONTEXTO DEL CLIENTE ###
{client_context}

### FRAGMENTOS DETECTADOS ###
{fragments}

Genera las 3 opciones de cierre:"""
        return self._call_openai(system_msg, user_msg)

    def add_details(self, sentiment_analysis, client_context, product_context, stage, conversation_history=None):
        """
        Añade detalles adicionales del producto para convencer al cliente.
        """
        history_snippet = self._format_recent_messages(conversation_history)
        system_msg = f"""El cliente solicita más detalles sobre el producto. Responde dando continuidad a la conversación.

### INFORMACIÓN DEL PRODUCTO ###
{product_context}

### INSTRUCCIONES ###
Genera 3 opciones persuasivas.
Devuelve JSON exacto con 3 opciones: directa, consultiva y empatica.
Usa este historial reciente para mantener coherencia:
{history_snippet}
"""

        user_msg = "Genera las opciones con detalles del producto:"
        return self._call_openai(system_msg, user_msg)

    def add_scarcity(self, sentiment_analysis, client_context, product_context, stage, conversation_history=None):
        """
        Genera sentido de urgencia / escasez para impulsar el cierre.
        """
        history_snippet = self._format_recent_messages(conversation_history)
        system_msg = f"""El cliente está en etapa de cierre. Usa técnicas de escasez y urgencia sin romper el hilo de la conversación.

### INFORMACIÓN DEL PRODUCTO ###
{product_context}

### INSTRUCCIONES ###
Genera 3 opciones persuasivas con urgencia/escasez.
Devuelve JSON exacto con 3 opciones: directa, consultiva y empatica.
Historial reciente:
{history_snippet}
"""

        user_msg = "Genera las opciones con técnicas de escasez:"
        return self._call_openai(system_msg, user_msg)


    def search_offers(self, sentiment_analysis, client_context, product_context, stage, conversation_history=None):
        """
        Muestra ofertas disponibles para convencer al cliente.
        """
        history_snippet = self._format_recent_messages(conversation_history)
        system_msg = f"""El cliente menciona descuentos o promociones y espera continuidad en la conversación.

### INFORMACIÓN DEL PRODUCTO ###
{product_context}

### INSTRUCCIONES ###
Genera 3 opciones persuasivas basadas en ofertas.
Devuelve JSON exacto con 3 opciones: directa, consultiva y empatica.
Historial reciente:
{history_snippet}
"""

        user_msg = "Genera las opciones con ofertas disponibles:"
        return self._call_openai(system_msg, user_msg)

    def default_tool(self, sentiment_analysis, client_context, product_context, stage, conversation_history=None):
        """
        Genera respuestas por defecto si no se detecta ninguna necesidad específica.
        """
        history_snippet = self._format_recent_messages(conversation_history)
        system_msg = f"""### INFORMACIÓN DEL PRODUCTO ###
{product_context}

### INSTRUCCIONES ###
Genera 3 opciones de respuesta persuasivas.
Devuelve JSON exacto con 3 opciones: directa, consultiva y empatica.
Usa el historial reciente para mantener coherencia:
{history_snippet}
"""

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
            options = self._normalize_options(options)

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

    def _format_recent_messages(self, conversation_history, limit=6):
        """
        Devuelve los últimos mensajes de la conversación en formato legible.
        """
        if not conversation_history:
            return "No hay mensajes previos."
        recent = conversation_history[-limit:]
        formatted = []
        for msg in recent:
            role = msg.get("role", "desconocido")
            content = msg.get("content", "")
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)

    def _normalize_options(self, options):
        """
        Ensure Groq responses are always a list of option dicts.
        """
        if isinstance(options, dict):
            intent_map = {
                "directa": "cierre",
                "consultiva": "pregunta",
                "empatica": "confianza",
            }
            normalized = []
            ordered_keys = ["directa", "consultiva", "empatica"]
            ordered_keys += [k for k in options.keys() if k not in ordered_keys]
            for option_id in ordered_keys:
                text = options.get(option_id)
                if text is None:
                    continue
                normalized.append({
                    "id": option_id,
                    "intent": intent_map.get(option_id, "respuesta"),
                    "text": text,
                })
            options = normalized
        return options

    def _extract_conversation_history(self, conversation_context):
        """
        Devuelve una lista homogénea de mensajes desde el contexto recibido.
        """
        if conversation_context is None:
            return []
        if hasattr(conversation_context, "conversation_history"):
            return conversation_context.conversation_history
        if isinstance(conversation_context, dict):
            history = conversation_context.get("conversation_history", [])
            return history if isinstance(history, list) else []
        return []
