import click

from sdd import __version__
from sdd.commands.config import config_command
from sdd.commands.confluence import confluence_command
from sdd.commands.cr import cr_command
from sdd.commands.dashboard import dashboard_command
from sdd.commands.feature import feature_command
from sdd.commands.init import init_command
from sdd.commands.jira import jira_command
from sdd.commands.pr import pr_command
from sdd.commands.project_type import project_type_command
from sdd.commands.review import review_command
from sdd.commands.token_log import token_log_command
from sdd.commands.upgrade import upgrade_command


@click.group()
@click.version_option(__version__, prog_name="sdd")
def cli():
    """SDD Framework CLI — Spec-Driven Development"""


cli.add_command(init_command, name="init")
cli.add_command(upgrade_command, name="upgrade")
cli.add_command(config_command, name="config")
cli.add_command(jira_command, name="jira")
cli.add_command(confluence_command, name="confluence")
cli.add_command(review_command, name="review")
cli.add_command(cr_command, name="cr")
cli.add_command(pr_command, name="pr")
cli.add_command(dashboard_command, name="dashboard")
cli.add_command(token_log_command, name="token-log")
cli.add_command(project_type_command, name="project-type")
cli.add_command(feature_command, name="feature")


if __name__ == "__main__":
    cli()
