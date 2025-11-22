import json
from typing import Any, Dict, Optional

import typer

try:  # Support both installed package and local execution via `python -m cli`
    from metatron.agents.closer import run_agent_interaction
    from metatron.agents.personality_adapter import PersonalityAdapter
    from metatron.agents.evaluator import Evaluator
except ModuleNotFoundError:  # pragma: no cover - dev fallback
    from agents.closer import run_agent_interaction  # type: ignore
    from agents.personality_adapter import PersonalityAdapter  # type: ignore
    from agents.evaluator import Evaluator  # type: ignore

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
