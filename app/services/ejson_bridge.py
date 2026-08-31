"""Translate sysmlpy's ANTLR parse dicts into SysML v2 API EJSON structures.

sysmlpy's ``load_grammar_antlr`` produces nested dicts whose keys mirror the
metamodel (``ownedRelationship``, ``ownedRelatedElement``, ``declaredName``,
...).  This module flattens those dicts into the flat element-with-owner-
reference shape used by the SysML v2 REST API:

    {
        "@type": "PartUsage",
        "identifier": "<uuid>",
        "name": "wheel",
        "owner": {"identifier": "<uuid-of-parent>"},
        ...
    }

All functions are side-effect free with respect to the parse dict.
"""

import uuid


def _new_id():
    return str(uuid.uuid4())


def _is_node(node, *names):
    return isinstance(node, dict) and node.get("name") in names


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _find_first(node, *keys):
    """Depth-first search for the first non-empty key match in a subtree."""
    if not isinstance(node, dict):
        return None
    for key in keys:
        if node.get(key):
            return node.get(key)
    for value in node.values():
        for item in _as_list(value):
            found = _find_first(item, *keys)
            if found is not None:
                return found
    return None


def _qualified_name(node):
    if not isinstance(node, dict):
        return None
    names = node.get("names")
    if isinstance(names, list):
        return "::".join(str(n) for n in names)
    # FeatureType wraps the QualifiedName under 'type'
    inner = node.get("type")
    if isinstance(inner, dict):
        qn = _qualified_name(inner)
        if qn:
            return qn
    qn = node.get("qualifiedName") or node.get("declaredName")
    return str(qn) if qn else None


def _extract_literal(expr):
    """Find the first Literal* node value in an expression tree."""
    if not isinstance(expr, dict):
        return None
    name = expr.get("name", "")
    if name.startswith("Literal"):
        value = expr.get("value")
        if isinstance(value, str) and len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            return value[1:-1]
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.isdigit():
                return int(stripped)
            try:
                return float(stripped)
            except ValueError:
                return value
        return value
    for value in expr.values():
        for item in _as_list(value):
            got = _extract_literal(item)
            if got is not None:
                return got
    return None


def _declaration_chain(payload):
    """Descend `declaration` until the dict carrying `identification`."""
    decl = payload.get("declaration") if isinstance(payload, dict) else None
    while isinstance(decl, dict) and "identification" not in decl:
        decl = decl.get("declaration")
    return decl


def _prefix_flags(prefix, elem):
    """Copy isAbstract/isVariation/isIndividual/isReference from a prefix."""
    if not isinstance(prefix, dict):
        return
    basic = prefix.get("prefix") if isinstance(prefix.get("prefix"), dict) else prefix
    if isinstance(basic, dict):
        if basic.get("isAbstract"):
            elem["isAbstract"] = True
        if basic.get("isVariation"):
            elem["isVariation"] = True
        if basic.get("isReference"):
            elem["isReference"] = True
    if prefix.get("isIndividual"):
        elem["isIndividual"] = True


def _multiplicity_from_part(mp):
    """MultiplicityPart dict -> {'lower': x, 'upper': y} or None."""
    ranges = []
    for rel in _as_list(mp.get("ownedRelationship")):
        for item in _as_list(rel.get("ownedRelatedElement")):
            if _is_node(item, "MultiplicityRange"):
                bounds = []
                for m in _as_list(item.get("ownedRelationship")):
                    for related in _as_list(m.get("ownedRelatedElement")):
                        for sub in _as_list(related.get("ownedRelatedElement") if isinstance(related, dict) else None):
                            if isinstance(sub, dict):
                                lit = _extract_literal(sub)
                                if lit is not None:
                                    bounds.append(lit)
                if bounds:
                    ranges.append(bounds)
    if not ranges:
        return None
    if len(ranges) == 1:
        b = ranges[0]
        return {"lower": b[0], "upper": b[1] if len(b) > 1 else b[0]}
    if len(ranges) >= 2:
        return {"lower": ranges[0][0], "upper": ranges[-1][0]}
    return None


