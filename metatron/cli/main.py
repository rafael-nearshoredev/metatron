import json
from typing import Any, Dict, Optional

import typer

try:  # Support both installed package and local execution via `python -m cli`
    from metatron.agents.closer import run_agent_interaction
    from metatron.agents.personality_adapter import PersonalityAdapter
    from metatron.agents.evaluator import Evaluator
    from metatron.agents.response_generator import ResponseGenerator
    from metatron.agents.sentiment_evaluator import SentimentAnalyst
except ModuleNotFoundError:  # pragma: no cover - dev fallback
    from agents.closer import run_agent_interaction  # type: ignore
    from agents.personality_adapter import PersonalityAdapter  # type: ignore
    from agents.evaluator import Evaluator  # type: ignore
    from agents.response_generator import ResponseGenerator  # type: ignore
    from agents.sentiment_evaluator import SentimentAnalyst  # type: ignore

app = typer.Typer()


def _parse_json_option(value: Optional[str], option_name: str) -> Dict[str, Any]:
    if value is None:
        return {}

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON for {option_name}: {exc}") from exc

    if not isinstance(parsed, dict):
        raise typer.BadParameter(f"{option_name} must be a JSON object.")

    return parsed


@app.command()
def ping():
    print("pong")


@app.command(name="adapt", help="Reescribe un texto al estilo definido en el perfil del vendedor.")
def adapt_text(
    text: str = typer.Argument(..., help="Texto original a adaptar."),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        envvar="OPENAI_API_KEY",
        help="Clave de OpenAI (por defecto toma la variable OPENAI_API_KEY).",
    ),
):
    if not api_key:
        typer.echo("OPENAI_API_KEY no está configurada. Usa --api-key o exporta la variable de entorno.", err=True)
        raise typer.Exit(code=1)

    adapter = PersonalityAdapter(openai_api_key=api_key)
    adapted_text = adapter.adapt(text)
    typer.echo(adapted_text)


@app.command(name="sentiment", help="Analiza el sentimiento y personalidad del cliente.")
def analyze_sentiment(
    text: str = typer.Argument(..., help="Texto del cliente a analizar."),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        envvar="OPENAI_API_KEY",
        help="Clave de OpenAI (por defecto toma la variable OPENAI_API_KEY).",
    ),
):
    if not api_key:
        typer.echo("OPENAI_API_KEY no está configurada. Usa --api-key o exporta la variable de entorno.", err=True)
        raise typer.Exit(code=1)

    analyst = SentimentAnalyst(openai_api_key=api_key)
    result = analyst.analyze(text)

    typer.echo("\n📊 ANÁLISIS DE SENTIMIENTO Y PERSONALIDAD\n")
    typer.echo(f"Texto original: {result['text']}\n")
    
    typer.echo("📝 Fragmentos identificados:")
    for i, frag in enumerate(result['fragments'], 1):
        typer.echo(f"  {i}. {frag}")
    
    typer.echo("\n💭 Sentimientos por fragmento:")
    for sent in result['sentiments']:
        typer.echo(f"  • '{sent['text']}'")
        typer.echo(f"    → {sent['label']} (confianza: {sent['score']:.2%})")
    
    typer.echo(f"\n🎯 Insight de personalidad:")
    typer.echo(f"  {result['personality_insight']}")
    
    typer.echo("\n📋 JSON completo:")
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


@app.command(name="evaluate", help="Evalúa tres opciones y devuelve la mejor según el Evaluator.")
def evaluate_options(
    option_a: str = typer.Option(..., "--option-a", "-a", help="Texto de la opción A."),
    option_b: str = typer.Option(..., "--option-b", "-b", help="Texto de la opción B."),
    option_c: str = typer.Option(..., "--option-c", "-c", help="Texto de la opción C."),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        envvar="OPENAI_API_KEY",
        help="Clave de OpenAI (por defecto toma la variable OPENAI_API_KEY).",
    ),
):
    if not api_key:
        typer.echo("OPENAI_API_KEY no está configurada. Usa --api-key o exporta la variable de entorno.", err=True)
        raise typer.Exit(code=1)

    # Historial fijo para pruebas rápidas en CLI
    conversation_history = [
        {"role": "cliente", "content": "Hola, vi su programa y quiero saber cómo me ayuda a lanzar mi startup."},
        {"role": "agente", "content": "Hola Rafael, te cuento brevemente las etapas y vemos si encaja contigo."},
        {"role": "cliente", "content": "Perfecto, me interesa avanzar pero quiero claridad en el acompañamiento."},
    ]

    options = [
        {"id": "option_a", "intent": "consulta", "text": option_a},
        {"id": "option_b", "intent": "cierre", "text": option_b},
        {"id": "option_c", "intent": "empatía", "text": option_c},
    ]

    evaluator = Evaluator(openai_api_key=api_key)
    result = evaluator.evaluate(conversation_history=conversation_history, options=options)
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


