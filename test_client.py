#!/usr/bin/env python
"""Test client for SysMLv2 API Services.

Usage:
    python test_client.py [--host HOST] [--port PORT]
"""
import argparse
import json
import sys
import urllib.request
import urllib.error


class SysMLv2Client:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def _request(self, method, path, data=None):
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                if resp.status == 204:
                    return None
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            print(f"  ERROR {e.code}: {e.read().decode()}")
            return None

    def get(self, path):
        return self._request("GET", path)

    def post(self, path, data):
        return self._request("POST", path, data)

    def put(self, path, data):
        return self._request("PUT", path, data)

    def delete(self, path):
        return self._request("DELETE", path)


def run_tests(client):
    print("=" * 60)
    print("SysMLv2 API Test Client")
    print("=" * 60)

    # 1. Health check
    print("\n[1] Health Check")
    resp = client.get("/health")
    print(f"  GET /health -> {resp}")
    assert resp and resp.get("status") == "healthy"

    # 2. Create Project
    print("\n[2] Create Project")
    project = client.post("/api/projects/", {"name": "MyModel", "description": "Test model"})
    print(f"  POST /api/projects/ -> {project}")
    assert project and "id" in project
    project_id = project["id"]

    # 3. Get Project
    print("\n[3] Get Project")
    project = client.get(f"/api/projects/{project_id}")
    print(f"  GET /api/projects/{project_id} -> {project}")
    assert project and project["name"] == "MyModel"

    # 4. List Projects
    print("\n[4] List Projects")
    projects = client.get("/api/projects/")
    print(f"  GET /api/projects/ -> {len(projects)} project(s)")
    assert len(projects) >= 1

    # 5. Create Elements
    print("\n[5] Create Elements")
    source = client.post("/api/elements/", {"@type": "PartDefinition", "name": "Vehicle"})
    print(f"  POST PartDefinition 'Vehicle' -> {source}")
    assert source and "identifier" in source
    source_id = source["identifier"]

    target = client.post("/api/elements/", {"@type": "PartDefinition", "name": "Engine"})
    print(f"  POST PartDefinition 'Engine' -> {target}")
    assert target and "identifier" in target
    target_id = target["identifier"]

    child = client.post("/api/elements/", {
        "@type": "PartUsage",
        "name": "engine1",
        "owner": {"id": source_id},
    })
    print(f"  POST PartUsage 'engine1' (owned by Vehicle) -> {child}")

    # 6. Get Element
    print("\n[6] Get Element")
    element = client.get(f"/api/elements/{source_id}")
    print(f"  GET /api/elements/{source_id} -> {element}")
    assert element and element["name"] == "Vehicle"

    # 7. List Elements
    print("\n[7] List Elements")
    elements = client.get("/api/elements/")
    print(f"  GET /api/elements/ -> {len(elements)} element(s)")
    assert len(elements) >= 3

    # 8. Get Owned Elements
    print("\n[8] Get Owned Elements")
    owned = client.get(f"/api/elements/{source_id}/owned")
    print(f"  GET /api/elements/{source_id}/owned -> {len(owned)} owned element(s)")
    assert len(owned) >= 1

    # 9. Create Relationship
    print("\n[9] Create Relationship")
    rel = client.post("/api/relationships/", {
        "type": "Generalization",
        "source": {"id": target_id},
        "target": {"id": source_id},
    })
    print(f"  POST relationship (Engine -> Vehicle) -> {rel}")
    assert rel and rel["type"] == "Generalization"

    # 10. Get Relationships by Target
    print("\n[10] Get Relationships by Target")
    rels = client.get(f"/api/relationships/target/{source_id}")
    print(f"  GET /api/relationships/target/{source_id} -> {len(rels)} relationship(s)")
    assert len(rels) >= 1

    # 11. Create Commit
    print("\n[11] Create Commit")
    commit = client.post("/api/commits/", {
        "project": {"id": project_id},
        "description": "Initial commit",
    })
    print(f"  POST /api/commits/ -> {commit}")
    assert commit and "id" in commit
    commit_id = commit["id"]

    # 12. Create Branch
    print("\n[12] Create Branch")
    branch = client.post("/api/branches/", {
        "project": {"id": project_id},
        "name": "main",
        "head": {"id": commit_id},
    })
    print(f"  POST /api/branches/ -> {branch}")
    assert branch and branch["name"] == "main"

    # 13. Create Tag
    print("\n[13] Create Tag")
    tag = client.post("/api/tags/", {
        "project": {"id": project_id},
        "name": "v1.0",
        "commit": {"id": commit_id},
    })
    print(f"  POST /api/tags/ -> {tag}")
    assert tag and tag["name"] == "v1.0"

    # 14. Query by Type
    print("\n[14] Query by Type")
    results = client.get("/api/query/type/PartDefinition")
    print(f"  GET /api/query/type/PartDefinition -> {len(results)} result(s)")
    assert len(results) >= 2

    # 15. Query by Name
    print("\n[15] Query by Name")
    results = client.get("/api/query/name/Vehicle")
    print(f"  GET /api/query/name/Vehicle -> {len(results)} result(s)")
    assert len(results) >= 1

    # 16. Get Schema
    print("\n[16] Get Schema")
    schema = client.get("/api/schema/")
    print(f"  GET /api/schema/ -> {len(schema.get('types', []))} types")
    assert "types" in schema

    # 17. Update Element
    print("\n[17] Update Element")
    updated = client.put(f"/api/elements/{source_id}", {"name": "VehicleUpdated"})
    print(f"  PUT /api/elements/{source_id} -> {updated}")
    assert updated and updated["name"] == "VehicleUpdated"

    # 18. Delete Element
    print("\n[18] Delete Element")
    client.delete(f"/api/elements/{target_id}")
    print(f"  DELETE /api/elements/{target_id} -> 204")
    deleted = client.get(f"/api/elements/{target_id}")
    assert deleted is None

    # 19. List Commits for Project
    print("\n[19] List Commits for Project")
    commits = client.get(f"/api/commits/project/{project_id}")
    print(f"  GET /api/commits/project/{project_id} -> {len(commits)} commit(s)")
    assert len(commits) >= 1

    # 20. List Branches for Project
    print("\n[20] List Branches for Project")
    branches = client.get(f"/api/branches/project/{project_id}")
    print(f"  GET /api/branches/project/{project_id} -> {len(branches)} branch(es)")
    assert len(branches) >= 1

    # 21. List Tags for Project
    print("\n[21] List Tags for Project")
    tags = client.get(f"/api/tags/project/{project_id}")
    print(f"  GET /api/tags/project/{project_id} -> {len(tags)} tag(s)")
    assert len(tags) >= 1

    # 22. Delete Project
    print("\n[22] Delete Project")
    client.delete(f"/api/projects/{project_id}")
    print(f"  DELETE /api/projects/{project_id} -> 204")

    print("\n" + "=" * 60)
    print("All 22 tests passed!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="SysMLv2 API Test Client")
    parser.add_argument("--host", default="localhost", help="API host (default: localhost)")
    parser.add_argument("--port", default="5000", help="API port (default: 5000)")
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"
    print(f"Connecting to {base_url}...")
    client = SysMLv2Client(base_url)

    try:
        run_tests(client)
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
