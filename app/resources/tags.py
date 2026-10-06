from flask_restx import Namespace, Resource
from flask import request

tag_ns = Namespace("tags", description="Tag operations")


def _store():
    from flask import current_app
    return current_app.config["store"]


@tag_ns.route("/")
class TagList(Resource):
    def get(self):
        """List all tags"""
        return [t.to_dict() for t in _store().tags.values()]

    def post(self):
        """Create a new tag"""
        from app.models.lifecycle import Tag
        data = request.get_json() or {}
        tag = Tag.from_dict(data)
        _store().add_tag(tag)
        return tag.to_dict(), 201


@tag_ns.route("/<tag_id>")
class TagDetail(Resource):
    def get(self, tag_id):
        """Get a tag by ID"""
        from flask import abort
        tag = _store().get_tag(tag_id)
        if not tag:
            abort(404, "Tag not found")
        return tag.to_dict()

    def put(self, tag_id):
        """Update a tag"""
        from flask import abort
        if not _store().get_tag(tag_id):
            abort(404, "Tag not found")
        data = request.get_json() or {}
        tag = _store().update_tag(tag_id, data)
        return tag.to_dict()

    def delete(self, tag_id):
        """Delete a tag"""
        from flask import abort
        if not _store().delete_tag(tag_id):
            abort(404, "Tag not found")
        return "", 204


@tag_ns.route("/project/<project_id>")
class ProjectTags(Resource):
    def get(self, project_id):
        """Get all tags for a project (flat alias)"""
        return [t.to_dict() for t in _store().get_tags_by_project(project_id)]


@tag_ns.route("/project/<project_id>/tag/<tag_name>")
class ProjectTagByName(Resource):
    def get(self, project_id, tag_name):
        """Get a tag by project and name"""
        from flask import abort
        tag = _store().get_tag_by_name(project_id, tag_name)
        if not tag:
            abort(404, "Tag not found")
        return tag.to_dict()