@app.command(name="generate", help="Genera 3 opciones de respuesta basadas en el contexto del cliente.")
def generate_responses(
    text: str = typer.Argument(..., help="Texto del cliente."),
    sentiment: float = typer.Option(0.5, "--sentiment", "-s", help="Score de sentimiento (0.0 a 1.0)."),
    stage: str = typer.Option("inicio", "--stage", help="Etapa de venta (inicio, negociacion, cierre)."),
    client_profile: Optional[str] = typer.Option(
        None,
        "--client-profile",
        help="JSON con datos del cliente (ej. '{\"name\": \"Carlos\", \"temperament\": \"cautious\"}').",
    ),
    product_info: Optional[str] = typer.Option(
        None,
        "--product-info",
        help="JSON con datos del producto (ej. '{\"name\": \"Suite Pro\", \"price\": \"1200 USD\"}').",
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        envvar="OPENAI_API_KEY",
        help="Clave de OpenAI (por defecto toma la variable OPENAI_API_KEY).",
    ),
):
    if not api_key:
        typer.echo("OPENAI_API_KEY no está configurada. Usa --api-key o exporta la variable de entorno.", err=True)
        raise typer.Exit(code=1)

    # Parse JSON options
    client_data = _parse_json_option(client_profile, "client-profile")
    product_data = _parse_json_option(product_info, "product-info")

    # Default values if not provided
    if not client_data:
        client_data = {"name": "Cliente", "temperament": "neutral"}
    if not product_data:
        product_data = {"name": "Programa 30X", "price": "1200 USD"}

    generator = ResponseGenerator(openai_api_key=api_key)
    options = generator.generate_options(
        client_text=text,
        sentiment_score=sentiment,
        client_context=client_data,
        product_context=product_data,
        stage=stage
    )

    typer.echo(json.dumps(options, indent=2, ensure_ascii=False))


@app.command(name="generate-and-evaluate", help="Genera opciones y evalúa cuál es la mejor.")
def generate_and_evaluate(
    text: str = typer.Argument(..., help="Texto del cliente."),
    sentiment: float = typer.Option(0.5, "--sentiment", "-s", help="Score de sentimiento (0.0 a 1.0)."),
    stage: str = typer.Option("inicio", "--stage", help="Etapa de venta (inicio, negociacion, cierre)."),
    client_profile: Optional[str] = typer.Option(
        None,
        "--client-profile",
        help="JSON con datos del cliente (ej. '{\"name\": \"Carlos\", \"temperament\": \"cautious\"}').",
    ),
    product_info: Optional[str] = typer.Option(
        None,
        "--product-info",
        help="JSON con datos del producto (ej. '{\"name\": \"Suite Pro\", \"price\": \"1200 USD\"}').",
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        envvar="OPENAI_API_KEY",
        help="Clave de OpenAI (por defecto toma la variable OPENAI_API_KEY).",
    ),
):
    if not api_key:
        typer.echo("OPENAI_API_KEY no está configurada. Usa --api-key o exporta la variable de entorno.", err=True)
        raise typer.Exit(code=1)

    # Parse JSON options
    client_data = _parse_json_option(client_profile, "client-profile")
    product_data = _parse_json_option(product_info, "product-info")

    # Default values if not provided
    if not client_data:
        client_data = {"name": "Cliente", "temperament": "neutral"}
    if not product_data:
        product_data = {"name": "Programa 30X", "price": "1200 USD"}

    # Step 1: Generate options
    typer.echo("🔄 Generando opciones de respuesta...\n")
    generator = ResponseGenerator(openai_api_key=api_key)
    options = generator.generate_options(
        client_text=text,
        sentiment_score=sentiment,
        client_context=client_data,
        product_context=product_data,
        stage=stage
    )

    typer.echo("\n📋 Opciones generadas:")
    typer.echo(json.dumps(options, indent=2, ensure_ascii=False))

    # Step 2: Evaluate options
    typer.echo("\n🔄 Evaluando opciones...\n")
    
    # Create a simple conversation history for evaluation
    conversation_history = [
        {"role": "cliente", "content": text}
    ]

    evaluator = Evaluator(openai_api_key=api_key)
    result = evaluator.evaluate(conversation_history=conversation_history, options=options)

    typer.echo("\n✅ Mejor opción seleccionada:")
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


