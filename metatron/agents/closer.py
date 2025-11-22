"""
closer_agents_es.py
Versión para CPU, español, con logging detallado.
"""

import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from utils.logger import logger
from agents.evaluator import Evaluator

# ---------------------------
# MODELO HF PARA ESPAÑOL
# ---------------------------

try:
    from transformers import pipeline
except Exception:
    pipeline = None
    raise RuntimeError("Debes instalar transformers: pip install transformers torch")


SPANISH_SENTIMENT_MODEL = "pysentimiento/robertuito-sentiment-analysis"
# Documentado en HF como un modelo optimizado para español.


# ---------------------------
# SENTIMENT RESULT
# ---------------------------
@dataclass
class SentimentResult:
    text: str
    label: str
    score: float

    def to_json(self) -> Dict[str, Any]:
        return {"text": self.text, "label": self.label, "score": self.score}


# ---------------------------
# SENTIMENT SCORER
# ---------------------------
class SentimentScorer:
    """
    Analiza sentimiento en español usando un modelo ligero para CPU.
    """

    def __init__(self, model_name: Optional[str] = None, device: int = -1):
        logger.info("Cargando modelo de sentimiento en español… (esto puede tardar unos segundos)")

        if pipeline is None:
            raise RuntimeError("transformers no está instalado.")

        self.model_name = model_name or SPANISH_SENTIMENT_MODEL
        self.pipe = pipeline(
            "sentiment-analysis",
            model=self.model_name,
            device=device  # siempre CPU (-1)
        )

        logger.info(f"Modelo cargado: {self.model_name} (CPU)")

    def score(self, text: str) -> SentimentResult:
        logger.info("➡️  Etapa 1: Evaluando sentimiento…")

        out = self.pipe(text)[0]
        label = out["label"]  # POS / NEG / NEU
        score = float(out["score"])

        logger.info(f"   → Sentimiento detectado: {label} ({score:.3f})")

        return SentimentResult(text=text, label=label, score=score)


# ---------------------------
# SPLIT DEL TEXTO POR SCORE
# ---------------------------
def split_text_by_score(text: str, score: float,
                        thresholds: Dict[str, float] = None) -> List[str]:

    logger.info("➡️  Etapa 2: Dividiendo texto según score…")

    if thresholds is None:
        thresholds = {"high": 0.75, "mid": 0.50}

    if score >= thresholds["high"]:
        logger.info("   → Score alto → dividir por puntos.")
        parts = re.split(r'(?<=[.!?])\s+', text.strip())

    elif score >= thresholds["mid"]:
        logger.info("   → Score medio → dividir por puntos y punto y coma.")
        parts = re.split(r'(?<=[.;!?])\s+', text.strip())

    else:
        logger.info("   → Score bajo → dividir por puntos y comas.")
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        parts = []
        for s in sentences:
            parts.extend([p.strip() for p in re.split(r',\s*', s) if p.strip()])

    parts = [p for p in parts if p]
    logger.info(f"   → Partes obtenidas: {parts}")

    return parts


# ---------------------------
# CONTEXTO DE CONVERSACIÓN
# ---------------------------
@dataclass
class ConversationContext:
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    stage: str = "inicio"
    meta: Dict[str, Any] = field(default_factory=dict)


# ---------------------------
# GENERADOR DE OPCIONES
# ---------------------------
class OptionsGenerator:

    def generate(self, fragments: List[str], sentiment: SentimentResult,
                 convo_ctx: ConversationContext) -> List[Dict[str, Any]]:

        logger.info("➡️  Etapa 3: Generando opciones de respuesta…")

        base_positive = sentiment.label.upper() == "POS"

        options = [
            {
                "id": "directa",
                "intent": "cierre" if base_positive else "avanzar",
                "text": self._opt_directa(fragments),
                "confidence_est": min(0.9, sentiment.score + 0.1),
            },
            {
                "id": "consultiva",
                "intent": "pregunta",
                "text": self._opt_consultiva(fragments),
                "confidence_est": 0.6 + 0.3 * sentiment.score,
            },
            {
                "id": "empatica",
                "intent": "confianza",
                "text": self._opt_empatica(fragments),
                "confidence_est": 0.5 + 0.3 * sentiment.score,
            },
        ]

        logger.info("   → Opciones generadas correctamente.")
        return options

    def _first(self, fragments):
        return fragments[0] if fragments else ""

    def _opt_directa(self, fragments):
        return f"Perfecto. Sobre lo que comentas: «{self._first(fragments)}». Si quieres, puedo avanzar con la confirmación ahora mismo."

    def _opt_consultiva(self, fragments):
        return f"Gracias por compartirlo. Cuando dices «{self._first(fragments)}», ¿a qué te refieres específicamente?"

    def _opt_empatica(self, fragments):
        return f"Te entiendo completamente respecto a «{self._first(fragments)}». Estoy aquí para ayudarte paso a paso."


