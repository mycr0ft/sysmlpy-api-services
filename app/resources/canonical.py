"""Spec-canonical URL space: /projects/{pid}/commits/... and friends.

The OMG Systems Modeling API & Services nests everything under the
owning project + commit. These routes are registered as a plain Flask
blueprint (not flask_restx) so the paths appear EXACTLY as the spec
defines them — no namespace prefix, no marshal masking:

    GET    /api/projects/{pid}/commits
    POST   /api/projects/{pid}/commits
    GET    /api/projects/{pid}/commits/{cid}
    GET    /api/projects/{pid}/commits/{cid}/changes           (DataVersion)
    GET    /api/projects/{pid}/commits/{cid}/changes/{changeId}
    GET    /api/projects/{pid}/commits/{cid}/elements
    GET    /api/projects/{pid}/commits/{cid}/elements/{eid}
    GET    /api/projects/{pid}/commits/{cid}/elements/{eid}/projectUsage
    GET    /api/projects/{pid}/commits/{cid}/elements/{eid}/relationships
    GET    /api/projects/{pid}/commits/{cid}/roots
    GET/POST /api/projects/{pid}/branches[/{bid}]
    GET/POST /api/projects/{pid}/tags[/{tid}]
    GET/POST /api/projects/{pid}/queries[/{qid}[/results]]
    GET/POST /api/projects/{pid}/query-results

Flat aliases in commits.py/branches.py/... remain for old clients.
"""
from flask import Blueprint, abort, request

bp = Blueprint("canonical", __name__)


def _store():
    from flask import current_app
    return current_app.config["store"]


def _serialize(obj):
    return obj.to_dict() if hasattr(obj, "to_dict") else obj


def _commit_or_404(store, pid, cid):
    commit = store.get_commit(cid)
    if not commit or commit.project_id != pid:
        abort(404, "Commit not found")
    return commit


def _element_to_dict(node_data):
    """Node attrs -> spec EJSON element (full shape, no marshal mask)."""
    data = dict(node_data)
    data.setdefault("@type", "Element")
    data.setdefault("identifier", data.get("id"))
    return data


def _set_project_ref(data, project_id):
    ref = data.get("project") if isinstance(data.get("project"), dict) else {}
    ref["identifier"] = project_id
    data["project"] = ref


class DataVersionRecord:
    """Lightweight DataVersion: what a commit changed."""

    def __init__(self, commit_id, element_id, operation):
        self.commit_id = commit_id
        self.element_id = element_id
        self.operation = operation  # "create" | "update" | "delete"

    def to_dict(self):
        return {
            "@type": "DataVersion",
            "identifier": f"{self.commit_id}:{self.element_id}",
            "element": {"identifier": self.element_id},
            "operation": self.operation,
        }


# -- Commits -----------------------------------------------------------------


@bp.get("/projects/<project_id>/commits")
def list_commits(project_id):
    """Get all commits in the project (spec getCommits)"""
    return [_serialize(c) for c in _store().get_commits_by_project(project_id)]


@bp.post("/projects/<project_id>/commits")
def create_commit(project_id):
    """Create a commit in the project (spec createCommit)"""
    from app.models.lifecycle import Commit
    data = request.get_json(silent=True) or {}
    _set_project_ref(data, project_id)
    commit = Commit.from_dict(data)
    _store().add_commit(commit)
    return commit.to_dict(), 201


@bp.get("/projects/<project_id>/commits/<commit_id>")
def get_commit(project_id, commit_id):
    """Get a commit by project + id (spec getCommitById)"""
    return _commit_or_404(_store(), project_id, commit_id).to_dict()


@bp.get("/projects/<project_id>/commits/<commit_id>/changes")
def get_commit_changes(project_id, commit_id):
    """Get the DataVersion records of a commit (spec getCommitChange)"""
    store = _store()
    _commit_or_404(store, project_id, commit_id)
    return [
        DataVersionRecord(commit_id, node_id, attrs.get("_op", "create")).to_dict()
        for node_id, attrs in store.graph.nodes(data=True)
        if attrs.get("commit") == commit_id
    ]


