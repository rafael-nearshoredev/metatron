import json
from typing import Any, Dict, Optional

import typer

try:  # Support both installed package and local execution via `python -m cli`
    from metatron.agents.closer import run_agent_interaction, Closer
    from metatron.agents.personality_adapter import PersonalityAdapter
    from metatron.agents.evaluator import Evaluator
    from metatron.agents.response_generator import ResponseGenerator
    from metatron.agents.sentiment_evaluator import SentimentAnalyst
except ModuleNotFoundError:  # pragma: no cover - dev fallback
    from agents.closer import run_agent_interaction, Closer  # type: ignore
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
        envvar="GROQ_API_KEY",
        help="Clave de Groq (por defecto toma la variable GROQ_API_KEY).",
    ),
):
    if not api_key:
        typer.echo("GROQ_API_KEY no está configurada. Usa --api-key o exporta la variable de entorno.", err=True)
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
        envvar="GROQ_API_KEY",
        help="Clave de Groq (por defecto toma la variable GROQ_API_KEY).",
    ),
):
    if not api_key:
        typer.echo("GROQ_API_KEY no está configurada. Usa --api-key o exporta la variable de entorno.", err=True)
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
        envvar="GROQ_API_KEY",
        help="Clave de Groq (por defecto toma la variable GROQ_API_KEY).",
    ),
):
    if not api_key:
        typer.echo("GROQ_API_KEY no está configurada. Usa --api-key o exporta la variable de entorno.", err=True)
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
        envvar="GROQ_API_KEY",
        help="Clave de Groq (por defecto toma la variable GROQ_API_KEY).",
    ),
):
    if not api_key:
        typer.echo("GROQ_API_KEY no está configurada. Usa --api-key o exporta la variable de entorno.", err=True)
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
        envvar="GROQ_API_KEY",
        help="Clave de Groq (por defecto toma la variable GROQ_API_KEY).",
    ),
):
    if not api_key:
        typer.echo("GROQ_API_KEY no está configurada. Usa --api-key o exporta la variable de entorno.", err=True)
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
        envvar="GROQ_API_KEY",
        help="Clave de Groq (por defecto toma la variable GROQ_API_KEY).",
    ),
):
    if not api_key:
        typer.echo("GROQ_API_KEY no está configurada. Usa --api-key o exporta la variable de entorno.", err=True)
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
        envvar="GROQ_API_KEY",
        help="Clave de Groq (por defecto toma la variable GROQ_API_KEY).",
    ),
):
    if not api_key:
        typer.echo("GROQ_API_KEY no está configurada. Usa --api-key o exporta la variable de entorno.", err=True)
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


@app.command(name="chat", help="Inicia una conversación interactiva con el Closer.")
def chat(
    stage: str = typer.Option("inicio", "--stage", "-s", help="Etapa inicial de la conversación."),
    client_name: Optional[str] = typer.Option(None, "--client-name", help="Nombre del cliente."),
):
    """
    Inicia una sesión de chat interactiva con el Closer.
    Mantiene el contexto de la conversación entre mensajes.
    """
    try:
        typer.echo("=" * 80)
        typer.echo("💬 CHAT INTERACTIVO CON EL CLOSER")
        typer.echo("=" * 80)
        typer.echo("\nInicializando el Closer...")
        
        # Crear instancia de Closer (mantiene contexto)
        closer = Closer()
        
        # Configurar información del cliente si se proporciona
        if client_name:
            closer.context.client_profile["name"] = client_name
        
        # Configurar etapa inicial
        if stage:
            closer.context.update_stage(stage)
        
        typer.echo(f"\n✅ Closer inicializado")
        typer.echo(f"📊 Etapa: {closer.context.stage}")
        typer.echo(f"👤 Cliente: {closer.context.client_profile.get('name', 'No especificado')}")
        typer.echo("\n" + "=" * 80)
        typer.echo("Escribe tus mensajes y presiona Enter.")
        typer.echo("Comandos especiales:")
        typer.echo("  /exit o /quit - Salir del chat")
        typer.echo("  /reset - Reiniciar la conversación")
        typer.echo("  /context - Ver el contexto actual")
        typer.echo("  /stage <etapa> - Cambiar la etapa (inicio, negociacion, cierre)")
        typer.echo("=" * 80 + "\n")
        
        message_count = 0
        
        while True:
            try:
                # Leer input del usuario
                user_input = typer.prompt(f"\n[{message_count}] Tú", prompt_suffix=": ")
                
                # Procesar comandos especiales
                if user_input.lower() in ["/exit", "/quit"]:
                    typer.echo("\n👋 ¡Hasta luego!")
                    break
                
                elif user_input.lower() == "/reset":
                    closer.reset_context()
                    message_count = 0
                    typer.echo("\n🔄 Conversación reiniciada")
                    continue
                
                elif user_input.lower() == "/context":
                    typer.echo("\n📊 CONTEXTO ACTUAL:")
                    typer.echo(f"  Etapa: {closer.context.stage}")
                    typer.echo(f"  Mensajes: {len(closer.context.conversation_history)}")
                    typer.echo(f"  Cliente: {json.dumps(closer.context.client_profile, indent=2, ensure_ascii=False)}")
                    continue
                
                elif user_input.lower().startswith("/stage "):
                    new_stage = user_input.split(" ", 1)[1].strip()
                    closer.context.update_stage(new_stage)
                    typer.echo(f"\n✅ Etapa cambiada a: {new_stage}")
                    continue
                
                # Procesar mensaje normal
                typer.echo("\n🤔 Procesando...")
                
                result = closer.process_message(
                    incoming_text=user_input,
                    stage=closer.context.stage
                )
                
                message_count += 1
                
                # Mostrar respuesta
                typer.echo(f"\n[{message_count}] Closer: {result['adapted_response']}")
                
                # Mostrar info adicional
                sentiment = result['sentiment_analysis']
                typer.echo(f"\n💭 Sentimiento detectado: {len(sentiment.get('sentiments', []))} fragmentos")
                typer.echo(f"🎯 Etapa actual: {closer.context.stage}")
                
            except KeyboardInterrupt:
                typer.echo("\n\n👋 Chat interrumpido. ¡Hasta luego!")
                break
            except EOFError:
                typer.echo("\n\n👋 ¡Hasta luego!")
                break
                
    except ValueError as e:
        typer.echo(f"\n❌ Error: {e}", err=True)
        typer.echo("Por favor configura GROQ_API_KEY en tu archivo .env", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"\n❌ Error inesperado: {e}", err=True)
        raise typer.Exit(code=1)


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


