import uuid
from datetime import datetime, timezone


class Project:
    def __init__(self, name=None, project_id=None, description=None):
        self.id = project_id or str(uuid.uuid4())
        self.name = name or "Unnamed Project"
        self.description = description or ""
        self.created = datetime.now(timezone.utc).isoformat()
        self.updated = self.created

    def to_dict(self):
        return {
            "@type": "Project",
            "id": self.id,
            "identifier": self.id,
            "name": self.name,
            "description": self.description,
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, data):
        project = cls(
            name=data.get("name"),
            project_id=data.get("id"),
            description=data.get("description"),
        )
        if "created" in data:
            project.created = data["created"]
        if "updated" in data:
            project.updated = data["updated"]
        return project


class Commit:
    def __init__(self, project_id=None, commit_id=None, description=None):
        self.id = commit_id or str(uuid.uuid4())
        self.project_id = project_id
        self.description = description or ""
        self.created = datetime.now(timezone.utc).isoformat()
        self.previous = None

    def to_dict(self):
        result = {
            "@type": "Commit",
            "id": self.id,
            "identifier": self.id,
            "owningProject": {"identifier": self.project_id} if self.project_id else None,
            "project": {"identifier": self.project_id} if self.project_id else None,
            "description": self.description,
            "created": self.created,
        }
        if self.previous:
            result["previous"] = {"identifier": self.previous}
        return result

    @classmethod
    def from_dict(cls, data):
        project = data.get("project")
        commit = cls(
            project_id=(project.get("identifier") or project.get("id")) if isinstance(project, dict) else None,
            commit_id=data.get("id"),
            description=data.get("description"),
        )
        if "previous" in data and data["previous"]:
            commit.previous = data["previous"].get("id") if isinstance(data["previous"], dict) else data["previous"]
        if "created" in data:
            commit.created = data["created"]
        return commit


class Branch:
    def __init__(self, project_id=None, branch_id=None, name=None, head=None):
        self.id = branch_id or str(uuid.uuid4())
        self.project_id = project_id
        self.name = name or "main"
        self.head = head

    def to_dict(self):
        result = {
            "@type": "Branch",
            "id": self.id,
            "identifier": self.id,
            "owningProject": {"identifier": self.project_id} if self.project_id else None,
            "project": {"identifier": self.project_id} if self.project_id else None,
            "name": self.name,
        }
        if self.head:
            result["head"] = {"identifier": self.head}
        return result

    @classmethod
    def from_dict(cls, data):
        project = data.get("project")
        branch = cls(
            project_id=(project.get("identifier") or project.get("id")) if isinstance(project, dict) else None,
            branch_id=data.get("id"),
            name=data.get("name"),
            head=data.get("head", {}).get("identifier") if data.get("head") else None,
        )
        return branch


class Tag:
    def __init__(self, project_id=None, tag_id=None, name=None, commit=None):
        self.id = tag_id or str(uuid.uuid4())
        self.project_id = project_id
        self.name = name or ""
        self.commit = commit

    def to_dict(self):
        result = {
            "@type": "Tag",
            "id": self.id,
            "identifier": self.id,
            "owningProject": {"identifier": self.project_id} if self.project_id else None,
            "project": {"identifier": self.project_id} if self.project_id else None,
            "name": self.name,
        }
        if self.commit:
            result["commit"] = {"identifier": self.commit}
        return result

    @classmethod
    def from_dict(cls, data):
        project = data.get("project")
        commit = data.get("commit")
        tag = cls(
            project_id=(project.get("identifier") or project.get("id")) if isinstance(project, dict) else None,
            tag_id=data.get("id"),
            name=data.get("name"),
            commit=(commit.get("identifier") or commit.get("id")) if isinstance(commit, dict) else None,
        )
        return tag


class SavedQuery:
    """Spec Query record: a named, saved criteria set owned by a Project."""

    def __init__(self, project_id=None, query_id=None, name=None, criteria=None, description=None):
        self.id = query_id or str(uuid.uuid4())
        self.project_id = project_id
        self.name = name or "query"
        self.criteria = criteria or {}
        self.description = description or ""

    def to_dict(self):
        return {
            "@type": "Query",
            "id": self.id,
            "identifier": self.id,
            "owningProject": {"identifier": self.project_id} if self.project_id else None,
            "name": self.name,
            "description": self.description,
            "criteria": self.criteria,
        }

    @classmethod
    def from_dict(cls, data, project_id=None):
        return cls(
            project_id=project_id,
            query_id=data.get("id"),
            name=data.get("name"),
            criteria=data.get("criteria") or data.get("filter") or {},
            description=data.get("description"),
        )