def _specialization_relationships(spec_part):
    """FeatureSpecializationPart -> (relationships, multiplicity)."""
    rels = []
    for spec in _as_list(spec_part.get("specialization")):
        if not isinstance(spec, dict):
            continue
        rel = spec.get("ownedRelationship")
        if isinstance(rel, dict):
            rel = [rel]
        for r in rel or []:
            if not isinstance(r, dict):
                continue
            rname = r.get("name")
            if rname == "Subsettings":
                for sub in _as_list(r.get("ownedRelationship")):
                    target = _qualified_name(sub.get("subsettedFeature") if isinstance(sub, dict) else None)
                    if target:
                        rels.append({"@type": "Subsetting", "subsettedFeature": target})
            elif rname == "Typings":
                tb = r.get("typedby")
                if isinstance(tb, dict):
                    for ft in _as_list(tb.get("ownedRelationship")):
                        if not _is_node(ft, "FeatureTyping"):
                            continue
                        for inner in _as_list(ft.get("ownedRelationship")):
                            target = _qualified_name(inner.get("type") if isinstance(inner, dict) else None)
                            if target:
                                rels.append({"@type": "FeatureTyping", "type": target})
            elif rname == "Redefinitions":
                for red in _as_list(r.get("ownedRelationship")):
                    target = _qualified_name(red.get("redefinedFeature") if isinstance(red, dict) else None)
                    if target:
                        rels.append({"@type": "Redefinition", "redefinedFeature": target})
    multiplicity = None
    if isinstance(spec_part.get("multiplicity"), dict):
        multiplicity = _multiplicity_from_part(spec_part["multiplicity"])
    return rels, multiplicity


def _subclassifications(decl):
    """DefinitionDeclaration.subclassificationpart -> list of supertypes."""
    scp = decl.get("subclassificationpart") if isinstance(decl, dict) else None
    out = []
    for rel in _as_list(scp.get("ownedRelationship") if isinstance(scp, dict) else None):
        target = _qualified_name(rel.get("superclassifier") if isinstance(rel, dict) else None)
        if target:
            out.append(target)
    return out


