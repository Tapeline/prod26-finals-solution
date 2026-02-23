import click

from alphabet.bootstrap.entrypoints.attribution_worker import (
    main as attribution_main,
)
from alphabet.bootstrap.entrypoints.guardrails_worker import (
    main as guardrails_main,
)
from alphabet.bootstrap.entrypoints.notifications_worker import (
    main as notifications_main,
)
from alphabet.bootstrap.entrypoints.web_app import main as web_main


@click.group()
def cli() -> None: ...


@cli.command()
@click.argument(
    "what",
    type=click.Choice(
        [
            "server",
            "attribution_worker",
            "notifications_worker",
            "guardrails_worker",
        ],
        case_sensitive=False,
    ),
    required=True,
)
def run(what: str) -> None:
    match what:
        case "server":
            web_main()
        case "attribution_worker":
            attribution_main()
        case "notifications_worker":
            notifications_main()
        case "guardrails_worker":
            guardrails_main()
        case _:
            raise click.UsageError(f"Unknown target: {what}")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
