from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .routes import bp, init_oauth


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["ISSUER"] = Config().ISSUER

    if app.config["BEHIND_PROXY"]:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    init_oauth(app)
    app.register_blueprint(bp, url_prefix=app.config["URL_PREFIX"])
    return app
