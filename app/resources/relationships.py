from flask_restx import Namespace, Resource, fields
from flask import request

relationship_ns = Namespace("relationships", description="Relationship operations")

element_ref_model = relationship_ns.model("RelationshipElementRef", {
    "id": fields.String(description="Element identifier"),
})

relationship_model = relationship_ns.model("Relationship", {
    "id": fields.String(description="Relationship identifier"),
    "type": fields.String(description="Relationship type"),
    "source": fields.Nested(element_ref_model, description="Source element"),
    "target": fields.Nested(element_ref_model, description="Target element"),
})

relationship_input_model = relationship_ns.model("RelationshipInput", {
    "type": fields.String(description="Relationship type", default="relationship"),
    "source": fields.Nested(element_ref_model, required=True, description="Source element"),
    "target": fields.Nested(element_ref_model, required=True, description="Target element"),
})


@relationship_ns.route("/")
class RelationshipList(Resource):
    @relationship_ns.marshal_list_with(relationship_model)
    def get(self):
        """List all relationships"""
        from flask import current_app
        store = current_app.config["store"]
        relationships = store.get_relationships()
        return relationships

    @relationship_ns.expect(relationship_input_model)
    def post(self):
        """Create a new relationship"""
        from flask import current_app
        store = current_app.config["store"]
        data = request.get_json()
        source_id = data.get("source", {}).get("id")
        target_id = data.get("target", {}).get("id")
        rel_type = data.get("type", "relationship")
        if not source_id or not target_id:
            return {"message": "source and target are required"}, 400
        relationship = store.add_relationship(source_id, target_id, rel_type)
        return relationship, 201


@relationship_ns.route("/target/<target_id>")
class RelationshipsByTarget(Resource):
    @relationship_ns.doc(params={"target_id": "Target element identifier"})
    def get(self, target_id):
        """Get relationships by target element"""
        from flask import current_app
        store = current_app.config["store"]
        relationships = store.get_relationships_by_target(target_id)
        return relationships
