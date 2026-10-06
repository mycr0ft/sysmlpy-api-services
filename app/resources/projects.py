from flask_restx import Namespace, Resource
from flask import request

project_ns = Namespace("projects", description="Project operations")


def _store():
    from flask import current_app
    return current_app.config["store"]


@project_ns.route("/")
class ProjectList(Resource):
    def get(self):
        """List all projects"""
        return [p.to_dict() for p in _store().get_all_projects()]

    def post(self):
        """Create a new project (spec: starts with default branch + initial commit)"""
        from app.models.lifecycle import Project, Branch, Commit
        data = request.get_json() or {}
        project = Project.from_dict(data)
        store = _store()
        store.add_project(project)
        commit = Commit(project_id=project.id, description="Initial commit")
        store.add_commit(commit)
        branch = Branch(project_id=project.id, name="main", head=commit.id)
        store.add_branch(branch)
        d = project.to_dict()
        d["defaultBranch"] = branch.to_dict()
        return d, 201


@project_ns.route("/<project_id>")
class ProjectDetail(Resource):
    def get(self, project_id):
        """Get a project by ID (with commit/branch members per spec)"""
        from flask import abort
        store = _store()
        project = store.get_project(project_id)
        if not project:
            abort(404, "Project not found")
        d = project.to_dict()
        d["commits"] = [{"identifier": c.id} for c in store.get_commits_by_project(project_id)]
        d["branches"] = [{"identifier": b.id} for b in store.get_branches_by_project(project_id)]
        return d

    def put(self, project_id):
        """Update a project"""
        from flask import abort
        if not _store().get_project(project_id):
            abort(404, "Project not found")
        data = request.get_json() or {}
        project = _store().update_project(project_id, data)
        return project.to_dict()

    def delete(self, project_id):
        """Delete a project"""
        from flask import abort
        if not _store().delete_project(project_id):
            abort(404, "Project not found")
        return "", 204