@app.command(name="voice-worker", help="Inicia el worker de voz de LiveKit")
def start_voice_worker():
    """
    Start the LiveKit voice agent worker.
    This worker will join LiveKit rooms and handle voice conversations.
    """
    try:
        from metatron.agents.voice_agent import run_voice_worker
        from metatron.config import settings
    except ImportError:
        from metatron.agents.voice_agent import run_voice_worker  # type: ignore
        from metatron.config import settings  # type: ignore
    
    typer.echo("=" * 80)
    typer.echo("🎙️  METATRON VOICE WORKER")
    typer.echo("=" * 80)
    
    # Validate configuration
    if not settings.livekit_url:
        typer.echo("\n❌ Error: LIVEKIT_URL not configured", err=True)
        typer.echo("Please set LIVEKIT_URL in your .env file", err=True)
        raise typer.Exit(code=1)
    
    if not settings.livekit_api_key or not settings.livekit_api_secret:
        typer.echo("\n❌ Error: LiveKit credentials not configured", err=True)
        typer.echo("Please set LIVEKIT_API_KEY and LIVEKIT_API_SECRET in your .env file", err=True)
        raise typer.Exit(code=1)
    
    if not settings.openai_api_key:
        typer.echo("\n❌ Error: OPENAI_API_KEY not configured", err=True)
        typer.echo("OpenAI is required for Whisper STT. Please set OPENAI_API_KEY in your .env file", err=True)
        raise typer.Exit(code=1)
    
    if not settings.elevenlabs_api_key:
        typer.echo("\n❌ Error: ElevenLabs API key not configured", err=True)
        typer.echo("Please set ELEVENLABS_API_KEY in your .env file", err=True)
        raise typer.Exit(code=1)
    
    typer.echo(f"\n✓ LiveKit URL: {settings.livekit_url}")
    typer.echo(f"✓ OpenAI API: Configured")
    typer.echo(f"✓ MiniMax API: Configured")
    typer.echo(f"✓ Groq API: {'Configured' if settings.groq_api_key else 'Not set'}")
    typer.echo("\nWaiting for connections...\n")
    
    try:
        run_voice_worker()
    except KeyboardInterrupt:
        typer.echo("\n\n👋 Voice worker stopped.")
    except Exception as e:
        typer.echo(f"\n❌ Error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command(name="api-server", help="Inicia el servidor API de FastAPI")
def start_api_server(
    host: Optional[str] = typer.Option(None, help="Host override (default from config)"),
    port: Optional[int] = typer.Option(None, help="Port override (default from config)"),
):
    """
    Start the FastAPI server for room management and context APIs.
    This is an alternative to running 'python -m metatron.main'.
    """
    try:
        from metatron.config import settings
        from metatron.main import app
    except ImportError:
        from config import settings  # type: ignore
        from main import app  # type: ignore
    
    import uvicorn
    
    host = host or settings.host
    port = port or settings.port
    
    typer.echo("=" * 80)
    typer.echo("🚀 METATRON API SERVER")
    typer.echo("=" * 80)
    typer.echo(f"\nServer: http://{host}:{port}")
    typer.echo(f"Docs: http://{host}:{port}/docs")
    typer.echo(f"Redoc: http://{host}:{port}/redoc")
    typer.echo(f"Health: http://{host}:{port}/ping\n")
    
    typer.echo("Available endpoints:")
    typer.echo("  - GET  /ping - Health check")
    typer.echo("  - GET  /context/{type} - Get context content")
    typer.echo("  - PUT  /context/{type} - Update context content")
    typer.echo("  - POST /rooms/create - Create LiveKit room")
    typer.echo("  - GET  /rooms - List active rooms")
    typer.echo("  - DELETE /rooms/{name} - Delete a room\n")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=settings.log_level.lower(),
    )