@app.command(name="full-pipeline", help="Pipeline completo: genera opciones, evalúa y adapta a personalidad.")
def full_pipeline(
    text: str = typer.Argument(..., help="Texto del cliente."),
    sentiment: float = typer.Option(0.5, "--sentiment", "-s", help="Score de sentimiento (0.0 a 1.0)."),
    stage: str = typer.Option("inicio", "--stage", help="Etapa de venta (inicio, negociacion, cierre)."),
    client_profile: Optional[str] = typer.Option(
        None,
        "--client-profile",
        help="JSON con datos del cliente (ej. '{\"name\": \"Carlos\", \"temperament\": \"cautious\"}').",
    ),
    product_info: Optional[str] = typer.Option(
        None,
        "--product-info",
        help="JSON con datos del producto (ej. '{\"name\": \"Suite Pro\", \"price\": \"1200 USD\"}').",
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        envvar="OPENAI_API_KEY",
        help="Clave de OpenAI (por defecto toma la variable OPENAI_API_KEY).",
    ),
):
    if not api_key:
        typer.echo("OPENAI_API_KEY no está configurada. Usa --api-key o exporta la variable de entorno.", err=True)
        raise typer.Exit(code=1)

    # Parse JSON options
    client_data = _parse_json_option(client_profile, "client-profile")
    product_data = _parse_json_option(product_info, "product-info")

    # Default values if not provided
    if not client_data:
        client_data = {"name": "Cliente", "temperament": "neutral"}
    if not product_data:
        product_data = {"name": "Programa 30X", "price": "1200 USD"}

    # Step 1: Generate options
    typer.echo("🔄 Paso 1: Generando opciones de respuesta...\n")
    generator = ResponseGenerator(openai_api_key=api_key)
    options = generator.generate_options(
        client_text=text,
        sentiment_score=sentiment,
        client_context=client_data,
        product_context=product_data,
        stage=stage
    )

    typer.echo("\n📋 Opciones generadas:")
    typer.echo(json.dumps(options, indent=2, ensure_ascii=False))

    # Step 2: Evaluate options
    typer.echo("\n🔄 Paso 2: Evaluando opciones...\n")
    
    conversation_history = [
        {"role": "cliente", "content": text}
    ]

    evaluator = Evaluator(openai_api_key=api_key)
    eval_result = evaluator.evaluate(conversation_history=conversation_history, options=options)

    typer.echo("\n✅ Mejor opción seleccionada:")
    typer.echo(json.dumps(eval_result, indent=2, ensure_ascii=False))

    # Step 3: Adapt to personality
    typer.echo("\n🔄 Paso 3: Adaptando a personalidad de Andrés Bilbao...\n")
    
    adapter = PersonalityAdapter(openai_api_key=api_key)
    adapted_text = adapter.adapt(eval_result["response"])

    typer.echo("\n🎯 Respuesta final adaptada:")
    typer.echo(adapted_text)

    # Final result
    typer.echo("\n" + "="*60)
    typer.echo("📊 RESUMEN DEL PIPELINE:")
    typer.echo("="*60)
    typer.echo(f"Texto original del cliente: {text}")
    typer.echo(f"Opción seleccionada (ID): {eval_result['mosfet']}")
    typer.echo(f"Texto antes de adaptar: {eval_result['response']}")
    typer.echo(f"Texto final adaptado: {adapted_text}")


