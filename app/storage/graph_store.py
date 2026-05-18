import networkx as nx


class GraphStore:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.commits = {}
        self.projects = {}
        self.branches = {}
        self.tags = {}

    def add_element(self, element, commit_id=None):
        node_data = element.to_dict(include_all=True)
        if commit_id:
            node_data["commit"] = commit_id
        self.graph.add_node(element.id, **node_data)
        return element

    def get_element(self, element_id, commit_id=None):
        if element_id not in self.graph:
            return None
        node_data = self.graph.nodes[element_id]
        if commit_id and node_data.get("commit") != commit_id:
            return None
        from app.models.element import Element
        element = Element(
            element_id=node_data.get("identifier"),
            type=node_data.get("@type", "Element"),
            name=node_data.get("name"),
            qualified_name=node_data.get("qualifiedName"),
            owner_id=node_data.get("owner", {}).get("id") if node_data.get("owner") else None,
            project_id=node_data.get("project", {}).get("id") if node_data.get("project") else None,
        )
        for key, value in node_data.items():
            if key not in ("@type", "identifier", "name", "qualifiedName", "owner", "project", "commit"):
                element.data[key] = value
        return element

    def get_all_elements(self, commit_id=None):
        elements = []
        from app.models.element import Element
        for node_id, node_data in self.graph.nodes(data=True):
            if commit_id and node_data.get("commit") != commit_id:
                continue
            element = Element(
                element_id=node_data.get("identifier"),
                type=node_data.get("@type", "Element"),
                name=node_data.get("name"),
                qualified_name=node_data.get("qualifiedName"),
                owner_id=node_data.get("owner", {}).get("id") if node_data.get("owner") else None,
                project_id=node_data.get("project", {}).get("id") if node_data.get("project") else None,
            )
            for key, value in node_data.items():
                if key not in ("@type", "identifier", "name", "qualifiedName", "owner", "project", "commit"):
                    element.data[key] = value
            elements.append(element)
        return elements

    def update_element(self, element_id, updates, commit_id=None):
        if element_id not in self.graph:
            return None
        node_data = dict(self.graph.nodes[element_id])
        node_data.update(updates)
        if commit_id:
            node_data["commit"] = commit_id
        self.graph.add_node(element_id, **node_data)
        return self.get_element(element_id, commit_id)

    def delete_element(self, element_id):
        if element_id not in self.graph:
            return False
        self.graph.remove_node(element_id)
        return True

    def add_relationship(self, source_id, target_id, rel_type="relationship", **attrs):
        self.graph.add_edge(source_id, target_id, type=rel_type, **attrs)
        return {"source": source_id, "target": target_id, "type": rel_type}

    def get_relationships(self, element_id=None, direction="both"):
        relationships = []
        if element_id is None:
            for u, v, attrs in self.graph.edges(data=True):
                relationships.append({
                    "source": u,
                    "target": v,
                    "type": attrs.get("type", "relationship"),
                })
        elif direction == "outgoing":
            for _, v, attrs in self.graph.out_edges(element_id, data=True):
                relationships.append({
                    "source": element_id,
                    "target": v,
                    "type": attrs.get("type", "relationship"),
                })
        elif direction == "incoming":
            for u, _, attrs in self.graph.in_edges(element_id, data=True):
                relationships.append({
                    "source": u,
                    "target": element_id,
                    "type": attrs.get("type", "relationship"),
                })
        else:
            for u, v, attrs in self.graph.edges(element_id, data=True):
                relationships.append({
                    "source": u,
                    "target": v,
                    "type": attrs.get("type", "relationship"),
                })
        return relationships

    def get_relationships_by_target(self, target_id):
        relationships = []
        for u, _, attrs in self.graph.in_edges(target_id, data=True):
            relationships.append({
                "source": u,
                "target": target_id,
                "type": attrs.get("type", "relationship"),
            })
        return relationships

    def get_owned_elements(self, owner_id, recursive=False):
        owned = []
        for node_id, node_data in self.graph.nodes(data=True):
            owner = node_data.get("owner")
            if owner and owner.get("id") == owner_id:
                from app.models.element import Element
                element = Element(
                    element_id=node_data.get("identifier"),
                    type=node_data.get("@type", "Element"),
                    name=node_data.get("name"),
                    qualified_name=node_data.get("qualifiedName"),
                    owner_id=owner_id,
                    project_id=node_data.get("project", {}).get("id") if node_data.get("project") else None,
                )
                for key, value in node_data.items():
                    if key not in ("@type", "identifier", "name", "qualifiedName", "owner", "project"):
                        element.data[key] = value
                owned.append(element)
                if recursive:
                    owned.extend(self.get_owned_elements(node_id, recursive=True))
        return owned

    def add_project(self, project):
        self.projects[project.id] = project
        return project

    def get_project(self, project_id):
        return self.projects.get(project_id)

    def get_all_projects(self):
        return list(self.projects.values())

    def update_project(self, project_id, updates):
        if project_id not in self.projects:
            return None
        project = self.projects[project_id]
        for key, value in updates.items():
            setattr(project, key, value)
        return project

    def delete_project(self, project_id):
        if project_id not in self.projects:
            return False
        del self.projects[project_id]
        return True

    def add_commit(self, commit):
        self.commits[commit.id] = commit
        return commit

    def get_commit(self, commit_id):
        return self.commits.get(commit_id)

    def get_commits_by_project(self, project_id):
        return [c for c in self.commits.values() if c.project_id == project_id]

    def update_commit(self, commit_id, updates):
        if commit_id not in self.commits:
            return None
        commit = self.commits[commit_id]
        for key, value in updates.items():
            setattr(commit, key, value)
        return commit

    def delete_commit(self, commit_id):
        if commit_id not in self.commits:
            return False
        del self.commits[commit_id]
        return True

    def add_branch(self, branch):
        self.branches[branch.id] = branch
        return branch

    def get_branch(self, branch_id):
        return self.branches.get(branch_id)

    def get_branches_by_project(self, project_id):
        return [b for b in self.branches.values() if b.project_id == project_id]

    def get_branch_by_name(self, project_id, name):
        for branch in self.branches.values():
            if branch.project_id == project_id and branch.name == name:
                return branch
        return None

    def update_branch(self, branch_id, updates):
        if branch_id not in self.branches:
            return None
        branch = self.branches[branch_id]
        for key, value in updates.items():
            setattr(branch, key, value)
        return branch

    def delete_branch(self, branch_id):
        if branch_id not in self.branches:
            return False
        del self.branches[branch_id]
        return True

    def add_tag(self, tag):
        self.tags[tag.id] = tag
        return tag

    def get_tag(self, tag_id):
        return self.tags.get(tag_id)

    def get_tags_by_project(self, project_id):
        return [t for t in self.tags.values() if t.project_id == project_id]

    def get_tag_by_name(self, project_id, name):
        for tag in self.tags.values():
            if tag.project_id == project_id and tag.name == name:
                return tag
        return None

    def update_tag(self, tag_id, updates):
        if tag_id not in self.tags:
            return None
        tag = self.tags[tag_id]
        for key, value in updates.items():
            setattr(tag, key, value)
        return tag

    def delete_tag(self, tag_id):
        if tag_id not in self.tags:
            return False
        del self.tags[tag_id]
        return True

    def query_elements(self, filters=None):
        elements = []
        from app.models.element import Element
        for node_id, node_data in self.graph.nodes(data=True):
            match = True
            if filters:
                for key, value in filters.items():
                    if key == "type":
                        if node_data.get("@type") != value:
                            match = False
                            break
                    elif key == "name":
                        if node_data.get("name") != value:
                            match = False
                            break
                    elif key in node_data:
                        if node_data.get(key) != value:
                            match = False
                            break
                    else:
                        match = False
                        break
            if match:
                element = Element(
                    element_id=node_data.get("identifier"),
                    type=node_data.get("@type", "Element"),
                    name=node_data.get("name"),
                    qualified_name=node_data.get("qualifiedName"),
                    owner_id=node_data.get("owner", {}).get("id") if node_data.get("owner") else None,
                    project_id=node_data.get("project", {}).get("id") if node_data.get("project") else None,
                )
                for k, v in node_data.items():
                    if k not in ("@type", "identifier", "name", "qualifiedName", "owner", "project"):
                        element.data[k] = v
                elements.append(element)
        return elements

    def get_graph(self):
        return self.graph
