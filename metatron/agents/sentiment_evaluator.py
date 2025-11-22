"""
sentiment_analyst.py
Segmenta el texto del cliente, analiza sentimiento y genera insights de personalidad.
"""

import json
from openai import OpenAI
from metatron.utils.logger import logger
from transformers import pipeline

SPANISH_SENTIMENT_MODEL = "pysentimiento/robertuito-sentiment-analysis"

# Groq configuration
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-120b"


class SentimentAnalyst:
    """
    Analiza sentimiento por frase y extrae insights de personalidad.
    """

    def __init__(self, openai_api_key: str, device: int = -1, model_name: str = None):
        self.openai = OpenAI(
            base_url=GROQ_BASE_URL,
            api_key=openai_api_key
        )
        self.model_name = model_name or SPANISH_SENTIMENT_MODEL
        self.pipe = pipeline("sentiment-analysis", model=self.model_name, device=device)
        logger.info(f"Modelo HF cargado: {self.model_name} (CPU)")
        logger.info(f"Groq configurado para segmentación y análisis de personalidad")

    def segment_text(self, text: str) -> list:
        """
        Usa Groq para dividir el texto en ideas o frases.
        Optimized for prompt caching: static instructions in system message.
        """
        logger.info("➡️ Segmentando texto con Groq…")
        
        # STATIC content (will be cached)
        system_message = """Segmenta el texto del cliente en frases o ideas separadas.

### INSTRUCCIONES ###
Devuelve un JSON con una lista de frases:
{"fragments": ["frase1", "frase2", ...]}"""

        # DYNAMIC content (user text)
        user_message = f'''Texto a segmentar:
"{text}"

Segmenta:'''

        response = self.openai.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.01  # Groq doesn't support 0, use minimum value
        )
        
        # Log cache usage
        if hasattr(response, 'usage') and response.usage:
            prompt_tokens = response.usage.prompt_tokens
            cached_tokens = getattr(response.usage.prompt_tokens_details, 'cached_tokens', 0) if hasattr(response.usage, 'prompt_tokens_details') else 0
            cache_hit_rate = (cached_tokens / prompt_tokens * 100) if prompt_tokens > 0 else 0
            logger.info(f"   → Cache: {cached_tokens}/{prompt_tokens} tokens ({cache_hit_rate:.1f}% hit)")
        result_text = response.choices[0].message.content.strip()
        try:
            data = json.loads(result_text)
            fragments = data.get("fragments", [])
        except Exception:
            logger.warning("No se pudo parsear JSON de Groq. Se usa split por puntos y comas como fallback.")
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
        Optimized for prompt caching: static instructions in system message.
        """
        logger.info("➡️ Generando insights de personalidad con Groq…")
        
        # STATIC content (will be cached)
        system_message = """Analiza las frases de un cliente y los sentimientos asociados.

### INSTRUCCIONES ###
Resume en 2-3 líneas cómo se percibe la personalidad del cliente:
- Estilo de comunicación
- Nivel de confianza
- Posibles preocupaciones

Devuelve solo texto, sin formato adicional."""

        # DYNAMIC content (customer data)
        user_message = f"""### FRASES DEL CLIENTE ###
{fragments}

### SENTIMIENTOS DETECTADOS ###
{sentiments}

Genera el insight de personalidad:"""

        response = self.openai.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.5
        )
        
        # Log cache usage
        if hasattr(response, 'usage') and response.usage:
            prompt_tokens = response.usage.prompt_tokens
            cached_tokens = getattr(response.usage.prompt_tokens_details, 'cached_tokens', 0) if hasattr(response.usage, 'prompt_tokens_details') else 0
            cache_hit_rate = (cached_tokens / prompt_tokens * 100) if prompt_tokens > 0 else 0
            logger.info(f"   → Cache: {cached_tokens}/{prompt_tokens} tokens ({cache_hit_rate:.1f}% hit)")
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