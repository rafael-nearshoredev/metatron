"""
closer.py  
Orquestador principal que coordina el flujo completo de análisis y respuesta.
Mantiene el contexto global de la conversación.
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from metatron.utils.logger import logger
from metatron.utils.file_reader import get_salesman_context, get_lead_context, get_product_context
from metatron.config import settings
from metatron.agents.sentiment_evaluator import SentimentAnalyst
from metatron.agents.response_generator import ResponseGenerator
from metatron.agents.evaluator import Evaluator
from metatron.agents.personality_adapter import PersonalityAdapter


# =====================================================================
# 1. CONTEXTO GLOBAL
# =====================================================================

@dataclass
class GlobalConversationContext:
    """
    Mantiene el estado global de la conversación a través de múltiples interacciones.
    """
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    stage: str = "intro"
    client_profile: Dict[str, Any] = field(default_factory=dict)
    product_info: Dict[str, Any] = field(default_factory=dict)
    sentiment_history: List[Dict[str, Any]] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, sentiment_data: Optional[Dict] = None):
        """Agrega un mensaje al historial de conversación."""
        logger.info(f"📝 Guardando mensaje en historial: {role}")
        message = {"role": role, "content": content}

        if sentiment_data:
            message["sentiment"] = sentiment_data
            self.sentiment_history.append(sentiment_data)

        self.conversation_history.append(message)

    def update_stage(self, new_stage: str):
        """Actualiza la etapa de la conversación."""
        logger.info(f"🔄 Cambio de etapa: {self.stage} → {new_stage}")
        self.stage = new_stage

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el contexto a diccionario."""
        return {
            "conversation_history": self.conversation_history,
            "stage": self.stage,
            "client_profile": self.client_profile,
            "product_info": self.product_info,
            "sentiment_history": self.sentiment_history,
            "meta": self.meta
        }


# =====================================================================
# 2. FUNCIÓN PARA EVALUAR TRANSICIONES DE FASE
# =====================================================================

def evaluate_stage_transition(context: GlobalConversationContext, sentiment_data: Dict[str, Any]) -> str:
    """
    Decide si el flujo de la llamada debe avanzar a la siguiente fase:

    intro → pitch → cierre

    Reglas (ajústalas según tu negocio real):
    - INTRO → PITCH: cuando el cliente da señales de interés o hace preguntas
    - PITCH → CIERRE: cuando el cliente expresa intención clara de compra
    """
    current_stage = context.stage
    fragments = [f["text"].lower() for f in sentiment_data.get("sentiments", [])]

    logger.info(f"🔎 Evaluando transición de etapa desde: {current_stage}")
    logger.info(f"🧩 Fragmentos detectados del cliente: {fragments}")

    if current_stage == "intro":
        if any(x in f for f in fragments for x in ["interesa", "cuéntame", "cómo funciona", "me gusta"]):
            return "pitch"

    if current_stage == "pitch":
        if any(x in f for f in fragments for x in ["precio", "cómo pago", "quiero", "compro", "me sirve"]):
            return "cierre"

    # No hay transición
    return current_stage


# =====================================================================
# 3. CLOSER: ORQUESTADOR PRINCIPAL
# =====================================================================