@bp.get("/projects/<project_id>/commits/<commit_id>/changes/<change_id>")
def get_commit_change(project_id, commit_id, change_id):
    """Get one DataVersion record (spec getCommitChangeById)"""
    store = _store()
    _commit_or_404(store, project_id, commit_id)
    for node_id, attrs in store.graph.nodes(data=True):
        if attrs.get("commit") == commit_id:
            rec = DataVersionRecord(commit_id, node_id, attrs.get("_op", "create"))
            if rec.to_dict()["identifier"] == change_id:
                return rec.to_dict()
    abort(404, "Change not found")


# -- Elements (commit-scoped — the spec's core addressing scheme) ------------


@bp.get("/projects/<project_id>/commits/<commit_id>/elements")
def get_commit_elements(project_id, commit_id):
    """Get elements at a commit (spec getElements; excludeUsed honored)"""
    store = _store()
    _commit_or_404(store, project_id, commit_id)
    exclude_used = request.args.get("excludeUsed", "").lower() in ("1", "true")
    out = []
    for node_id, attrs in store.graph.nodes(data=True):
        if attrs.get("commit") != commit_id:
            continue
        if exclude_used and attrs.get("_used"):
            continue
        out.append(_element_to_dict(attrs))
    return out


@bp.get("/projects/<project_id>/commits/<commit_id>/elements/<element_id>")
def get_commit_element(project_id, commit_id, element_id):
    """Get one element at a commit (spec getElementById)"""
    store = _store()
    _commit_or_404(store, project_id, commit_id)
    attrs = store.graph.nodes.get(element_id)
    if not attrs or attrs.get("commit") != commit_id:
        abort(404, "Element not found")
    return _element_to_dict(attrs)


@bp.get("/projects/<project_id>/commits/<commit_id>/elements/<element_id>/projectUsage")
def get_commit_element_project_usage(project_id, commit_id, element_id):
    """Derived property projectUsage (spec)"""
    store = _store()
    _commit_or_404(store, project_id, commit_id)
    attrs = store.graph.nodes.get(element_id) or {}
    proj = attrs.get("project")
    pid = proj.get("identifier") if isinstance(proj, dict) else None
    if not pid:
        abort(404, "Element has no project usage")
    return {"projectUsage": {"identifier": pid}}


@bp.get("/projects/<project_id>/commits/<commit_id>/roots")
def get_commit_roots(project_id, commit_id):
    """Get root elements (no owner) at a commit (spec getRootElements)"""
    store = _store()
    _commit_or_404(store, project_id, commit_id)
    out = []
    for node_id, attrs in store.graph.nodes(data=True):
        if attrs.get("commit") != commit_id:
            continue
        owner = attrs.get("owner")
        oid = owner.get("identifier") or owner.get("id") if isinstance(owner, dict) else None
        # root = not owned by ANOTHER ELEMENT (project-owned packages are roots)
        if not oid or oid not in store.graph:
            out.append(_element_to_dict(attrs))
    return out


@bp.get("/projects/<project_id>/commits/<commit_id>/elements/<related_element_id>/relationships")
def get_commit_element_relationships(project_id, commit_id, related_element_id):
    """Relationships of an element at a commit (spec getRelationshipsByRelatedElement)"""
    store = _store()
    _commit_or_404(store, project_id, commit_id)
    if related_element_id not in store.graph:
        abort(404, "Element not found")
    direction = request.args.get("direction", "both")
    rels = []
    if direction in ("outgoing", "both"):
        for _, v, a in store.graph.out_edges(related_element_id, data=True):
            rels.append({"source": {"identifier": related_element_id},
                         "target": {"identifier": v},
                         "@type": a.get("type", "Relationship")})
    if direction in ("incoming", "both"):
        for u, _, a in store.graph.in_edges(related_element_id, data=True):
            rels.append({"source": {"identifier": u},
                         "target": {"identifier": related_element_id},
                         "@type": a.get("type", "Relationship")})
    return rels


# -- Branches / Tags (canonical nested) ---------------------------------------


@bp.get("/projects/<project_id>/branches")
def list_branches(project_id):
    """Get all branches in the project (spec getBranches)"""
    return [_serialize(b) for b in _store().get_branches_by_project(project_id)]


