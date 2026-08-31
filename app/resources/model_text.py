"""SysML text import/export endpoints backed by the sysmlpy parser.

POST /projects/<project_id>/model.sysml   parse SysML text -> create elements
GET  /projects/<project_id>/model.sysml   export stored elements as SysML text
"""

from flask_restx import Namespace, Resource
from flask import request, current_app, abort

from app.models.element import Element
from app.services.ejson_bridge import convert_source

model_ns = Namespace("model", description="SysML text model import/export")


def _store():
    return current_app.config["store"]


def _require_project(project_id):
    store = _store()
    project = store.get_project(project_id)
    if not project:
        abort(404, "Project not found")
    return project


def _qualified_name(element_id, store, cache):
    """Build the qualified name by walking owner links."""
    if element_id in cache:
        return cache[element_id]
    element = store.get_element(element_id)
    if element is None:
        cache[element_id] = None
        return None
    owner_id = element.owner_id
    if owner_id:
        parent_qn = _qualified_name(owner_id, store, cache)
        name = ".".join(p for p in (parent_qn, element.name) if p)
    else:
        name = element.name
    cache[element_id] = name
    return name


@model_ns.route("/projects/<project_id>/model.sysml")
class ProjectModelText(Resource):
    @model_ns.doc(params={"project_id": "Project identifier"})
    def get(self, project_id):
        """Export a project's elements as SysMLv2 text."""
        from flask import Response

        _require_project(project_id)
        store = _store()
        text = ModelTextBuilder(store).build(project_id)
        return Response(text, 200, {"Content-Type": "text/plain; charset=utf-8"})

    def post(self, project_id):
        """Ingest SysMLv2 text: parse and store the elements in the project."""
        _require_project(project_id)
        source = request.get_data(as_text=True)
        if not source or not source.strip():
            return {"message": "Request body must contain SysML text"}, 400

        try:
            elements = convert_source(source)
        except Exception as exc:  # parse errors surface as 422
            return {"message": f"Failed to parse SysML: {exc}"}, 422

        store = _store()
        by_id = {}
        for data in elements:
            # normalize reference keys for the existing store ("id" style)
            for ref_key in ("owner", "project"):
                ref = data.get(ref_key)
                if isinstance(ref, dict) and "identifier" in ref and "id" not in ref:
                    data[ref_key] = {"id": ref["identifier"]}
            # root package belongs to the project
            if data.get("@type") == "Package" and not data.get("owner"):
                data["owner"] = {"id": project_id}
            element = Element.from_dict(data)
            element.project_id = project_id
            if element.owner_id:
                owner = by_id.get(element.owner_id) or store.get_element(element.owner_id)
                if owner is not None and getattr(owner, "qualified_name", None):
                    element.qualified_name = f"{owner.qualified_name}::{element.name}"
                elif element.name:
                    element.qualified_name = element.name
            store.add_element(element)
            by_id[element.id] = element
        return [
            e.to_dict() for e in by_id.values()
        ], 201


