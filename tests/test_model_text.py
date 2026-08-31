import pytest
from app.app import create_app
from app.services.ejson_bridge import convert_source


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        yield client


SAMPLE = """
package VehicleDomain {
    part def Vehicle :> Base {
        attribute mass = 1500;
        port def Pwr;
        part wheel[4];
        doc /* Vehicle documentation */;
    }
    part v1 : Vehicle;
    requirement r1;
    private import Base::*;
    state s1;
    action a1 { in inp : Item1; out out1; }
    enum def E1 { a; b; }
}
"""


class TestEJSONBridge:
    def testconverts_package(self):
        elements = convert_source("package V { }")
        package = next(e for e in elements if e["@type"] == "Package")
        assert package["name"] == "V"

    def test_part_definition_with_subclassification(self):
        elements = convert_source("package V { part def Vehicle :> Base; }")
        vehicle = next(e for e in elements if e.get("name") == "Vehicle")
        assert vehicle["@type"] == "PartDefinition"
        assert vehicle["ownedRelationship"][0]["@type"] == "Subclassification"
        assert vehicle["ownedRelationship"][0]["superclassifier"] == "Base"

    def test_usage_with_typing_and_subsetting(self):
        elements = convert_source("package V { part v1 subsets v0 : Vehicle; }")
        v1 = next(e for e in elements if e.get("name") == "v1")
        rels = v1["ownedRelationship"]
        assert {"@type": "FeatureTyping", "type": "Vehicle"} in rels
        assert {"@type": "Subsetting", "subsettedFeature": "v0"} in rels

    def test_attribute_value_and_multiplicity(self):
        elements = convert_source("package V { attribute m = 1500; part w[4]; }")
        m = next(e for e in elements if e.get("name") == "m")
        assert m["values"][0]["value"] == 1500
        w = next(e for e in elements if e.get("name") == "w")
        assert w["multiplicity"] == {"lower": 4, "upper": 4}

    def test_owner_links(self):
        elements = convert_source("package V { part def P { part wheel; } }")
        by_name = {e["name"]: e for e in elements}
        wheel = by_name["wheel"]
        assert wheel["owner"]["identifier"] == by_name["P"]["identifier"]

    def test_owners_and_flags(self):
        elements = convert_source("package V { abstract part def AP; ref part rp; }")
        ap = next(e for e in elements if e.get("name") == "AP")
        assert ap["isAbstract"] is True
        rp = next(e for e in elements if e.get("name") == "rp")
        assert rp["isReference"] is True

    def test_string_literal_value(self):
        elements = convert_source('package V { attribute s = "hi"; }')
        s = next(e for e in elements if e.get("name") == "s")
        assert s["values"][0]["value"] == "hi"


class TestModelTextIngest:
    def test_ingest_creates_elements(self, client):
        project = client.post("/api/projects/", json={"name": "IngestTest"}).get_json()
        response = client.post(
            f"/api/model/projects/{project['id']}/model.sysml",
            data="package V { part def Vehicle; part v1 : Vehicle; }",
            content_type="text/plain",
        )
        assert response.status_code == 201
        created = response.get_json()
        names = {e["name"] for e in created}
        assert {"V", "Vehicle", "v1"} <= names

    def test_ingest_requires_project(self, client):
        response = client.post(
            "/api/model/projects/does-not-exist/model.sysml",
            data="package V { }",
            content_type="text/plain",
        )
        assert response.status_code == 404

    def test_ingest_invalid_syntax(self, client):
        project = client.post("/api/projects/", json={"name": "Bad"}).get_json()
        response = client.post(
            f"/api/model/projects/{project['id']}/model.sysml",
            data="package V { part def ",
            content_type="text/plain",
        )
        assert response.status_code == 422

    def test_ingest_empty_body(self, client):
        project = client.post("/api/projects/", json={"name": "Empty"}).get_json()
        response = client.post(
            f"/api/model/projects/{project['id']}/model.sysml",
            data="   ",
            content_type="text/plain",
        )
        assert response.status_code == 400

    def test_ingested_elements_are_queryable(self, client):
        project = client.post("/api/projects/", json={"name": "Q"}).get_json()
        client.post(
            f"/api/model/projects/{project['id']}/model.sysml",
            data="package V { part def Vehicle { part wheel; } }",
            content_type="text/plain",
        )
        listing = client.get("/api/elements/").get_json()
        names = {e["name"] for e in listing}
        assert "wheel" in names


class TestModelTextExport:
    def test_round_trip(self, client):
        project = client.post("/api/projects/", json={"name": "RT"}).get_json()
        pid = project["id"]
        client.post(
            f"/api/model/projects/{pid}/model.sysml",
            data=SAMPLE,
            content_type="text/plain",
        )
        export = client.get(f"/api/model/projects/{pid}/model.sysml")
        assert export.status_code == 200
        assert export.headers["Content-Type"].startswith("text/plain")
        text = export.get_data(as_text=True)
        assert "package VehicleDomain" in text
        assert "part def Vehicle :> Base" in text
        assert "attribute mass = 1500" in text
        assert "part wheel[4]" in text
        assert "part v1 : Vehicle" in text
        assert "state s1" in text

    def test_export_text_reparses(self, client):
        project = client.post("/api/projects/", json={"name": "Reparse"}).get_json()
        pid = project["id"]
        client.post(
            f"/api/model/projects/{pid}/model.sysml",
            data=SAMPLE,
            content_type="text/plain",
        )
        text = client.get(f"/api/model/projects/{pid}/model.sysml").get_data(as_text=True)
        # export must be valid SysML again
        elements = convert_source(text)
        types = {e["@type"] for e in elements}
        assert "Package" in types
        assert "PartDefinition" in types

    def test_ingest_export_round_trip(self, client):
        first = client.post("/api/projects/", json={"name": "A"}).get_json()
        second = client.post("/api/projects/", json={"name": "B"}).get_json()
        client.post(
            f"/api/model/projects/{first['id']}/model.sysml",
            data=SAMPLE,
            content_type="text/plain",
        )
        text = client.get(f"/api/model/projects/{first['id']}/model.sysml").get_data(as_text=True)
        response = client.post(
            f"/api/model/projects/{second['id']}/model.sysml",
            data=text,
            content_type="text/plain",
        )
        assert response.status_code == 201
        again = client.get(f"/api/model/projects/{second['id']}/model.sysml").get_data(as_text=True)
        assert again == text