import click
from flask.cli import with_appcontext
from app import db
from app.models.user import User, Role, Permission
from app.services.user_service import create_user

@click.group()
def cli():
    """User management commands."""
    pass

@cli.command("create-user")
@click.argument("username")
@click.password_option()
@click.argument("role")
@with_appcontext
def create_user_command(username, password, role):
    """Create a new user."""
    try:
        user = create_user(username, password, role)
        click.echo(f"Created user {user.username} with role {user.role}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)

@cli.command("list-users")
@with_appcontext
def list_users_command():
    """List all users."""
    users = User.query.all()
    if not users:
        click.echo("No users found.")
        return
    
    click.echo("Users:")
    for user in users:
        status = "active" if user.is_active else "inactive"
        click.echo(f"- {user.username} (Role: {user.role}, Status: {status})")

@cli.command("init-db")
@with_appcontext
def init_db_command():
    """Initialize the database."""
    db.create_all()
    click.echo("Initialized the database.")

def init_app(app):
    """Register CLI commands with the application."""
    app.cli.add_command(cli)
