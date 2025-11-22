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


@dataclass
class GlobalConversationContext:
    """
    Mantiene el estado global de la conversación a través de múltiples interacciones.
    """
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    stage: str = "inicio"
    client_profile: Dict[str, Any] = field(default_factory=dict)
    product_info: Dict[str, Any] = field(default_factory=dict)
    sentiment_history: List[Dict[str, Any]] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, sentiment_data: Optional[Dict] = None):
        """Agrega un mensaje al historial de conversación."""
        message = {"role": role, "content": content}
        if sentiment_data:
            message["sentiment"] = sentiment_data
        self.conversation_history.append(message)
        
        if sentiment_data:
            self.sentiment_history.append(sentiment_data)

    def update_stage(self, new_stage: str):
        """Actualiza la etapa de la conversación."""
        logger.info(f"Actualizando etapa: {self.stage} → {new_stage}")
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


class Closer:
    """
    Orquestador principal que coordina todos los agentes y mantiene el contexto global.
    """

    def __init__(self, load_context_from_files: bool = True):
        """
        Inicializa el Closer con todos los agentes necesarios.
        Usa la configuración global de settings para obtener la API key.
        
        Args:
            load_context_from_files: Si True, carga el contexto desde los archivos de configuración
        """
        # Validar que existe la API key de Groq
        if not settings.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY no está configurada. "
                "Por favor configura la variable de entorno GROQ_API_KEY en tu archivo .env"
            )
        
        # Inicializar agentes con la API key de Groq desde settings
        self.sentiment_analyst = SentimentAnalyst(openai_api_key=settings.groq_api_key)
        self.response_generator = ResponseGenerator(openai_api_key=settings.groq_api_key)
        self.evaluator = Evaluator(openai_api_key=settings.groq_api_key)
        self.personality_adapter = PersonalityAdapter(openai_api_key=settings.groq_api_key)
        self.context = GlobalConversationContext()
        
        # Cargar contexto desde archivos si está habilitado
        if load_context_from_files:
            self._load_context_from_files()
        
        logger.info("✅ Closer inicializado con todos los agentes")

    def _load_context_from_files(self):
        """Carga el contexto inicial desde los archivos de configuración."""
        try:
            # Cargar información del lead/cliente
            lead_context = get_lead_context()
            logger.info(f"📄 Contexto del lead cargado: {lead_context[:100]}...")
            self.context.client_profile["description"] = lead_context
            
            # Cargar información del producto
            product_context = get_product_context()
            logger.info(f"📄 Contexto del producto cargado: {product_context[:100]}...")
            self.context.product_info["description"] = product_context
            
            # Cargar perfil del vendedor (para referencia)
            salesman_context = get_salesman_context()
            logger.info(f"📄 Contexto del vendedor cargado: {salesman_context[:100]}...")
            self.context.meta["salesman_profile"] = salesman_context
            
            logger.info("✅ Contexto cargado exitosamente desde archivos")
        except Exception as e:
            logger.warning(f"⚠️  No se pudo cargar contexto desde archivos: {e}")

    def process_message(
        self,
        incoming_text: str,
        client_profile: Optional[Dict[str, Any]] = None,
        product_info: Optional[Dict[str, Any]] = None,
        stage: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Procesa un mensaje del cliente y genera una respuesta completa.
        
        Args:
            incoming_text: Texto del cliente
            client_profile: Información del cliente (opcional, usa el del contexto si no se provee)
            product_info: Información del producto (opcional, usa el del contexto si no se provee)
            stage: Etapa actual (opcional, usa la del contexto si no se provee)
            
        Returns:
            Diccionario con la respuesta y metadatos del proceso
        """
        logger.info("=" * 80)
        logger.info("🚀 INICIANDO PROCESAMIENTO DE MENSAJE")
        logger.info("=" * 80)

        # Actualizar contexto global
        if client_profile:
            self.context.client_profile.update(client_profile)
        if product_info:
            self.context.product_info.update(product_info)
        if stage:
            self.context.update_stage(stage)

        # Paso 1: Análisis de sentimiento
        logger.info("\n📊 Paso 1: Análisis de sentimiento")
        sentiment_analysis = self.sentiment_analyst.analyze(incoming_text)
        
        # Agregar mensaje al historial
        self.context.add_message("cliente", incoming_text, sentiment_analysis)

        # Paso 2: Generar opciones de respuesta
        logger.info("\n💡 Paso 2: Generación de opciones")
        options = self.response_generator.generate_response(
            sentiment_analysis=sentiment_analysis,
            client_context=self.context.client_profile,
            product_context=self.context.product_info,
            stage=self.context.stage
        )

        # Paso 3: Evaluar y seleccionar mejor opción
        logger.info("\n⚖️  Paso 3: Evaluación de opciones")
        evaluation = self.evaluator.evaluate(
            conversation_history=self.context.conversation_history,
            options=options
        )

        # Paso 4: Adaptar a personalidad
        logger.info("\n🎭 Paso 4: Adaptación de personalidad")
        adapted_response = self.personality_adapter.adapt(evaluation["response"])

        # Agregar respuesta al historial
        self.context.add_message("agente", adapted_response)

        # Preparar resultado
        result = {
            "input_text": incoming_text,
            "sentiment_analysis": sentiment_analysis,
            "options_generated": options,
            "evaluation": evaluation,
            "original_response": evaluation["response"],
            "adapted_response": adapted_response,
            "context": self.context.to_dict()
        }

        logger.info("\n" + "=" * 80)
        logger.info("✅ PROCESAMIENTO COMPLETADO")
        logger.info("=" * 80)

        return result

    def get_context(self) -> GlobalConversationContext:
        """Retorna el contexto global actual."""
        return self.context

    def reset_context(self):
        """Reinicia el contexto global."""
        logger.info("🔄 Reiniciando contexto global")
        self.context = GlobalConversationContext()


def run_agent_interaction(
    incoming_text: str,
    client_profile: Optional[Dict[str, Any]] = None,
    product_info: Optional[Dict[str, Any]] = None,
    *,
    stage: str = "inicio",
    personality: str = "amigable",
    thresholds: Optional[Dict[str, float]] = None,
    openai_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Función de compatibilidad con la API anterior.
    Ahora usa la nueva clase Closer internamente con settings.
    
    NOTA: Esta función crea una nueva instancia de Closer cada vez,
    por lo que no mantiene contexto entre llamadas. Para mantener contexto,
    usa directamente la clase Closer.
    
    El parámetro openai_api_key se mantiene por compatibilidad pero ya no se usa.
    La API key de Groq se obtiene de settings (config.py).
    """
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
        "fragments": result["sentiment_analysis"].get("fragments", []),
        "evaluation": result["evaluation"],
        "message": result["adapted_response"],
        "context": result["context"]
    }