class EJSONConverter:
    """Converts a sysmlpy parse dict into flat EJSON element dicts."""

    def convert(self, parse_dict):
        self.elements = []
        self._convert_members(_as_list(parse_dict.get("ownedRelationship")), None)
        return self.elements

    def convert_text(self, source):
        from sysmlpy import load_grammar_antlr

        return self.convert(load_grammar_antlr(source))

    # -- members -----------------------------------------------------------

    def _convert_members(self, members, owner_id):
        for member in members:
            if not isinstance(member, dict):
                continue
            if member.get("name") == "Import":
                self._convert_import(member, owner_id)
                continue
            owned = member.get("ownedRelatedElement")
            for element in _as_list(owned):
                # DefinitionElement / UsageElement wrap the actual element
                wrapped = element.get("ownedRelatedElement") if _is_node(element, "DefinitionElement", "UsageElement") else element
                for inner in _as_list(wrapped):
                    self._convert_element(inner, owner_id)

    def _convert_import(self, member, owner_id):
        ident = member.get("identification") or {}
        # plain `import B::*;` is flat; `private import B::*;` nests everything
        # under ownedRelationship (a NamespaceImport node)
        source = member
        nested = member.get("ownedRelationship")
        if isinstance(nested, dict) and "Import" in str(nested.get("name", "")):
            source = nested
        elem = {
            "@type": "Import",
            "identifier": _new_id(),
            "name": ident.get("declaredName"),
        }
        if owner_id:
            elem["owner"] = {"identifier": owner_id}
        ns = source.get("namespace")
        if isinstance(ns, dict):
            qn = ns.get("namespaces")
            if qn is None:
                inner = ns.get("namespace")
                qn = inner.get("names") if isinstance(inner, dict) else None
            elem["importedNamespace"] = "::".join(qn) if isinstance(qn, list) else qn
            elem["isRecursive"] = bool(ns.get("isRecursive"))
        prefix = source.get("prefix")
        if isinstance(prefix, dict):
            vis = prefix.get("visibility")
            visval = vis.get("visibility") if isinstance(vis, dict) else None
            if visval:
                elem["visibility"] = str(visval)
        self.elements.append(elem)

    # -- elements ----------------------------------------------------------

    def _convert_element(self, element, owner_id):
        """Handle one concrete element payload.

        Shapes encountered (all dicts with 'name'):

        - Package / PartDefinition / ... : {declaration, body, [definition]}
        - OccurrenceUsageElement / NonOccurrenceUsageElement /
          BehaviorUsageElement: wrappers, ownedRelatedElement or
          ownedRelationship carries the concrete usage
        - concrete usages (PartUsage, AttributeUsage, ...):
          {usage: {declaration, completion}} or {declaration, body}
        """
        if not isinstance(element, dict):
            return
        etype = element.get("name")
        if etype is None:
            return

        # Unwrap the *Element layers
        if etype in ("OccurrenceUsageElement", "NonOccurrenceUsageElement"):
            for inner in _as_list(element.get("ownedRelatedElement")):
                self._convert_element(inner, owner_id)
            return
        if etype == "BehaviorUsageElement":
            ors = element.get("ownedRelationship")
            if isinstance(ors, dict) and "name" in ors:
                # single concrete usage directly attached
                self._convert_element(ors, owner_id)
                return
            for rel in _as_list(ors):
                owned = rel.get("ownedRelatedElement") if isinstance(rel, dict) else None
                for inner in _as_list(owned):
                    self._convert_element(inner, owner_id)
            return

        if etype in ("StructureUsageElement", "BehaviorUsageElement2"):
            for inner in _as_list(element.get("ownedRelatedElement")):
                self._convert_element(inner, owner_id)
            return

        # Comments / documentation
        if etype in ("AnnotatingElement",):
            for child in _as_list(element.get("ownedRelatedElement")):
                self._convert_annotating(child, owner_id)
            return
        if etype in ("CommentSysML", "Documentation"):
            self._emit_comment(element, etype, owner_id)
            return

        if etype in ("Package", "LibraryPackage"):
            self._convert_package(element, owner_id)
            return

        # Concrete usage metaclasses end with 'Usage' and carry 'usage'
        if etype.endswith("Usage") and "usage" in element:
            self._convert_usage(element, etype, owner_id)
            return

        # Concrete definition metaclasses end with 'Definition' and carry
        # either a 'definition' payload (part def, action def, ...) or a
        # direct declaration+body (enum def, attribute def, ...)
        if etype.endswith("Definition"):
            self._convert_definition(element, etype, owner_id)
            return

        # Behavior / occurrence usages arriving bare (declaration + body).
        # Skip empty anonymous artifacts (e.g. the phantom ref created by
        # `doc /* ... */` sugar).
        if etype in ("EnumeratedValue", "DefaultInterfaceEnd") or (etype.endswith("Usage") and "usage" not in element):
            if "usage" in element:
                self._convert_usage(
                    {"name": etype, "usage": element["usage"]},
                    "EnumeratedValue" if etype == "EnumeratedValue" else etype,
                    owner_id,
                )
                return
            decl = _declaration_chain(element) or {}
            if (decl.get("identification") or {}).get("declaredName") is None and not element.get("valuepart"):
                return
            self._convert_usage_shallow(element, etype, owner_id)
            return

    def _convert_package(self, element, owner_id):
        decl = element.get("declaration") or {}
        ident = decl.get("identification") or {}
        elem = {
            "@type": "Package",
            "identifier": _new_id(),
        }
        if ident.get("declaredShortName") is not None:
            elem["declaredShortName"] = ident["declaredShortName"]
        elem["name"] = ident.get("declaredName")
        if owner_id:
            elem["owner"] = {"identifier": owner_id}
        if element.get("isStandardLibrary"):
            elem["isStandardLibrary"] = True
        body = element.get("body")
        if isinstance(body, dict):
            self._convert_members(_as_list(body.get("ownedRelationship")), elem["identifier"])
        self.elements.append(elem)

    def _convert_definition(self, element, etype, owner_id):
        payload = element.get("definition") or {
            "declaration": element.get("declaration"),
            "body": element.get("body"),
        }
        decl = payload.get("declaration") or {}
        ident = decl.get("identification") or {}

        elem = {
            "@type": etype,
            "identifier": _new_id(),
        }
        if ident.get("declaredShortName") is not None:
            elem["declaredShortName"] = ident["declaredShortName"]
        elem["name"] = ident.get("declaredName")
        if owner_id:
            elem["owner"] = {"identifier": owner_id}
        _prefix_flags(element.get("prefix"), elem)

        for target in _subclassifications(decl):
            elem.setdefault("ownedRelationship", []).append(
                {"@type": "Subclassification", "superclassifier": target}
            )

        body = payload.get("body")
        if isinstance(body, dict):
            members = _as_list(body.get("ownedRelationship"))
            for item in _as_list(body.get("ownedRelatedElement")):
                for rel in _as_list(item.get("ownedRelationship") if isinstance(item, dict) else None):
                    members.append(rel)
            self._convert_definition_body(members, elem["identifier"])

        self.elements.append(elem)

    def _convert_definition_body(self, members, owner_id):
        for member in members:
            if not isinstance(member, dict):
                continue
            mname = member.get("name", "")
            for element in _as_list(member.get("ownedRelatedElement")):
                inner = element
                if _is_node(inner, "InterfaceOccurrenceUsageElement") and isinstance(inner.get("element"), dict):
                    self._convert_element(inner.get("element"), owner_id)
                    continue
                # nested wrap layers
                wrapped = (
                    inner.get("ownedRelatedElement")
                    if _is_node(inner, "DefinitionElement", "UsageElement",
                                "OccurrenceUsageElement", "NonOccurrenceUsageElement",
                                "BehaviorUsageMember")
                    else inner
                )
                for node in _as_list(wrapped):
                    self._convert_element(node, owner_id)

    def _convert_usage(self, element, etype, owner_id):
        """PartUsage/AttributeUsage/... carrying {'usage': {...}}."""
        payload = element.get("usage") or {}
        decl = _declaration_chain(payload) or {}
        ident = decl.get("identification") or {}

        elem = {
            "@type": etype,
            "identifier": _new_id(),
        }
        if ident.get("declaredShortName") is not None:
            elem["declaredShortName"] = ident["declaredShortName"]
        elem["name"] = ident.get("declaredName")
        if owner_id:
            elem["owner"] = {"identifier": owner_id}
        _prefix_flags(element.get("prefix"), elem)

        self._apply_usage_extras(payload, decl, elem)
        self._emit(elem)

    def _convert_usage_shallow(self, element, etype, owner_id):
        """Usage arriving directly (declaration [+ valuepart] + body)."""
        payload = element
        decl = _declaration_chain(payload) or {}
        ident = decl.get("identification") or {}
        elem = {
            "@type": etype,
            "identifier": _new_id(),
            "name": ident.get("declaredName"),
        }
        if ident.get("declaredShortName") is not None:
            elem["declaredShortName"] = ident["declaredShortName"]
        if owner_id:
            elem["owner"] = {"identifier": owner_id}
        _prefix_flags(element.get("prefix"), elem)
        # feature direction ('in x', 'out y')
        direction = (element.get("prefix") or {}).get("direction") if isinstance(element.get("prefix"), dict) else None
        if isinstance(direction, dict):
            if direction.get("in"):
                elem["direction"] = "in"
            elif direction.get("out"):
                elem["direction"] = "out"
            elif direction.get("inout"):
                elem["direction"] = "inout"
        # interface ends carry isEnd
        if element.get("isEnd"):
            elem["isEnd"] = True
        self._apply_usage_extras(payload, decl, elem)
        self._emit(elem)

    def _apply_usage_extras(self, payload, decl, elem):
        # specializations live on FeatureDeclaration.specialization
        feat = decl
        while isinstance(feat, dict) and feat.get("name") != "FeatureDeclaration":
            nxt = feat.get("declaration")
            if not isinstance(nxt, dict):
                break
            feat = nxt
        if isinstance(feat, dict) and feat.get("name") == "FeatureDeclaration" and isinstance(feat.get("specialization"), dict):
            rels, multiplicity = _specialization_relationships(feat["specialization"])
            for rel in rels:
                elem.setdefault("ownedRelationship", []).append(rel)
            if multiplicity is not None:
                elem["multiplicity"] = multiplicity

        # values
        completion = payload.get("completion")
        if isinstance(completion, dict):
            vp = completion.get("valuepart")
            if isinstance(vp, dict):
                values = []
                for fv in _as_list(vp.get("ownedRelationship")):
                    if not _is_node(fv, "FeatureValue"):
                        continue
                    owned = fv.get("ownedRelatedElement")
                    expr = None
                    if isinstance(owned, dict):
                        expr = owned.get("expression")
                    values.append(
                        {
                            "value": _extract_literal(expr),
                            "isInitial": bool(fv.get("isInitial")),
                            "isDefault": bool(fv.get("isDefault")),
                            "isEqual": bool(fv.get("isEqual")),
                        }
                    )
                if values:
                    elem["values"] = values

        # nested body
        body = payload.get("body") if isinstance(payload, dict) else None
        if isinstance(body, dict):
            inner = body.get("body") or body
            members = _as_list(inner.get("ownedRelationship"))
            for item in _as_list(inner.get("ownedRelatedElement")):
                for rel in _as_list(item.get("ownedRelationship") if isinstance(item, dict) else None):
                    members.append(rel)
            # StateDefBody nests members under part.item
            part = inner.get("part")
            if isinstance(part, dict):
                for item in _as_list(part.get("item")):
                    members.extend(_as_list(item.get("ownedRelationship") if isinstance(item, dict) else None))
            # ActionBody nests members under items
            for item in _as_list(inner.get("items")):
                members.extend(_as_list(item.get("ownedRelationship") if isinstance(item, dict) else None))
            self._convert_definition_body(members, elem["identifier"])

    def _convert_annotating(self, element, owner_id):
        self._emit_comment(element, element.get("name"), owner_id)

    def _emit_comment(self, element, etype, owner_id):
        ident = element.get("identification") if isinstance(element.get("identification"), dict) else {}
        elem = {
            "@type": "Comment",
            "identifier": _new_id(),
            "name": ident.get("declaredName"),
            "body": element.get("body"),
        }
        if ident.get("declaredShortName") is not None:
            elem["declaredShortName"] = ident["declaredShortName"]
        if owner_id:
            elem["owner"] = {"identifier": owner_id}
        if etype == "Documentation":
            elem["isDocumentation"] = True
        self.elements.append(elem)

    def _emit(self, elem):
        self.elements.append(elem)


def convert_parse_dict(parse_dict):
    """Parse dict -> list of EJSON element dicts."""
    return EJSONConverter().convert(parse_dict)


def convert_source(source):
    """SysMLv2 text -> list of EJSON element dicts."""
    return EJSONConverter().convert_text(source)