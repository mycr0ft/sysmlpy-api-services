from flask_restx import Namespace, Resource, fields
from flask import request

project_ns = Namespace("projects", description="Project operations")

project_model = project_ns.model("Project", {
    "id": fields.String(description="Project identifier"),
    "name": fields.String(required=True, description="Project name"),
    "description": fields.String(description="Project description"),
    "created": fields.String(description="Creation timestamp"),
    "updated": fields.String(description="Last update timestamp"),
})

project_input_model = project_ns.model("ProjectInput", {
    "name": fields.String(required=True, description="Project name"),
    "description": fields.String(description="Project description"),
})


@project_ns.route("/")
class ProjectList(Resource):
    @project_ns.marshal_list_with(project_model)
    def get(self):
        """List all projects"""
        from flask import current_app
        store = current_app.config["store"]
        return store.get_all_projects()

    @project_ns.marshal_with(project_model)
    @project_ns.expect(project_input_model)
    def post(self):
        """Create a new project"""
        from flask import current_app
        from app.models.lifecycle import Project
        store = current_app.config["store"]
        data = request.get_json()
        project = Project.from_dict(data)
        store.add_project(project)
        return project, 201


@project_ns.route("/<project_id>")
class ProjectDetail(Resource):
    @project_ns.marshal_with(project_model)
    def get(self, project_id):
        """Get a project by ID"""
        from flask import current_app, abort
        store = current_app.config["store"]
        project = store.get_project(project_id)
        if not project:
            abort(404, "Project not found")
        return project

    @project_ns.marshal_with(project_model)
    @project_ns.expect(project_input_model)
    def put(self, project_id):
        """Update a project"""
        from flask import current_app, abort
        store = current_app.config["store"]
        if not store.get_project(project_id):
            abort(404, "Project not found")
        data = request.get_json()
        project = store.update_project(project_id, data)
        return project

    def delete(self, project_id):
        """Delete a project"""
        from flask import current_app, abort
        store = current_app.config["store"]
        if not store.delete_project(project_id):
            abort(404, "Project not found")
        return "", 204
