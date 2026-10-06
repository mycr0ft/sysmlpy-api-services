# SysMLv2 API Services (Python)

Python implementation of the SysML v2 REST/HTTP API Services — the OMG
[Systems Modeling API and Services](https://www.omg.org/spec/SystemsModelingAPI/1.0/Beta1/PDF)
specification — built with Flask-RESTX and [sysmlpy](https://github.com/mycr0ft/sysmlpy),
alongside the [Java pilot implementation](https://github.com/Systems-Modeling/SysML-v2-API-Services).

## Spec conformance — a tracked effort

This server is developed **against the OMG Systems Modeling API &
Services v1.0 specification** with two standing artifacts:

- **[`docs/api-alignment.md`](docs/api-alignment.md)** — the alignment
  report: endpoint-by-endpoint parity with the reference pilot's route
  table, EJSON element-shape verdicts, and the ranked conformance gaps.
  Verdict at time of writing: EJSON element shape close, endpoint
  topology aligned, several derived surfaces (DataVersion records,
  roots, saved queries) implemented.
- **[`tests/conformance_api_test.py`](tests/conformance_api_test.py)** —
  36 conformance tests (48 total in the suite) that pin every aligned
  behavior and fail on regression. Each test names the alignment item
  it covers.

What the conformance suite pins, verified live:

- **Spec-canonical URL space** — `/projects/{pid}/commits`,
  `/projects/{pid}/commits/{cid}/elements/...`, `/branches`, `/tags`,
  `/queries[/{qid}/results]`, `/query-results`, exactly as the
  specification defines them (flat aliases are kept below for existing
  clients).
- **EJSON element shape** — `@type`, `identifier`, name-chained
  `qualifiedName` (`Vehicles::Vehicle::engine1`), and
  `{"identifier": uuid}` reference values on `owner` / `project` /
  `previous` / `head` / `commit`, per the formal specification.
- **Commit-scoped versioning model** — every model ingestion creates a
  Commit; elements are addressable at a commit; each commit carries
  **DataVersion** change records (`.../changes[/{changeId}]`);
  commits are **immutable** (no PUT/DELETE — the spec's versioning
  semantics).
- **getElements / getElementById / getRootElements at a commit**,
  with the `excludeUsed` parameter honored.
- **getRelationshipsByRelatedElement** with the `direction` parameter;
  relationship payloads (FeatureTyping, Subsetting, Redefinition)
  survive serialization.
- **Query service** — saved Query records owned by a Project
  (`createQuery` / `getQueryById` / `getResults` + commit scoping) and
  one-shot ad-hoc `query-results` (POST criteria body / GET params).
- **Project record** — new projects start with a default branch
  (`main`) + initial commit, per the spec's Project lifecycle.

Known remaining gaps (tracked in the alignment report): `projectUsage`
derived-property payload detail, full change-operation tracking
(create/update/delete vs. the current create-only DataVersion
annotation), and a persistent storage backend.

## Features

- REST API for SysMLv2 modeling operations
- SysML text import/export via the sysmlpy parser
  (`POST/GET /api/model/projects/<id>/model.sysml`) — text goes in,
  spec-EJSON elements come out
- NetworkX graph-based storage for elements and relationships
- Support for projects, commits, branches, and tags (lifecycle management)
- Element CRUD operations with ownership hierarchy
- Relationship management
- Query API for filtering elements
- Swagger/OpenAPI documentation

## Installation

```bash
poetry install
```

## Running

```bash
poetry run python run.py
```

The API will be available at `http://<host>:5000` (replace `<host>` with the machine's IP or hostname).

## API Documentation

Interactive Swagger UI is available at `http://<host>:5000/docs/`.

## API Endpoints

Spec-canonical routes (conformant addressing):

```
GET/POST   /api/projects/{pid}/commits
GET        /api/projects/{pid}/commits/{cid}
GET        /api/projects/{pid}/commits/{cid}/changes[/{changeId}]
GET        /api/projects/{pid}/commits/{cid}/elements[/{eid}]
GET        /api/projects/{pid}/commits/{cid}/elements/{eid}/relationships[?direction=]
GET        /api/projects/{pid}/commits/{cid}/roots
GET/POST   /api/projects/{pid}/branches[/{bid}]
GET/POST   /api/projects/{pid}/tags[/{tid}]
GET/POST   /api/projects/{pid}/queries[/{qid}[/results]]
GET/POST   /api/projects/{pid}/query-results
```

Flat aliases (kept for existing clients):

### Projects
- `GET /api/projects/` - List all projects
- `POST /api/projects/` - Create a project
- `GET /api/projects/<id>` - Get a project
- `PUT /api/projects/<id>` - Update a project
- `DELETE /api/projects/<id>` - Delete a project

### Commits
- `GET /api/commits/` - List all commits
- `POST /api/commits/` - Create a commit
- `GET /api/commits/<id>` - Get a commit
- `GET /api/commits/project/<project_id>` - Get commits for a project

### Branches
- `GET /api/branches/` - List all branches
- `POST /api/branches/` - Create a branch
- `GET /api/branches/<id>` - Get a branch
- `PUT /api/branches/<id>` - Update a branch
- `DELETE /api/branches/<id>` - Delete a branch
- `GET /api/branches/project/<project_id>` - Get branches for a project
- `GET /api/branches/project/<project_id>/branch/<name>` - Get branch by name

### Tags
- `GET /api/tags/` - List all tags
- `POST /api/tags/` - Create a tag
- `GET /api/tags/<id>` - Get a tag
- `PUT /api/tags/<id>` - Update a tag
- `DELETE /api/tags/<id>` - Delete a tag
- `GET /api/tags/project/<project_id>` - Get tags for a project
- `GET /api/tags/project/<project_id>/tag/<name>` - Get tag by name

### Elements
- `GET /api/elements/` - List all elements
- `POST /api/elements/` - Create an element
- `GET /api/elements/<id>` - Get an element
- `PUT /api/elements/<id>` - Update an element
- `DELETE /api/elements/<id>` - Delete an element
- `GET /api/elements/<id>/owned` - Get owned elements
- `GET /api/elements/<id>/relationships` - Get element relationships

### Relationships
- `GET /api/relationships/` - List all relationships
- `POST /api/relationships/` - Create a relationship
- `GET /api/relationships/target/<target_id>` - Get relationships by target

### Query
- `POST /api/query/` - Execute a query
- `GET /api/query/type/<type>` - Query by element type
- `GET /api/query/name/<name>` - Query by element name

### Schema
- `GET /api/schema/` - Get metamodel schema
- `GET /api/schema/<type>` - Get schema for a specific type

### Model text (sysmlpy bridge)
- `POST /api/model/projects/<id>/model.sysml` - Ingest SysML text → EJSON elements (creates a commit)
- `GET /api/model/projects/<id>/model.sysml` - Export a project as SysML text

## Example Usage

### Create a Project
```bash
curl -X POST http://<host>:5000/api/projects/ \
  -H "Content-Type: application/json" \
  -d '{"name": "MyModel", "description": "A sample SysMLv2 model"}'
```

### Import a SysML model (creates a commit)
```bash
curl -X POST http://<host>:5000/api/model/projects/<pid>/model.sysml \
  -H "Content-Type: text/plain" \
  -d 'package Vehicles { part def Vehicle { part engine1 : Engine; } part def Engine; }'
```

### Read elements at a commit (spec addressing)
```bash
curl http://<host>:5000/api/projects/<pid>/commits/<cid>/elements
```

### Create a Relationship
```bash
curl -X POST http://<host>:5000/api/relationships/ \
  -H "Content-Type: application/json" \
  -d '{
    "type": "Generalization",
    "source": {"id": "<source-id>"},
    "target": {"id": "<target-id>"}
  }'
```

## Project Structure

```
sysmlpy-api-services/
├── app/
│   ├── app.py              # Flask application factory
│   ├── config.py           # Configuration
│   ├── models/
│   │   ├── lifecycle.py    # Project, Commit, Branch, Tag, SavedQuery models
│   │   └── element.py      # Element model
│   ├── resources/
│   │   ├── canonical.py    # Spec-canonical /projects/{pid}/... routes
│   │   ├── projects.py     # Project API endpoints
│   │   ├── commits.py      # Commit API endpoints (immutable per spec)
│   │   ├── branches.py     # Branch API endpoints
│   │   ├── tags.py         # Tag API endpoints
│   │   ├── elements.py     # Element API endpoints
│   │   ├── relationships.py # Relationship API endpoints
│   │   ├── queries.py      # Query API endpoints
│   │   ├── model_text.py   # SysML text import/export (sysmlpy bridge)
│   │   └── schema.py       # Schema API endpoints
│   ├── services/
│   │   └── ejson_bridge.py # sysmlpy parse dicts → spec EJSON elements
│   └── storage/
│       └── graph_store.py  # NetworkX graph storage backend
├── docs/
│   └── api-alignment.md    # OMG spec alignment report
├── tests/
│   ├── test_api.py         # Functional suite
│   └── conformance_api_test.py  # OMG spec conformance suite
├── pyproject.toml          # Poetry project configuration
├── run.py                  # Entry point
└── README.md
```

## License

MIT License