@app.command(name="complete-pipeline", help="Pipeline completo con análisis de sentimiento: sentiment → generate → evaluate → adapt.")
def complete_pipeline(
    text: str = typer.Argument(..., help="Texto del cliente."),
    stage: str = typer.Option("inicio", "--stage", help="Etapa de venta (inicio, negociacion, cierre)."),
    client_profile: Optional[str] = typer.Option(
        None,
        "--client-profile",
        help="JSON con datos del cliente (ej. '{\"name\": \"Carlos\", \"temperament\": \"cautious\"}').",
    ),
    product_info: Optional[str] = typer.Option(
        None,
        "--product-info",
        help="JSON con datos del producto (ej. '{\"name\": \"Suite Pro\", \"price\": \"1200 USD\"}').",
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        envvar="OPENAI_API_KEY",
        help="Clave de OpenAI (por defecto toma la variable OPENAI_API_KEY).",
    ),
):
    if not api_key:
        typer.echo("OPENAI_API_KEY no está configurada. Usa --api-key o exporta la variable de entorno.", err=True)
        raise typer.Exit(code=1)

    # Parse JSON options
    client_data = _parse_json_option(client_profile, "client-profile")
    product_data = _parse_json_option(product_info, "product-info")

    # Default values if not provided
    if not client_data:
        client_data = {"name": "Cliente", "temperament": "neutral"}
    if not product_data:
        product_data = {"name": "Programa 30X", "price": "1200 USD"}

    typer.echo("=" * 80)
    typer.echo("🚀 PIPELINE COMPLETO DE ANÁLISIS Y RESPUESTA")
    typer.echo("=" * 80)

    # Step 1: Sentiment Analysis
    typer.echo("\n🔄 Paso 1: Analizando sentimiento y personalidad...\n")
    analyst = SentimentAnalyst(openai_api_key=api_key)
    sentiment_result = analyst.analyze(text)

    typer.echo(f"📝 Fragmentos: {len(sentiment_result['fragments'])}")
    typer.echo(f"🎯 Insight: {sentiment_result['personality_insight'][:100]}...")

    # Step 2: Generate options using sentiment analysis with tool selection
    typer.echo("\n🔄 Paso 2: Generando opciones de respuesta basadas en sentimiento...\n")
    generator = ResponseGenerator(openai_api_key=api_key)
    options = generator.generate_response(
        sentiment_analysis=sentiment_result,
        client_context=client_data,
        product_context=product_data,
        stage=stage
    )

    typer.echo("📋 Opciones generadas:")
    for opt in options:
        typer.echo(f"  • {opt['id']} ({opt['intent']}): {opt['text'][:60]}...")

    # Step 3: Evaluate options
    typer.echo("\n🔄 Paso 3: Evaluando mejor opción...\n")
    
    conversation_history = [
        {"role": "cliente", "content": text}
    ]

    evaluator = Evaluator(openai_api_key=api_key)
    eval_result = evaluator.evaluate(conversation_history=conversation_history, options=options)

    typer.echo(f"✅ Mejor opción: {eval_result['mosfet']}")
    typer.echo(f"📝 Texto: {eval_result['response'][:80]}...")

    # Step 4: Adapt to personality
    typer.echo("\n🔄 Paso 4: Adaptando a personalidad de Andrés Bilbao...\n")
    
    adapter = PersonalityAdapter(openai_api_key=api_key)
    adapted_text = adapter.adapt(eval_result["response"])

    typer.echo("🎯 Respuesta final adaptada:")
    typer.echo(f"  {adapted_text}")

    # Final summary
    typer.echo("\n" + "=" * 80)
    typer.echo("📊 RESUMEN COMPLETO")
    typer.echo("=" * 80)
    typer.echo(f"\n💬 Cliente dijo: {text}")
    typer.echo(f"\n🎭 Personalidad detectada: {sentiment_result['personality_insight']}")
    typer.echo(f"\n💭 Sentimientos:")
    for s in sentiment_result['sentiments']:
        typer.echo(f"  • {s['label']}: {s['text'][:50]}...")
    typer.echo(f"\n🎯 Opción seleccionada: {eval_result['mosfet']}")
    typer.echo(f"\n📝 Respuesta original: {eval_result['response']}")
    typer.echo(f"\n✨ Respuesta adaptada (Andrés Bilbao): {adapted_text}")
    typer.echo("\n" + "=" * 80)


@app.command(help="Ejecuta el agente closer con el texto indicado.")
def interact(
    text: str = typer.Argument(..., help="Texto recibido del cliente."),
    stage: str = typer.Option("inicio", "--stage", "-s", help="Etapa actual de la conversación."),
    personality: str = typer.Option("amigable", "--personality", "-p", help="Estilo del vendedor."),
    client_profile: Optional[str] = typer.Option(
        None,
        "--client-profile",
        help="JSON con datos del cliente (ej. '{\"temperament\": \"decisive\"}').",
    ),
    product_info: Optional[str] = typer.Option(
        None,
        "--product-info",
        help="JSON con datos del producto (ej. '{\"name\": \"Suite Pro\"}').",
    ),
    json_output: bool = typer.Option(
        False,
        "--json-output",
        help="Muestra todo el resultado en formato JSON.",
    ),
):
    profile_data = _parse_json_option(client_profile, "client-profile")
    product_data = _parse_json_option(product_info, "product-info")

    result = run_agent_interaction(
        incoming_text=text,
        client_profile=profile_data,
        product_info=product_data,
        stage=stage,
        personality=personality,
    )

    if json_output:
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
        return

    typer.echo("Mensaje final sugerido:\n")
    typer.echo(result["message"])
