# SysMLv2 API Services (Python)

Python implementation of the SysMLv2 REST API Services, similar to the [Java reference implementation](https://github.com/Systems-Modeling/SysML-v2-API-Services), built with Flask-RESTX and [sysmlpy](https://github.com/mycr0ft/sysmlpy).

## Features

- REST API for SysMLv2 modeling operations
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
- `PUT /api/commits/<id>` - Update a commit
- `DELETE /api/commits/<id>` - Delete a commit
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

## Example Usage

### Create a Project
```bash
curl -X POST http://<host>:5000/api/projects/ \
  -H "Content-Type: application/json" \
  -d '{"name": "MyModel", "description": "A sample SysMLv2 model"}'
```

### Create an Element
```bash
curl -X POST http://<host>:5000/api/elements/ \
  -H "Content-Type: application/json" \
  -d '{
    "@type": "PartUsage",
    "name": "Engine",
    "project": {"id": "<project-id>"}
  }'
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
│   │   ├── lifecycle.py    # Project, Commit, Branch, Tag models
│   │   └── element.py      # Element model
│   ├── resources/
│   │   ├── projects.py     # Project API endpoints
│   │   ├── commits.py      # Commit API endpoints
│   │   ├── branches.py     # Branch API endpoints
│   │   ├── tags.py         # Tag API endpoints
│   │   ├── elements.py     # Element API endpoints
│   │   ├── relationships.py # Relationship API endpoints
│   │   ├── queries.py      # Query API endpoints
│   │   └── schema.py       # Schema API endpoints
│   ├── storage/
│   │   └── graph_store.py  # NetworkX graph storage backend
│   └── services/           # Business logic (future)
├── tests/                  # Test suite
├── pyproject.toml          # Poetry project configuration
├── run.py                  # Entry point
└── README.md
```

## License

MIT License
