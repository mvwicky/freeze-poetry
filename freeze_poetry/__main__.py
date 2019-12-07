import os
from typing import Callable

import click
from funcy import compose


def create_cli(f: Callable = None):
    if f is None:

        def inner(func: Callable):
            return create_cli(func)

        return inner

    wrappers = [
        click.option("--dev/--prod", "-d/-p", "mode", default=True),
        click.option(
            "--force/--no-force",
            "-f/ ",
            default=False,
            help="Build even if not out of date.",
        ),
        click.argument(
            "root", type=click.Path(file_okay=False), default=os.getcwd()
        ),
        click.command(context_settings={"max_content_width": 100}),
    ]
    return compose(*wrappers)(f)


@create_cli()
def cli():
    pass


if __name__ == "__main__":
    cli()