@bp.post("/projects/<project_id>/branches")
def create_branch(project_id):
    """Create a branch in the project (spec createBranch)"""
    from app.models.lifecycle import Branch
    data = request.get_json(silent=True) or {}
    _set_project_ref(data, project_id)
    branch = Branch.from_dict(data)
    _store().add_branch(branch)
    return branch.to_dict(), 201


@bp.get("/projects/<project_id>/branches/<branch_id>")
def get_branch(project_id, branch_id):
    """Get a branch by project + id (spec getBranchById)"""
    b = _store().get_branch(branch_id)
    if not b or b.project_id != project_id:
        abort(404, "Branch not found")
    return b.to_dict()


@bp.get("/projects/<project_id>/tags")
def list_tags(project_id):
    """Get all tags in the project (spec getTags)"""
    return [_serialize(t) for t in _store().get_tags_by_project(project_id)]


@bp.post("/projects/<project_id>/tags")
def create_tag(project_id):
    """Create a tag in the project (spec createTag)"""
    from app.models.lifecycle import Tag
    data = request.get_json(silent=True) or {}
    _set_project_ref(data, project_id)
    tag = Tag.from_dict(data)
    _store().add_tag(tag)
    return tag.to_dict(), 201


@bp.get("/projects/<project_id>/tags/<tag_id>")
def get_tag(project_id, tag_id):
    """Get a tag by project + id (spec getTagById)"""
    t = _store().get_tag(tag_id)
    if not t or t.project_id != project_id:
        abort(404, "Tag not found")
    return t.to_dict()


# -- Queries (saved Query objects + results, spec semantics) ------------------


@bp.get("/projects/<project_id>/queries")
def list_queries(project_id):
    """Get all saved queries in the project (spec getQueries)"""
    return [_serialize(q) for q in _store().queries.values() if q.project_id == project_id]


@bp.post("/projects/<project_id>/queries")
def create_query(project_id):
    """Create a saved query (spec createQuery: Query record w/ criteria)"""
    from app.models.lifecycle import SavedQuery
    data = request.get_json(silent=True) or {}
    q = SavedQuery.from_dict(data, project_id)
    _store().add_query(q)
    return q.to_dict(), 201


@bp.get("/projects/<project_id>/queries/<query_id>")
def get_query(project_id, query_id):
    """Get a saved query (spec getQueryById)"""
    q = _store().get_query(query_id)
    if not q or q.project_id != project_id:
        abort(404, "Query not found")
    return q.to_dict()


@bp.delete("/projects/<project_id>/queries/<query_id>")
def delete_query(project_id, query_id):
    """Delete a saved query (spec deleteQuery)"""
    if not _store().delete_query(query_id):
        abort(404, "Query not found")
    return "", 204


@bp.get("/projects/<project_id>/queries/<query_id>/results")
def get_query_results(project_id, query_id):
    """Execute a saved query (spec getQueryResultsById, ?commit= scoping)"""
    store = _store()
    q = store.get_query(query_id)
    if not q or q.project_id != project_id:
        abort(404, "Query not found")
    commit_id = request.args.get("commit")
    elements = store.query_elements(_criteria_from(q.criteria))
    if commit_id:
        elements = [e for e in elements
                    if store.graph.nodes.get(e.id, {}).get("commit") == commit_id]
    return [e.to_dict() for e in elements]


@bp.get("/projects/<project_id>/query-results")
def query_results_get(project_id):
    """Ad-hoc query via params (spec getQueryResultsByProjectIdQuery GET form)"""
    criteria = _criteria_from(dict(request.args.items()))
    return [e.to_dict() for e in _store().query_elements(criteria)]


@bp.post("/projects/<project_id>/query-results")
def query_results_post(project_id):
    """Ad-hoc query via criteria body (spec getQueryResultsByProjectIdQuery POST form)"""
    data = request.get_json(silent=True) or {}
    return [e.to_dict() for e in _store().query_elements(_criteria_from(data))]


def _criteria_from(data):
    criteria = {}
    f = data.get("filter")
    if isinstance(f, dict):
        criteria.update(f)
    for k in ("type", "@type", "name", "qualifiedName"):
        if k in data:
            criteria["@type" if k == "type" else k] = data[k]
    return criteria