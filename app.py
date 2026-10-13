import os
import sys

# Try loading .env and .flaskenv explicitly in case CLI didn't load them
try:
    from dotenv import load_dotenv
    # Load .flaskenv and .env if present
    load_dotenv('.flaskenv')
    load_dotenv('.env')
except ImportError:
    pass

# Patch werkzeug run_simple and flask CLI default port so `flask run` defaults to 4000
try:
    import werkzeug.serving
    _orig_run_simple = werkzeug.serving.run_simple

    def _patched_run_simple(hostname, port, application, *args, **kwargs):
        # Check if user explicitly passed a custom port in CLI args
        has_cli_port = any(arg in sys.argv for arg in ['-p', '--port']) or any(
            arg.startswith(('--port=', '-p=')) for arg in sys.argv
        )
        if not has_cli_port and port == 5000:
            port = int(os.environ.get('PORT', 4000))
        return _orig_run_simple(hostname, port, application, *args, **kwargs)

    werkzeug.serving.run_simple = _patched_run_simple
except Exception:
    pass

try:
    import flask.cli
    port_param = [p for p in flask.cli.run_command.params if p.name == 'port']
    if port_param:
        port_param[0].default = 4000
except Exception:
    pass

from flask import Flask
from flask_socketio import SocketIO
from models import db
from views import auth_bp, chat_bp
from socket_events import register_socket_events

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'open-chatting-secret-key-2026')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max file upload

    # Initialize extensions
    db.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)

    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    register_socket_events(socketio)

    # Create tables and auto-migrate schema for new file columns
    with app.app_context():
        db.create_all()
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            if inspector.has_table('messages'):
                existing_cols = [c['name'] for c in inspector.get_columns('messages')]
                with db.engine.connect() as conn:
                    if 'file_url' not in existing_cols:
                        conn.execute(text("ALTER TABLE messages ADD COLUMN file_url VARCHAR(256)"))
                    if 'file_name' not in existing_cols:
                        conn.execute(text("ALTER TABLE messages ADD COLUMN file_name VARCHAR(256)"))
                    if 'file_size' not in existing_cols:
                        conn.execute(text("ALTER TABLE messages ADD COLUMN file_size INTEGER"))
                    if 'file_type' not in existing_cols:
                        conn.execute(text("ALTER TABLE messages ADD COLUMN file_type VARCHAR(64)"))
                    conn.commit()
        except Exception as e:
            print("DB schema migration notice:", e)

    return app, socketio

app, socketio = create_app()

if __name__ == '__main__':
    # Run server on all interfaces so local and network devices can connect (Default port: 4000)
    port = int(os.environ.get('PORT', 4000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
