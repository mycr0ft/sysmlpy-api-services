"""Conformance tests vs OMG Systems Modeling API & Services v1.0.

Each test names the alignment item from docs/api-alignment.md it pins.
These define the "aligned behaviors" standing suite: green = claim
backed, red = regression.
"""
import pytest
from app.app import create_app


@pytest.fixture
def client():
    app = create_app("testing")
    app.testing = True
    with app.test_client() as c:
        yield c


def _mk_project(client, name="Conf"):
    r = client.post("/api/projects/", json={"name": name})
    assert r.status_code == 201
    return r.get_json()


def _import_model(client, pid, src):
    r = client.post(f"/api/model/projects/{pid}/model.sysml",
                    data=src, content_type="text/plain")
    assert r.status_code == 201, r.get_data(as_text=True)
    return r


SRC = ("package Vehicles { part def Vehicle { part engine1 : Engine; "
       "attribute mass : Real; } part def Engine { attribute power : Real; "
       "port p : P; } port def P; }")


class TestEJSONShape:
    """Item: EJSON element shape + reference normalization (gap 4)."""

    def test_element_has_type_identifier(self, client):
        pid = _mk_project(client)["id"]
        els = _import_model(client, pid, SRC).get_json()
        pkg = next(e for e in els if e["@type"] == "Package")
        assert pkg["identifier"]

    def test_owner_ref_is_identifier_key(self, client):
        pid = _mk_project(client)["id"]
        els = _import_model(client, pid, SRC).get_json()
        engine1 = next(e for e in els if e.get("name") == "engine1")
        assert engine1["owner"]["identifier"] == next(
            e["identifier"] for e in els if e.get("name") == "Vehicle")

    def test_qualified_names_chain(self, client):
        pid = _mk_project(client)["id"]
        els = _import_model(client, pid, SRC).get_json()
        engine1 = next(e for e in els if e.get("name") == "engine1")
        assert "Vehicle" in (engine1.get("qualifiedName") or "")

    def test_relationship_payload_survives(self, client):
        """Gap 6: FeatureTyping/Redefinition must not be dropped."""
        pid = _mk_project(client)["id"]
        src = ("package P { part def Base; part def Engine; "
               "part e1 : Engine subsets Base; }")
        els = _import_model(client, pid, src).get_json()
        e1 = next(e for e in els if e.get("name") == "e1")
        rels = e1.get("ownedRelationship") or []
        kinds = {r.get("@type") for r in rels}
        assert "FeatureTyping" in kinds, e1
        assert "Subsetting" in kinds, e1
        ft = next(r for r in rels if r["@type"] == "FeatureTyping")
        assert "Engine" in str(ft.get("type", ""))


class TestCommitScoping:
    """Item A/C: canonical nested routes + commit-scoped elements."""

    def test_canonical_commits_list(self, client):
        pid = _mk_project(client)["id"]
        r = client.get(f"/api/projects/{pid}/commits")
        assert r.status_code == 200
        assert len(r.get_json()) >= 1

    def test_canonical_create_commit(self, client):
        pid = _mk_project(client)["id"]
        r = client.post(f"/api/projects/{pid}/commits",
                        json={"description": "checkpoint"})
        assert r.status_code == 201
        assert r.get_json()["owningProject"]["identifier"] == pid

    def test_import_creates_commit_and_scopes_elements(self, client):
        pid = _mk_project(client)["id"]
        r = _import_model(client, pid, SRC)
        cid = r.headers["X-SysML-Commit"]
        els = client.get(f"/api/projects/{pid}/commits/{cid}/elements")
        assert els.status_code == 200
        names = {e.get("name") for e in els.get_json()}
        assert {"Vehicles", "Vehicle", "Engine", "engine1"} <= names

    def test_commit_detail_scoped_to_project(self, client):
        pid = _mk_project(client)["id"]
        cid = _import_model(client, pid, SRC).headers["X-SysML-Commit"]
        assert client.get(f"/api/projects/{pid}/commits/{cid}").status_code == 200
        other = _mk_project(client, name="Other")["id"]
        assert client.get(f"/api/projects/{other}/commits/{cid}").status_code == 404

    def test_changes_data_version_records(self, client):
        """Gap 2: commits must carry DataVersion change records."""
        pid = _mk_project(client)["id"]
        cid = _import_model(client, pid, SRC).headers["X-SysML-Commit"]
        changes = client.get(f"/api/projects/{pid}/commits/{cid}/changes")
        assert changes.status_code == 200
        recs = changes.get_json()
        assert len(recs) >= 8
        assert all(r["@type"] == "DataVersion" for r in recs)
        assert any(r["element"]["identifier"] for r in recs)

    def test_one_change_by_id(self, client):
        pid = _mk_project(client)["id"]
        cid = _import_model(client, pid, SRC).headers["X-SysML-Commit"]
        recs = client.get(f"/api/projects/{pid}/commits/{cid}/changes").get_json()
        cid_change = recs[0]["identifier"]
        r = client.get(f"/api/projects/{pid}/commits/{cid}/changes/{cid_change}")
        assert r.status_code == 200

    def test_roots_endpoint(self, client):
        """Gap 5: roots."""
        pid = _mk_project(client)["id"]
        cid = _import_model(client, pid, SRC).headers["X-SysML-Commit"]
        roots = client.get(f"/api/projects/{pid}/commits/{cid}/roots")
        assert roots.status_code == 200
        roots = roots.get_json()
        assert len(roots) == 1 and roots[0]["name"] == "Vehicles"

    def test_commit_is_immutable(self, client):
        """Item F: no PUT/DELETE on commits (spec: immutable)."""
        pid = _mk_project(client)["id"]
        cid = _import_model(client, pid, SRC).headers["X-SysML-Commit"]
        assert client.put(f"/api/commits/{cid}", json={}).status_code == 405
        assert client.delete(f"/api/commits/{cid}").status_code == 405


