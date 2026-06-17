import click
from sdd import __version__
from sdd.commands.init import init_command
from sdd.commands.upgrade import upgrade_command


@click.group()
@click.version_option(__version__, prog_name="sdd")
def cli():
    """SDD Framework CLI — Spec-Driven Development"""


cli.add_command(init_command, name="init")
cli.add_command(upgrade_command, name="upgrade")


if __name__ == "__main__":
    cli()
