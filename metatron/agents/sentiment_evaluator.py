"""
sentiment_analyst.py
Segmenta el texto del cliente, analiza sentimiento y genera insights de personalidad.
"""

import json
from openai import OpenAI
from utils.logger import logger
from transformers import pipeline

SPANISH_SENTIMENT_MODEL = "pysentimiento/robertuito-sentiment-analysis"

class SentimentAnalyst:
    """
    Analiza sentimiento por frase y extrae insights de personalidad.
    """

    def __init__(self, openai_api_key: str, device: int = -1, model_name: str = None):
        self.openai = OpenAI(api_key=openai_api_key)
        self.model_name = model_name or SPANISH_SENTIMENT_MODEL
        self.pipe = pipeline("sentiment-analysis", model=self.model_name, device=device)
        logger.info(f"Modelo HF cargado: {self.model_name} (CPU)")

    def segment_text(self, text: str) -> list:
        """
        Usa OpenAI para dividir el texto en ideas o frases.
        """
        logger.info("➡️ Segmentando texto con OpenAI…")
        prompt = f"""
Segmenta el siguiente texto en frases o ideas separadas:
"{text}"

Devuelve un JSON con una lista de frases:
{{"fragments": ["frase1", "frase2", ...]}}
"""
        response = self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        result_text = response.choices[0].message.content.strip()
        try:
            data = json.loads(result_text)
            fragments = data.get("fragments", [])
        except Exception:
            logger.warning("No se pudo parsear JSON de OpenAI. Se usa split por puntos y comas como fallback.")
            import re
            fragments = [f.strip() for f in re.split(r'[.;!?]\s*', text) if f.strip()]

        logger.info(f"   → Fragments obtenidos: {fragments}")
        return fragments

    def analyze_sentiments(self, fragments: list) -> list:
        """
        Analiza sentimiento de cada fragmento usando HF.
        """
        logger.info("➡️ Analizando sentimiento de cada fragmento…")
        results = []
        for frag in fragments:
            out = self.pipe(frag)[0]
            results.append({
                "text": frag,
                "label": out["label"],
                "score": float(out["score"])
            })
            logger.info(f"   → '{frag}' -> {out['label']} ({out['score']:.3f})")
        return results

    def generate_personality_insights(self, fragments: list, sentiments: list) -> str:
        """
        Genera un breve resumen de la personalidad del cliente basado en sus frases y sentimiento.
        """
        logger.info("➡️ Generando insights de personalidad con OpenAI…")
        prompt = f"""
Analiza la siguiente lista de frases de un cliente y los sentimientos asociados:
Frases: {fragments}
Sentimientos: {sentiments}

Resume en 2-3 líneas cómo se percibe la personalidad del cliente (estilo de comunicación, nivel de confianza, posibles preocupaciones).
Devuelve solo texto.
"""
        response = self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        insight = response.choices[0].message.content.strip()
        logger.info(f"   → Insight generado: {insight}")
        return insight

    def analyze(self, text: str) -> dict:
        fragments = self.segment_text(text)
        sentiments = self.analyze_sentiments(fragments)
        insight = self.generate_personality_insights(fragments, sentiments)
        return {
            "text": text,
            "fragments": fragments,
            "sentiments": sentiments,
            "personality_insight": insight
        }