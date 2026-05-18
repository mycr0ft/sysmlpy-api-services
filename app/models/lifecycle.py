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
            "id": self.id,
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
            "id": self.id,
            "project": {"id": self.project_id} if self.project_id else None,
            "description": self.description,
            "created": self.created,
        }
        if self.previous:
            result["previous"] = {"id": self.previous}
        return result

    @classmethod
    def from_dict(cls, data):
        commit = cls(
            project_id=data.get("project", {}).get("id") if data.get("project") else None,
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
            "id": self.id,
            "project": {"id": self.project_id} if self.project_id else None,
            "name": self.name,
        }
        if self.head:
            result["head"] = {"id": self.head}
        return result

    @classmethod
    def from_dict(cls, data):
        branch = cls(
            project_id=data.get("project", {}).get("id") if data.get("project") else None,
            branch_id=data.get("id"),
            name=data.get("name"),
            head=data.get("head", {}).get("id") if data.get("head") else None,
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
            "id": self.id,
            "project": {"id": self.project_id} if self.project_id else None,
            "name": self.name,
        }
        if self.commit:
            result["commit"] = {"id": self.commit}
        return result

    @classmethod
    def from_dict(cls, data):
        tag = cls(
            project_id=data.get("project", {}).get("id") if data.get("project") else None,
            tag_id=data.get("id"),
            name=data.get("name"),
            commit=data.get("commit", {}).get("id") if data.get("commit") else None,
        )
        return tag
