"""Commit endpoints — OMG Systems Modeling API & Services alignment.

Commits are IMMUTABLE per the spec (no PUT/DELETE). Canonical nested
routes live in canonical.py (mounted at the API root, mirroring the
spec URL space /projects/{pid}/commits/...); the routes here are the
flat aliases kept for back-compatibility.
"""
from flask_restx import Namespace, Resource
from flask import request

commit_ns = Namespace("commits", description="Commit operations")


def _store():
    from flask import current_app
    return current_app.config["store"]


def _serialize(obj):
    return obj.to_dict() if hasattr(obj, "to_dict") else obj


@commit_ns.route("/")
class CommitList(Resource):
    def get(self):
        """List all commits"""
        return [_serialize(c) for c in _store().commits.values()]

    def post(self):
        """Create a new commit"""
        from app.models.lifecycle import Commit
        data = request.get_json() or {}
        commit = Commit.from_dict(data)
        _store().add_commit(commit)
        return commit.to_dict(), 201


@commit_ns.route("/<commit_id>")
class CommitDetail(Resource):
    def get(self, commit_id):
        """Get a commit by ID"""
        from flask import abort
        commit = _store().get_commit(commit_id)
        if not commit:
            abort(404, "Commit not found")
        return commit.to_dict()


@commit_ns.route("/project/<project_id>")
class ProjectCommits(Resource):
    def get(self, project_id):
        """Get all commits for a project (flat alias)"""
        return [_serialize(c) for c in _store().get_commits_by_project(project_id)]