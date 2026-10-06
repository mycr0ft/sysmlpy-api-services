import uuid


class Element:
    SYSML_TYPES = [
        "Element",
        "Package",
        "PartDefinition",
        "PartUsage",
        "ItemDefinition",
        "ItemUsage",
        "ActionDefinition",
        "ActionUsage",
        "AttributeDefinition",
        "AttributeUsage",
        "PortDefinition",
        "PortUsage",
        "InterfaceDefinition",
        "InterfaceUsage",
        "Connector",
        "BindingConnector",
        "FlowConnection",
        "RequirementDefinition",
        "RequirementUsage",
        "ConstraintDefinition",
        "ConstraintUsage",
        "UseCaseDefinition",
        "UseCaseUsage",
        "StateDefinition",
        "StateUsage",
        "ReferenceDefinition",
        "ReferenceUsage",
        "Comment",
        "TextualRepresentation",
        "MetadataDefinition",
        "MetadataUsage",
        "EnumerationDefinition",
        "EnumerationUsage",
        "AssignmentActionUsage",
        "AcceptActionUsage",
        "PerformActionUsage",
        "CalculationDefinition",
        "CalculationUsage",
        "AnalysisCaseDefinition",
        "AnalysisCaseUsage",
        "ConcernDefinition",
        "ConcernUsage",
        "CaseDefinition",
        "CaseUsage",
        "ActorMembership",
        "SubjectMembership",
        "ParameterMembership",
        "FeatureMembership",
        "Definition",
        "Usage",
        "Feature",
        "Type",
        "Classifier",
        "Namespace",
        "Relationship",
        "OwningMembership",
        "Subsetting",
        "FeatureTyping",
        "Redefinition",
        "Conjugation",
        "Intersecting",
        "Unioning",
        "Disjoining",
        "Specialization",
        "Subclassification",
        "Membership",
        "Import",
        "Expose",
        "IncludeUseCaseUsage",
        "RequirementConstraintMembership",
        "RequirementVerificationMembership",
        "RequirementConformanceMembership",
        "StakeholderMembership",
        "ObjectiveMembership",
        "ActorMembership",
        "Succession",
        "FlowConnectionUsage",
        "AllocationDefinition",
        "AllocationUsage",
        "ConnectionDefinition",
        "ConnectionUsage",
        "Association",
        "AssociationStructure",
        "Class",
        "DataType",
        "BooleanExpression",
        "CollectExpression",
        "ConstructorExpression",
        "ControlNode",
        "DecisionNode",
        "ForkNode",
        "JoinNode",
        "MergeNode",
        "ActionNode",
    ]

    def __init__(self, element_id=None, type="Element", name=None, qualified_name=None, owner_id=None, project_id=None):
        self.id = element_id or str(uuid.uuid4())
        self.type = type
        self.name = name
        self.qualified_name = qualified_name
        self.owner_id = owner_id
        self.project_id = project_id
        self.data = {}

    def set_data(self, key, value):
        self.data[key] = value

    def get_data(self, key, default=None):
        return self.data.get(key, default)

    def to_dict(self, include_all=False):
        result = {
            "@type": self.type,
            "identifier": self.id,
        }
        if self.name is not None:
            result["name"] = self.name
        if self.qualified_name is not None:
            result["qualifiedName"] = self.qualified_name
        # OMG spec reference shape: {"identifier": <uuid>} (v1.0 formal EJSON)
        if self.owner_id is not None:
            result["owner"] = {"identifier": self.owner_id}
        if self.project_id is not None:
            result["project"] = {"identifier": self.project_id}

        if include_all:
            result.update(self.data)

        return result

    @classmethod
    def from_dict(cls, data):
        element_type = data.get("@type", data.get("type", "Element"))
        owner = data.get("owner")
        project = data.get("project")
        element = cls(
            element_id=data.get("identifier", data.get("id")),
            type=element_type,
            name=data.get("name"),
            qualified_name=data.get("qualifiedName"),
            owner_id=(owner.get("identifier") or owner.get("id")) if isinstance(owner, dict) else None,
            project_id=(project.get("identifier") or project.get("id")) if isinstance(project, dict) else None,
        )
        for key, value in data.items():
            if key not in ("@type", "type", "identifier", "id", "name", "qualifiedName", "owner", "project"):
                element.data[key] = value
        return element