# ---------------------------
# VENDEDOR / CLOSER
# ---------------------------
class Seller:

    def __init__(self, personality="amigable"):
        self.personality = personality

    def greet_and_present(self):
        logger.info("➡️  Etapa 5: Construyendo saludo y presentación…")

        greetings = {
            "profesional": "Hola, soy Mateo de Acme. Un gusto saludarte.",
            "amigable": "¡Hola! Soy Mateo 😊 Encantado de ayudarte.",
            "calmo": "Hola, soy Mateo. Vamos paso a paso.",
            "enérgico": "¡Hola! Soy Mateo, listo para ayudarte a cerrar esto hoy mismo.",
        }
        return greetings.get(self.personality, greetings["profesional"])

    def build_message(self, option, client_profile, product_info, stage):
        logger.info("➡️  Etapa 6: Construyendo mensaje final…")

        greeting = self.greet_and_present()
        body = option["text"]
        cierre = ""

        if option["intent"] == "cierre" or stage == "cierre":
            cierre = f"\n¿Quieres que deje todo confirmado para que tengas tu {product_info.get('name', 'producto')} hoy mismo?"

        final = f"{greeting}\n\n{body}{cierre}".strip()

        logger.info("   → Mensaje final construido.")

        return final


def run_agent_interaction(
    incoming_text: str,
    client_profile: Optional[Dict[str, Any]] = None,
    product_info: Optional[Dict[str, Any]] = None,
    *,
    stage: str = "inicio",
    personality: str = "amigable",
    thresholds: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Ejecuta el flujo completo del agente y devuelve el mensaje generado y metadatos.
    """

    client_profile = client_profile or {}
    product_info = product_info or {}

    convo_ctx = ConversationContext(stage=stage)

    scorer = SentimentScorer()
    sentiment = scorer.score(incoming_text)

    fragments = split_text_by_score(incoming_text, sentiment.score, thresholds)

    og = OptionsGenerator()
    options = og.generate(fragments, sentiment, convo_ctx)

    evaluator = Evaluator()
    evaluation = evaluator.evaluate(
        client_profile,
        product_info,
        convo_ctx.stage,
        options
    )

    seller = Seller(personality=personality)
    final_msg = seller.build_message(
        evaluation["best"],
        client_profile,
        product_info,
        convo_ctx.stage
    )

    return {
        "input_text": incoming_text,
        "sentiment": sentiment.to_json(),
        "fragments": fragments,
        "evaluation": evaluation,
        "message": final_msg,
    }


# ---------------------------
# EJEMPLO DE FLUJO COMPLETO
# ---------------------------
def demo_flow():
    logger.info("🚀 INICIANDO DEMO COMPLETA DEL AGENTE CLOSER\n")

    incoming_text = (
        "Hola Mateo, estuve revisando la propuesta y la verdad me encanta. "
        "Solo me preocupa un poco el tiempo de implementación, pero sí quiero avanzar."
    )

    client_profile = {
        "temperament": "decisive",
        "name": "Carlos"
    }

    product_info = {
        "name": "Suite Pro",
        "price": "1200 USD"
    }

    result = run_agent_interaction(
        incoming_text,
        client_profile=client_profile,
        product_info=product_info,
        stage="cierre",
        personality="amigable",
    )

    print("\n📩 MENSAJE FINAL AL CLIENTE:\n")
    print(result["message"])


if __name__ == "__main__":
    demo_flow()
