from flask_restx import Namespace, Resource, fields
from flask import request

element_ns = Namespace("elements", description="Element operations")

element_ref_model = element_ns.model("ElementRef", {
    "id": fields.String(description="Element identifier"),
})

element_model = element_ns.model("Element", {
    "@type": fields.String(description="Element type"),
    "identifier": fields.String(description="Element identifier"),
    "name": fields.String(description="Element name"),
    "qualifiedName": fields.String(description="Qualified name"),
    "owner": fields.Nested(element_ref_model, allow_null=True, description="Owner element"),
    "project": fields.Nested(element_ref_model, allow_null=True, description="Parent project"),
})

element_input_model = element_ns.model("ElementInput", {
    "@type": fields.String(description="Element type", default="Element"),
    "identifier": fields.String(description="Element identifier"),
    "name": fields.String(description="Element name"),
    "qualifiedName": fields.String(description="Qualified name"),
    "owner": fields.Nested(element_ref_model, allow_null=True, description="Owner element"),
    "project": fields.Nested(element_ref_model, allow_null=True, description="Parent project"),
})


@element_ns.route("/")
class ElementList(Resource):
    @element_ns.marshal_list_with(element_model)
    def get(self):
        """List all elements"""
        from flask import current_app, request as flask_request
        store = current_app.config["store"]
        commit_id = flask_request.args.get("commit")
        elements = store.get_all_elements(commit_id=commit_id)
        return [e.to_dict() for e in elements]

    @element_ns.marshal_with(element_model)
    @element_ns.expect(element_input_model)
    def post(self):
        """Create a new element"""
        from flask import current_app
        from app.models.element import Element
        store = current_app.config["store"]
        data = request.get_json()
        element = Element.from_dict(data)
        store.add_element(element)
        return element.to_dict(), 201


@element_ns.route("/<element_id>")
class ElementDetail(Resource):
    @element_ns.doc(params={"element_id": "Element identifier"})
    def get(self, element_id):
        """Get an element by ID"""
        from flask import current_app, abort, request as flask_request
        store = current_app.config["store"]
        commit_id = flask_request.args.get("commit")
        element = store.get_element(element_id, commit_id=commit_id)
        if not element:
            abort(404, "Element not found")
        return element.to_dict()

    @element_ns.doc(params={"element_id": "Element identifier"})
    @element_ns.expect(element_input_model)
    def put(self, element_id):
        """Update an element"""
        from flask import current_app, abort
        store = current_app.config["store"]
        if not store.get_element(element_id):
            abort(404, "Element not found")
        data = request.get_json()
        element = store.get_element(element_id)
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
                element.owner_id = value.get("id") if value else None
            elif key == "project":
                element.project_id = value.get("id") if value else None
            else:
                element.data[key] = value
        store.update_element(element_id, element.to_dict(include_all=True))
        return element.to_dict()

    @element_ns.doc(params={"element_id": "Element identifier"})
    def delete(self, element_id):
        """Delete an element"""
        from flask import current_app, abort
        store = current_app.config["store"]
        if not store.delete_element(element_id):
            abort(404, "Element not found")
        return "", 204


@element_ns.route("/<element_id>/owned")
class OwnedElements(Resource):
    @element_ns.doc(params={"element_id": "Owner element identifier"})
    def get(self, element_id):
        """Get owned elements"""
        from flask import current_app, abort, request as flask_request
        store = current_app.config["store"]
        if not store.get_element(element_id):
            abort(404, "Element not found")
        recursive = flask_request.args.get("recursive", "false").lower() == "true"
        owned = store.get_owned_elements(element_id, recursive=recursive)
        return [e.to_dict() for e in owned]


@element_ns.route("/<element_id>/relationships")
class ElementRelationships(Resource):
    @element_ns.doc(params={"element_id": "Element identifier"})
    def get(self, element_id):
        """Get relationships for an element"""
        from flask import current_app, abort, request as flask_request
        store = current_app.config["store"]
        if not store.get_element(element_id):
            abort(404, "Element not found")
        direction = flask_request.args.get("direction", "both")
        relationships = store.get_relationships(element_id, direction=direction)
        return relationships
