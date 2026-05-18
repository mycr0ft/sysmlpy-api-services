from flask_restx import Namespace, Resource, fields

schema_ns = Namespace("schema", description="Schema operations")


@schema_ns.route("/")
class SchemaList(Resource):
    def get(self):
        """Get the SysMLv2 metamodel schema"""
        from app.models.element import Element
        return {
            "types": Element.SYSML_TYPES,
            "description": "SysMLv2 metamodel types supported by this API",
        }


@schema_ns.route("/<type_name>")
class SchemaType(Resource):
    @schema_ns.doc(params={"type_name": "Metamodel type name"})
    def get(self, type_name):
        """Get schema for a specific type"""
        from app.models.element import Element
        if type_name not in Element.SYSML_TYPES:
            return {"message": f"Type '{type_name}' not found"}, 404
        return {
            "type": type_name,
            "properties": {
                "@type": {"type": "string", "description": "Element type"},
                "identifier": {"type": "string", "description": "Unique identifier"},
                "name": {"type": "string", "description": "Element name"},
                "qualifiedName": {"type": "string", "description": "Fully qualified name"},
                "owner": {"type": "object", "description": "Owner element reference"},
                "project": {"type": "object", "description": "Project reference"},
            },
        }
