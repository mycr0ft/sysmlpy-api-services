import os
from flask import Flask
from flask_restx import Api
from flask_cors import CORS

from app.config import config_by_name
from app.storage.graph_store import GraphStore


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    CORS(app)

    store = GraphStore()
    app.config["store"] = store

    api = Api(
        app,
        version="1.0.0",
        title="SysMLv2 API Services",
        description="Python implementation of SysMLv2 REST API Services using Flask-RESTX and sysmlpy",
        doc="/docs/",
        prefix="/api",
    )

    from app.resources.projects import project_ns
    from app.resources.commits import commit_ns
    from app.resources.branches import branch_ns
    from app.resources.tags import tag_ns
    from app.resources.elements import element_ns
    from app.resources.relationships import relationship_ns
    from app.resources.queries import query_ns
    from app.resources.schema import schema_ns
    from app.resources.model_text import model_ns

    api.add_namespace(project_ns, path="/projects")
    api.add_namespace(commit_ns, path="/commits")
    api.add_namespace(branch_ns, path="/branches")
    api.add_namespace(tag_ns, path="/tags")
    api.add_namespace(element_ns, path="/elements")
    api.add_namespace(relationship_ns, path="/relationships")
    api.add_namespace(query_ns, path="/query")
    api.add_namespace(schema_ns, path="/schema")
    api.add_namespace(model_ns, path="/model")

    @app.route("/")
    def index():
        return {"message": "SysMLv2 API Services", "docs": "/api/docs/"}

    @app.route("/health")
    def health():
        return {"status": "healthy"}

    return app
