from flask_restx import Namespace, Resource, fields
from flask import request

tag_ns = Namespace("tags", description="Tag operations")

tag_model = tag_ns.model("Tag", {
    "id": fields.String(description="Tag identifier"),
    "project": fields.Nested(tag_ns.model("TagProjectRef", {
        "id": fields.String(description="Project identifier"),
    }), description="Parent project"),
    "name": fields.String(description="Tag name"),
    "commit": fields.Nested(tag_ns.model("TagCommitRef", {
        "id": fields.String(description="Commit identifier"),
    }), allow_null=True, description="Tagged commit"),
})

tag_input_model = tag_ns.model("TagInput", {
    "project": fields.Nested(tag_ns.model("TagInputProject", {
        "id": fields.String(required=True, description="Project identifier"),
    }), required=True, description="Parent project"),
    "name": fields.String(required=True, description="Tag name"),
    "commit": fields.Nested(tag_ns.model("TagInputCommit", {
        "id": fields.String(required=True, description="Commit identifier"),
    }), required=True, description="Tagged commit"),
})


@tag_ns.route("/")
class TagList(Resource):
    @tag_ns.marshal_list_with(tag_model)
    def get(self):
        """List all tags"""
        from flask import current_app
        store = current_app.config["store"]
        return list(store.tags.values())

    @tag_ns.marshal_with(tag_model)
    @tag_ns.expect(tag_input_model)
    def post(self):
        """Create a new tag"""
        from flask import current_app
        from app.models.lifecycle import Tag
        store = current_app.config["store"]
        data = request.get_json()
        tag = Tag.from_dict(data)
        store.add_tag(tag)
        return tag, 201


@tag_ns.route("/<tag_id>")
class TagDetail(Resource):
    @tag_ns.marshal_with(tag_model)
    def get(self, tag_id):
        """Get a tag by ID"""
        from flask import current_app, abort
        store = current_app.config["store"]
        tag = store.get_tag(tag_id)
        if not tag:
            abort(404, "Tag not found")
        return tag

    @tag_ns.marshal_with(tag_model)
    @tag_ns.expect(tag_input_model)
    def put(self, tag_id):
        """Update a tag"""
        from flask import current_app, abort
        store = current_app.config["store"]
        if not store.get_tag(tag_id):
            abort(404, "Tag not found")
        data = request.get_json()
        tag = store.update_tag(tag_id, data)
        return tag

    def delete(self, tag_id):
        """Delete a tag"""
        from flask import current_app, abort
        store = current_app.config["store"]
        if not store.delete_tag(tag_id):
            abort(404, "Tag not found")
        return "", 204


@tag_ns.route("/project/<project_id>")
class ProjectTags(Resource):
    @tag_ns.marshal_list_with(tag_model)
    def get(self, project_id):
        """Get all tags for a project"""
        from flask import current_app
        store = current_app.config["store"]
        return store.get_tags_by_project(project_id)


@tag_ns.route("/project/<project_id>/tag/<tag_name>")
class ProjectTagByName(Resource):
    @tag_ns.marshal_with(tag_model)
    def get(self, project_id, tag_name):
        """Get a tag by project and name"""
        from flask import current_app, abort
        store = current_app.config["store"]
        tag = store.get_tag_by_name(project_id, tag_name)
        if not tag:
            abort(404, "Tag not found")
        return tag