class Closer:
    """
    Orquestador principal que coordina todos los agentes y mantiene el contexto global.
    """

    def __init__(self, load_context_from_files: bool = True):
        """
        Inicializa el Closer con todos los agentes necesarios.
        """
        if not settings.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY no está configurada. "
                "Por favor configura la variable de entorno GROQ_API_KEY en tu archivo .env"
            )

        self.sentiment_analyst = SentimentAnalyst(openai_api_key=settings.groq_api_key)
        self.response_generator = ResponseGenerator(openai_api_key=settings.groq_api_key)
        self.evaluator = Evaluator(openai_api_key=settings.groq_api_key)
        self.personality_adapter = PersonalityAdapter(openai_api_key=settings.groq_api_key)

        self.context = GlobalConversationContext()

        if load_context_from_files:
            self._load_context_from_files()

        logger.info("🚀 Closer inicializado con todos los agentes")

    # -----------------------------------------------------------------

    def _load_context_from_files(self):
        """Carga el contexto inicial desde los archivos de configuración."""
        try:
            lead_context = get_lead_context()
            self.context.client_profile["description"] = lead_context

            product_context = get_product_context()
            self.context.product_info["description"] = product_context

            salesman_context = get_salesman_context()
            self.context.meta["salesman_profile"] = salesman_context

            logger.info("📄 Contexto cargado exitosamente desde archivos")

        except Exception as e:
            logger.warning(f"⚠️ No se pudo cargar contexto desde archivos: {e}")

    # -----------------------------------------------------------------

    def process_message(
        self,
        incoming_text: str,
        client_profile: Optional[Dict[str, Any]] = None,
        product_info: Optional[Dict[str, Any]] = None,
        stage: Optional[str] = None
    ) -> Dict[str, Any]:

        logger.info("=" * 80)
        logger.info("📞 NUEVO MENSAJE DEL CLIENTE")
        logger.info("=" * 80)

        # Actualizar contexto
        if client_profile:
            self.context.client_profile.update(client_profile)
        if product_info:
            self.context.product_info.update(product_info)
        if stage:
            self.context.update_stage(stage)

        # -----------------------------------------------------------------
        # PASO 1: ANALIZAR SENTIMIENTO
        # -----------------------------------------------------------------

        logger.info("📊 Analizando sentimiento...")
        sentiment_analysis = self.sentiment_analyst.analyze(incoming_text)

        self.context.add_message("cliente", incoming_text, sentiment_analysis)

        # -----------------------------------------------------------------
        # PASO 2: EVALUAR SI DEBEMOS PASAR A LA SIGUIENTE FASE
        # -----------------------------------------------------------------

        new_stage = evaluate_stage_transition(self.context, sentiment_analysis)

        if new_stage != self.context.stage:
            logger.info(f"🏆 Transición de etapa detectada → {new_stage}")
            self.context.update_stage(new_stage)

        # -----------------------------------------------------------------
        # PASO 3: GENERAR OPCIONES
        # -----------------------------------------------------------------

        logger.info("💡 Generando opciones...")
        options = self.response_generator.generate_response(
            sentiment_analysis=sentiment_analysis,
            client_context=self.context.client_profile,
            product_context=self.context.product_info,
            stage=self.context.stage,
            conversation_context=self.context,
        )

        # -----------------------------------------------------------------
        # PASO 4: EVALUAR OPCIONES
        # -----------------------------------------------------------------

        logger.info("⚖️ Evaluando opciones...")
        evaluation = self.evaluator.evaluate(
            conversation_history=self.context.conversation_history,
            options=options,
            full_context=self.context.to_dict(),
        )

        # -----------------------------------------------------------------
        # PASO 5: ADAPTAR PERSONALIDAD
        # -----------------------------------------------------------------

        logger.info("🎭 Adaptando personalidad...")
        adapted_response = self.personality_adapter.adapt(evaluation["response"])

        self.context.add_message("agente", adapted_response)

        # -----------------------------------------------------------------
        # RESULTADO FINAL
        # -----------------------------------------------------------------

        logger.info("✅ Procesamiento completado")
        try:
            context_snapshot = json.dumps(self.context.to_dict(), indent=2, ensure_ascii=False)
            logger.info("📚 Contexto completo de la conversación:")
            logger.info(context_snapshot)
        except Exception as e:
            logger.warning(f"⚠️ No se pudo imprimir el contexto completo: {e}")

        return {
            "input_text": incoming_text,
            "sentiment_analysis": sentiment_analysis,
            "stage": self.context.stage,
            "options_generated": options,
            "evaluation": evaluation,
            "original_response": evaluation["response"],
            "adapted_response": adapted_response,
            "context": self.context.to_dict()
        }

    # -----------------------------------------------------------------

    def get_context(self):
        return self.context

    def reset_context(self):
        logger.info("🔄 Reiniciando contexto global…")
        self.context = GlobalConversationContext()


# =====================================================================
# 4. API COMPATIBLE (EN DESUSO)
# =====================================================================

def run_agent_interaction(
    incoming_text: str,
    client_profile: Optional[Dict[str, Any]] = None,
    product_info: Optional[Dict[str, Any]] = None,
    *,
    stage: str = "intro",
) -> Dict[str, Any]:
    closer = Closer()
    result = closer.process_message(
        incoming_text=incoming_text,
        client_profile=client_profile,
        product_info=product_info,
        stage=stage
    )

    return {
        "input_text": result["input_text"],
        "sentiment": result["sentiment_analysis"],
        "evaluation": result["evaluation"],
        "message": result["adapted_response"],
        "stage": result["stage"],
        "context": result["context"]
    }
