from flask_restx import Namespace, Resource
from flask import request

branch_ns = Namespace("branches", description="Branch operations")


def _store():
    from flask import current_app
    return current_app.config["store"]


@branch_ns.route("/")
class BranchList(Resource):
    def get(self):
        """List all branches"""
        return [b.to_dict() for b in _store().branches.values()]

    def post(self):
        """Create a new branch"""
        from app.models.lifecycle import Branch
        data = request.get_json() or {}
        branch = Branch.from_dict(data)
        _store().add_branch(branch)
        return branch.to_dict(), 201


@branch_ns.route("/<branch_id>")
class BranchDetail(Resource):
    def get(self, branch_id):
        """Get a branch by ID"""
        from flask import abort
        branch = _store().get_branch(branch_id)
        if not branch:
            abort(404, "Branch not found")
        return branch.to_dict()

    def put(self, branch_id):
        """Update a branch"""
        from flask import abort
        if not _store().get_branch(branch_id):
            abort(404, "Branch not found")
        data = request.get_json() or {}
        branch = _store().update_branch(branch_id, data)
        return branch.to_dict()

    def delete(self, branch_id):
        """Delete a branch"""
        from flask import abort
        if not _store().delete_branch(branch_id):
            abort(404, "Branch not found")
        return "", 204


@branch_ns.route("/project/<project_id>")
class ProjectBranches(Resource):
    def get(self, project_id):
        """Get all branches for a project (flat alias)"""
        return [b.to_dict() for b in _store().get_branches_by_project(project_id)]


@branch_ns.route("/project/<project_id>/branch/<branch_name>")
class ProjectBranchByName(Resource):
    def get(self, project_id, branch_name):
        """Get a branch by project and name"""
        from flask import abort
        branch = _store().get_branch_by_name(project_id, branch_name)
        if not branch:
            abort(404, "Branch not found")
        return branch.to_dict()