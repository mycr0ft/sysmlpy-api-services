from flask_restx import Namespace, Resource
from flask import request

element_ns = Namespace("elements", description="Element operations")

# NOTE: no marshal_with masks on these endpoints — the spec EJSON shape
# (@type, identifier, owner: {identifier}, ownedRelationship, values, ...)
# must pass through unfiltered. Masks were why relationship payloads
# (FeatureTyping/Subsetting/Redefinition) vanished from responses.


def _store():
    from flask import current_app
    return current_app.config["store"]


@element_ns.route("/")
class ElementList(Resource):
    def get(self):
        """List all elements (spec EJSON shape, unmasked)"""
        from flask import request as flask_request
        commit_id = flask_request.args.get("commit")
        return [e.to_dict(include_all=True) for e in _store().get_all_elements(commit_id=commit_id)]

    def post(self):
        """Create a new element"""
        from app.models.element import Element
        data = request.get_json() or {}
        element = Element.from_dict(data)
        _store().add_element(element)
        return element.to_dict(), 201


@element_ns.route("/<element_id>")
class ElementDetail(Resource):
    def get(self, element_id):
        """Get an element by ID (full EJSON, incl. ownedRelationship)"""
        from flask import abort, request as flask_request
        commit_id = flask_request.args.get("commit")
        element = _store().get_element(element_id, commit_id=commit_id)
        if not element:
            abort(404, "Element not found")
        return element.to_dict(include_all=True)

    def put(self, element_id):
        """Update an element"""
        from flask import abort
        if not _store().get_element(element_id):
            abort(404, "Element not found")
        data = request.get_json() or {}
        element = _store().get_element(element_id)
        for key, value in data.items():
            if key == "@type":
                element.type = value
            elif key == "identifier":
                element.id = value
            elif key == "name":
                element.name = value
            elif key == "qualifiedName":
                element.qualified_name = value
            elif key == "owner":
                element.owner_id = (value.get("identifier") or value.get("id")) if isinstance(value, dict) else None
            elif key == "project":
                element.project_id = (value.get("identifier") or value.get("id")) if isinstance(value, dict) else None
            else:
                element.data[key] = value
        _store().update_element(element_id, element.to_dict(include_all=True))
        return element.to_dict(include_all=True)

    def delete(self, element_id):
        """Delete an element"""
        from flask import abort
        if not _store().delete_element(element_id):
            abort(404, "Element not found")
        return "", 204


@element_ns.route("/<element_id>/owned")
class OwnedElements(Resource):
    def get(self, element_id):
        """Get owned elements"""
        from flask import abort, request as flask_request
        if not _store().get_element(element_id):
            abort(404, "Element not found")
        recursive = flask_request.args.get("recursive", "false").lower() == "true"
        return [e.to_dict() for e in _store().get_owned_elements(element_id, recursive=recursive)]


@element_ns.route("/<element_id>/relationships")
class ElementRelationships(Resource):
    def get(self, element_id):
        """Get relationships for an element (direction=outgoing|incoming|both)"""
        from flask import abort, request as flask_request
        if not _store().get_element(element_id):
            abort(404, "Element not found")
        direction = flask_request.args.get("direction", "both")
        return _store().get_relationships(element_id, direction=direction)