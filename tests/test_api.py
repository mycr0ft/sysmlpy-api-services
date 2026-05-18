import pytest
from app.app import create_app


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        yield client


class TestProjects:
    def test_create_project(self, client):
        response = client.post("/api/projects/", json={
            "name": "TestProject",
            "description": "A test project",
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "TestProject"

    def test_list_projects(self, client):
        client.post("/api/projects/", json={"name": "Project1"})
        client.post("/api/projects/", json={"name": "Project2"})
        response = client.get("/api/projects/")
        assert response.status_code == 200
        assert len(response.get_json()) == 2

    def test_get_project(self, client):
        create_resp = client.post("/api/projects/", json={"name": "GetTest"})
        project_id = create_resp.get_json()["id"]
        response = client.get(f"/api/projects/{project_id}")
        assert response.status_code == 200
        assert response.get_json()["name"] == "GetTest"

    def test_delete_project(self, client):
        create_resp = client.post("/api/projects/", json={"name": "DeleteTest"})
        project_id = create_resp.get_json()["id"]
        response = client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 204
        response = client.get(f"/api/projects/{project_id}")
        assert response.status_code == 404


class TestElements:
    def test_create_element(self, client):
        response = client.post("/api/elements/", json={
            "@type": "PartUsage",
            "name": "Engine",
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["@type"] == "PartUsage"
        assert data["name"] == "Engine"

    def test_list_elements(self, client):
        client.post("/api/elements/", json={"@type": "PartUsage", "name": "Part1"})
        client.post("/api/elements/", json={"@type": "PartUsage", "name": "Part2"})
        response = client.get("/api/elements/")
        assert response.status_code == 200
        assert len(response.get_json()) == 2

    def test_get_element(self, client):
        create_resp = client.post("/api/elements/", json={"@type": "ActionUsage", "name": "TestAction"})
        element_id = create_resp.get_json()["identifier"]
        response = client.get(f"/api/elements/{element_id}")
        assert response.status_code == 200
        assert response.get_json()["name"] == "TestAction"


class TestRelationships:
    def test_create_relationship(self, client):
        source_resp = client.post("/api/elements/", json={"name": "Source"})
        target_resp = client.post("/api/elements/", json={"name": "Target"})
        source_id = source_resp.get_json()["identifier"]
        target_id = target_resp.get_json()["identifier"]

        response = client.post("/api/relationships/", json={
            "type": "Generalization",
            "source": {"id": source_id},
            "target": {"id": target_id},
        })
        assert response.status_code == 201

    def test_get_relationships_by_target(self, client):
        source_resp = client.post("/api/elements/", json={"name": "Source2"})
        target_resp = client.post("/api/elements/", json={"name": "Target2"})
        source_id = source_resp.get_json()["identifier"]
        target_id = target_resp.get_json()["identifier"]

        client.post("/api/relationships/", json={
            "type": "Dependency",
            "source": {"id": source_id},
            "target": {"id": target_id},
        })

        response = client.get(f"/api/relationships/target/{target_id}")
        assert response.status_code == 200
        assert len(response.get_json()) == 1


class TestSchema:
    def test_get_schema(self, client):
        response = client.get("/api/schema/")
        assert response.status_code == 200
        assert "types" in response.get_json()

    def test_get_schema_type(self, client):
        response = client.get("/api/schema/PartUsage")
        assert response.status_code == 200
        assert response.get_json()["type"] == "PartUsage"


class TestHealth:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.get_json()["status"] == "healthy"
