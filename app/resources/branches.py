from flask_restx import Namespace, Resource, fields
from flask import request

branch_ns = Namespace("branches", description="Branch operations")

branch_model = branch_ns.model("Branch", {
    "id": fields.String(description="Branch identifier"),
    "project": fields.Nested(branch_ns.model("BranchProjectRef", {
        "id": fields.String(description="Project identifier"),
    }), description="Parent project"),
    "name": fields.String(description="Branch name"),
    "head": fields.Nested(branch_ns.model("BranchHeadRef", {
        "id": fields.String(description="Head commit identifier"),
    }), allow_null=True, description="Head commit"),
})

branch_input_model = branch_ns.model("BranchInput", {
    "project": fields.Nested(branch_ns.model("BranchInputProject", {
        "id": fields.String(required=True, description="Project identifier"),
    }), required=True, description="Parent project"),
    "name": fields.String(required=True, description="Branch name"),
    "head": fields.Nested(branch_ns.model("BranchInputHead", {
        "id": fields.String(description="Head commit identifier"),
    }), allow_null=True, description="Head commit"),
})


@branch_ns.route("/")
class BranchList(Resource):
    @branch_ns.marshal_list_with(branch_model)
    def get(self):
        """List all branches"""
        from flask import current_app
        store = current_app.config["store"]
        return list(store.branches.values())

    @branch_ns.marshal_with(branch_model)
    @branch_ns.expect(branch_input_model)
    def post(self):
        """Create a new branch"""
        from flask import current_app
        from app.models.lifecycle import Branch
        store = current_app.config["store"]
        data = request.get_json()
        branch = Branch.from_dict(data)
        store.add_branch(branch)
        return branch, 201


@branch_ns.route("/<branch_id>")
class BranchDetail(Resource):
    @branch_ns.marshal_with(branch_model)
    def get(self, branch_id):
        """Get a branch by ID"""
        from flask import current_app, abort
        store = current_app.config["store"]
        branch = store.get_branch(branch_id)
        if not branch:
            abort(404, "Branch not found")
        return branch

    @branch_ns.marshal_with(branch_model)
    @branch_ns.expect(branch_input_model)
    def put(self, branch_id):
        """Update a branch"""
        from flask import current_app, abort
        store = current_app.config["store"]
        if not store.get_branch(branch_id):
            abort(404, "Branch not found")
        data = request.get_json()
        branch = store.update_branch(branch_id, data)
        return branch

    def delete(self, branch_id):
        """Delete a branch"""
        from flask import current_app, abort
        store = current_app.config["store"]
        if not store.delete_branch(branch_id):
            abort(404, "Branch not found")
        return "", 204


@branch_ns.route("/project/<project_id>")
class ProjectBranches(Resource):
    @branch_ns.marshal_list_with(branch_model)
    def get(self, project_id):
        """Get all branches for a project"""
        from flask import current_app
        store = current_app.config["store"]
        return store.get_branches_by_project(project_id)


@branch_ns.route("/project/<project_id>/branch/<branch_name>")
class ProjectBranchByName(Resource):
    @branch_ns.marshal_with(branch_model)
    def get(self, project_id, branch_name):
        """Get a branch by project and name"""
        from flask import current_app, abort
        store = current_app.config["store"]
        branch = store.get_branch_by_name(project_id, branch_name)
        if not branch:
            abort(404, "Branch not found")
        return branch