class ModelTextBuilder:
    """Serializes stored elements back into SysML text."""

    def __init__(self, store):
        self.store = store
        self.cache = {}

    def build(self, project_id):
        elements = [e for e in self.store.get_all_elements() if e.project_id == project_id]
        if not elements:
            return ""
        return self._render_package(elements)

    def _render_package(self, elements):
        package = next((e for e in elements if e.type == "Package"), None)
        name = package.name if package and package.name else "Model"
        children = [e for e in elements if package and e.owner_id == package.id]
        lines = [f"package {name} {{"]
        for child in children:
            lines.extend(self._render_element(child))
        lines.append("}")
        return "\n".join(lines)

    def _render_element(self, element, indent="   "):
        lines = []
        name = element.name or ""
        rels = element.get_data("ownedRelationship", [])
        typ = element.type

        if typ == "Package":
            children = [e for e in self.store.get_owned_elements(element.id) if e.project_id == element.project_id]
            lines.append(f"{indent}package {name} {{")
            for child in children:
                lines.extend(self._render_element(child, indent + "   "))
            lines.append(f"{indent}}}")
            return lines

        # keyword mapping
        keyword = {
            "PartDefinition": "part def", "PartUsage": "part",
            "AttributeDefinition": "attribute def", "AttributeUsage": "attribute",
            "PortDefinition": "port def", "PortUsage": "port",
            "ActionDefinition": "action def", "ActionUsage": "action",
            "ItemDefinition": "item def", "ItemUsage": "item",
            "RequirementDefinition": "requirement def", "RequirementUsage": "requirement",
            "ConstraintDefinition": "constraint def", "ConstraintUsage": "constraint",
            "EnumerationDefinition": "enum def",
            "InterfaceDefinition": "interface def", "InterfaceUsage": "interface",
            "StateDefinition": "state def", "StateUsage": "state",
            "ConnectionDefinition": "connection def", "ConnectionUsage": "connection",
            "UseCaseDefinition": "use case def", "UseCaseUsage": "use case",
            "CalculationDefinition": "calc def", "CalculationUsage": "calc",
            "DefaultReferenceUsage": "feature",
            "Comment": "comment",
            "EnumeratedValue": "",
        }.get(typ)

        if typ == "Comment":
            body = element.get_data("body", "")
            if element.get_data("isDocumentation"):
                lines.append(f"{indent}doc {body}")
            else:
                label = f"{name} " if name else ""
                lines.append(f"{indent}comment {label}{body}")
            return lines
        if typ == "Import":
            ns = element.get_data("importedNamespace")
            # the parser only accepts imports with a visibility prefix
            visibility = (element.get_data("visibility") or "private").lower()
            if ns:
                recursion = "::**" if element.get_data("isRecursive") else "::*"
                lines.append(f"{indent}{visibility} import {ns}{recursion};")
            else:
                lines.append(f"{indent}{visibility} import {name};")
            return lines

        if typ == "EnumeratedValue":
            lines.append(f"{indent}{name};")
            return lines

        if keyword is None:
            # unknown types render as a comment so text stays parseable
            lines.append(f"{indent}// {typ} {name}".rstrip())
            return lines

        # type references / subset relationships
        suffix = ""
        for rel in rels:
            if rel.get("@type") == "FeatureTyping":
                suffix += f" : {rel.get('type')}"
            elif rel.get("@type") == "Subsetting":
                suffix += f" subsets {rel.get('subsettedFeature')}"
            elif rel.get("@type") == "Subclassification":
                suffix += f" :> {rel.get('superclassifier')}"

        mult = element.get_data("multiplicity")
        if mult:
            lower, upper = mult.get("lower"), mult.get("upper")
            suffix += f"[{lower}]" if lower == upper else f"[{lower}..{upper}]"

        values = element.get_data("values", [])
        stmt = f"{indent}{keyword} {name}".rstrip()
        direction = element.get_data("direction")
        if direction:
            # `in x` / `out x` replaces the feature keyword entirely
            stmt = stmt.replace(f"{keyword} ", f"{direction} ", 1)
        stmt += suffix
        if values and values[0].get("value") is not None:
            stmt += f" = {values[0].get('value')}"
        if not stmt.endswith(";"):
            has_children = self._has_children(element)
            if has_children:
                stmt += " {"
            else:
                stmt += ";"
        lines.append(stmt)

        if self._has_children(element):
            for child in self._children(element):
                lines.extend(self._render_element(child, indent + "   "))
            lines.append(f"{indent}}}")
        return lines

    def _has_children(self, element):
        owned = self.store.get_owned_elements(element.id)
        return len([e for e in owned if e.project_id == element.project_id]) > 0

    def _children(self, element):
        return [e for e in self.store.get_owned_elements(element.id) if e.project_id == element.project_id]