from flask_restx import Namespace, Resource, fields
from flask import request

commit_ns = Namespace("commits", description="Commit operations")

commit_model = commit_ns.model("Commit", {
    "id": fields.String(description="Commit identifier"),
    "project": fields.Nested(commit_ns.model("CommitProjectRef", {
        "id": fields.String(description="Project identifier"),
    }), description="Parent project"),
    "description": fields.String(description="Commit description"),
    "created": fields.String(description="Creation timestamp"),
    "previous": fields.Nested(commit_ns.model("CommitPrevRef", {
        "id": fields.String(description="Previous commit identifier"),
    }), allow_null=True, description="Previous commit"),
})

commit_input_model = commit_ns.model("CommitInput", {
    "project": fields.Nested(commit_ns.model("CommitInputProject", {
        "id": fields.String(required=True, description="Project identifier"),
    }), required=True, description="Parent project"),
    "description": fields.String(description="Commit description"),
    "previous": fields.Nested(commit_ns.model("CommitInputPrev", {
        "id": fields.String(description="Previous commit identifier"),
    }), allow_null=True, description="Previous commit"),
})


@commit_ns.route("/")
class CommitList(Resource):
    @commit_ns.marshal_list_with(commit_model)
    def get(self):
        """List all commits"""
        from flask import current_app
        store = current_app.config["store"]
        return list(store.commits.values())

    @commit_ns.marshal_with(commit_model)
    @commit_ns.expect(commit_input_model)
    def post(self):
        """Create a new commit"""
        from flask import current_app
        from app.models.lifecycle import Commit
        store = current_app.config["store"]
        data = request.get_json()
        commit = Commit.from_dict(data)
        store.add_commit(commit)
        return commit, 201


@commit_ns.route("/<commit_id>")
class CommitDetail(Resource):
    @commit_ns.marshal_with(commit_model)
    def get(self, commit_id):
        """Get a commit by ID"""
        from flask import current_app, abort
        store = current_app.config["store"]
        commit = store.get_commit(commit_id)
        if not commit:
            abort(404, "Commit not found")
        return commit

    @commit_ns.marshal_with(commit_model)
    @commit_ns.expect(commit_input_model)
    def put(self, commit_id):
        """Update a commit"""
        from flask import current_app, abort
        store = current_app.config["store"]
        if not store.get_commit(commit_id):
            abort(404, "Commit not found")
        data = request.get_json()
        commit = store.update_commit(commit_id, data)
        return commit

    def delete(self, commit_id):
        """Delete a commit"""
        from flask import current_app, abort
        store = current_app.config["store"]
        if not store.delete_commit(commit_id):
            abort(404, "Commit not found")
        return "", 204


@commit_ns.route("/project/<project_id>")
class ProjectCommits(Resource):
    @commit_ns.marshal_list_with(commit_model)
    def get(self, project_id):
        """Get all commits for a project"""
        from flask import current_app
        store = current_app.config["store"]
        return store.get_commits_by_project(project_id)
