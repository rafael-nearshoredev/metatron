import json
from typing import Any, Dict, Optional

import typer

try:  # Support both installed package and local execution via `python -m cli`
    from metatron.agents.closer import run_agent_interaction
except ModuleNotFoundError:  # pragma: no cover - dev fallback
    from agents.closer import run_agent_interaction  # type: ignore

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
