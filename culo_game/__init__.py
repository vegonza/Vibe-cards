from flask import Flask


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__, static_folder='../app/static', template_folder='../app/templates')

    # Import configuration
    from culo_game.config.config import configure_app
    configure_app(app)

    # Register blueprints
    from culo_game.controllers.game_controller import game_bp
    from culo_game.controllers.player_controller import player_bp
    from culo_game.controllers.chat_controller import chat_bp
    from culo_game.controllers.admin_controller import admin_bp

    app.register_blueprint(game_bp)
    app.register_blueprint(player_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(admin_bp)

    return app