class TestProjectRecord:
    """Spec Project record: defaultBranch, commits/branches members."""

    def test_new_project_has_default_branch_and_commit(self, client):
        d = _mk_project(client)
        assert d["defaultBranch"]["name"] == "main"
        assert d["defaultBranch"]["head"]["identifier"]
        pid = d["id"]
        detail = client.get(f"/api/projects/{pid}").get_json()
        assert detail["commits"]
        assert detail["branches"]

    def test_project_members_in_detail(self, client):
        pid = _mk_project(client)["id"]
        d = client.get(f"/api/projects/{pid}").get_json()
        assert d["commits"] and d["branches"]


class TestQueries:
    """Gap 5: saved Query objects + results, one-shot query-results."""

    def test_saved_query_roundtrip(self, client):
        pid = _mk_project(client)["id"]
        _import_model(client, pid, SRC)
        r = client.post(f"/api/projects/{pid}/queries", json={
            "name": "parts", "criteria": {"type": "PartDefinition"}})
        assert r.status_code == 201
        qid = r.get_json()["identifier"]
        results = client.get(f"/api/projects/{pid}/queries/{qid}/results")
        assert results.status_code == 200
        names = {e.get("name") for e in results.get_json()}
        assert {"Vehicle", "Engine"} <= names

    def test_one_shot_query_results(self, client):
        pid = _mk_project(client)["id"]
        _import_model(client, pid, SRC)
        r = client.post(f"/api/projects/{pid}/query-results",
                        json={"filter": {"type": "PartUsage"}})
        assert r.status_code == 200
        assert any(e.get("name") == "engine1" for e in r.get_json())

    def test_query_by_type_alias(self, client):
        pid = _mk_project(client)["id"]
        _import_model(client, pid, SRC)
        r = client.get("/api/query/type/PartDefinition")
        assert r.status_code == 200
        assert {e["name"] for e in r.get_json()} >= {"Vehicle", "Engine"}


class TestBranchesTagsCanonical:
    def test_canonical_branches(self, client):
        pid = _mk_project(client)["id"]
        # project starts with main
        bl = client.get(f"/api/projects/{pid}/branches").get_json()
        assert any(b["name"] == "main" for b in bl)
        r = client.post(f"/api/projects/{pid}/branches", json={"name": "dev"})
        assert r.status_code == 201
        bid = r.get_json()["identifier"]
        assert client.get(f"/api/projects/{pid}/branches/{bid}").status_code == 200

    def test_canonical_tags(self, client):
        pid = _mk_project(client)["id"]
        cid = _import_model(client, pid, SRC).headers["X-SysML-Commit"]
        r = client.post(f"/api/projects/{pid}/tags",
                        json={"name": "SRR", "commit": {"identifier": cid}})
        assert r.status_code == 201
        assert r.get_json()["commit"]["identifier"] == cid
        tid = r.get_json()["identifier"]
        assert client.get(f"/api/projects/{pid}/tags/{tid}").status_code == 200


class TestLegacyAliases:
    """Flat routes keep working for existing clients."""

    def test_flat_element_roundtrip(self, client):
        r = client.post("/api/elements/", json={"@type": "PartUsage", "name": "X"})
        assert r.status_code == 201
        eid = r.get_json()["identifier"]
        assert client.get(f"/api/elements/{eid}").status_code == 200

    def test_flat_commits(self, client):
        pid = _mk_project(client)["id"]
        r = client.get(f"/api/commits/project/{pid}")
        assert r.status_code == 200  # alias remains reachable (GET only, no POST)