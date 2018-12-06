from app import create_app, db
from app.models import User, UserItem, Task, Notification
from flask_migrate import upgrade


app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'UserItem': UserItem,
        'Task': Task,
        'Notification': Notification
    }


@app.cli.command()
def deploy():
    """Run deployment tasks."""
    # Don' t forget to `export FLASK_APP=gcpubsub.py` for the command to work
    # or set it in a `.flaskenv` file on the top-level dir of the project.

    # migrate database to latest revision
    upgrade()

    # create or update user roles
    # Role.insert_roles()

    # Seed User db with `admin` user.
    User.add_user('admin', 'admin@gcpubsub.com', 'cannotguess')


if __name__ == '__main__':
    # app.run(debug=True, use_debugger=False, use_reloader=False, passthrough_errors=True)
    app.run()
