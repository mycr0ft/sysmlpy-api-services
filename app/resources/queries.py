from flask_restx import Namespace, Resource, fields
from flask import request

query_ns = Namespace("query", description="Query operations")

query_input_model = query_ns.model("QueryInput", {
    "commit": fields.Nested(query_ns.model("QueryCommitRef", {
        "id": fields.String(description="Commit identifier"),
    }), allow_null=True, description="Commit to query"),
    "filter": fields.Raw(description="Filter criteria", example={"type": "PartUsage", "name": "myPart"}),
})


@query_ns.route("/")
class QueryExecute(Resource):
    @query_ns.expect(query_input_model)
    def post(self):
        """Execute a query against elements"""
        from flask import current_app
        store = current_app.config["store"]
        data = request.get_json()
        filters = data.get("filter", {})
        elements = store.query_elements(filters)
        return [e.to_dict() for e in elements]


@query_ns.route("/type/<element_type>")
class QueryByType(Resource):
    @query_ns.doc(params={"element_type": "Element type to query"})
    def get(self, element_type):
        """Query elements by type"""
        from flask import current_app
        store = current_app.config["store"]
        elements = store.query_elements({"type": element_type})
        return [e.to_dict() for e in elements]


@query_ns.route("/name/<element_name>")
class QueryByName(Resource):
    @query_ns.doc(params={"element_name": "Element name to query"})
    def get(self, element_name):
        """Query elements by name"""
        from flask import current_app
        store = current_app.config["store"]
        elements = store.query_elements({"name": element_name})
        return [e.to_dict() for e in elements]
