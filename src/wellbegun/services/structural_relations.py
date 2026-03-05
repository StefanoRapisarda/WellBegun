"""Pure constants module for entity relationship predicates.

No service imports — safe to import from anywhere without circular deps.
"""

ENTITY_TYPES = [
    "project",
    "activity",
    "note",
    "log",
    "source",
    "actor",
    "plan",
    "collection",
]

# Meaningful (source_type, target_type) pairs → default predicate verb.
# Only pairs with clear, natural relationships are listed here.
# Unlisted pairs fall back to "related to" via get_structural_predicate().
# Convention: lowercase verb phrases, third-person where natural.
# Reads as "subject [predicate] object".
STRUCTURAL_PREDICATES: dict[tuple[str, str], str] = {
    # ── project ──
    ("project", "project"): "related to",
    ("project", "activity"): "contains",
    ("project", "note"): "contains",
    ("project", "log"): "contains",
    ("project", "source"): "references",
    ("project", "actor"): "involves",
    ("project", "plan"): "contains",
    # ── activity ──
    ("activity", "project"): "belongs to",
    ("activity", "activity"): "related to",
    ("activity", "note"): "contains",
    ("activity", "log"): "contains",
    ("activity", "source"): "consults",
    ("activity", "actor"): "assigned to",
    ("activity", "plan"): "belongs to",
    # ── note ──
    ("note", "project"): "belongs to",
    ("note", "activity"): "documents",
    ("note", "note"): "links to",
    ("note", "log"): "references",
    ("note", "source"): "cites",
    ("note", "actor"): "mentions",
    ("note", "plan"): "informs",
    # ── log ──
    ("log", "project"): "belongs to",
    ("log", "activity"): "records",
    ("log", "note"): "references",
    ("log", "log"): "related to",
    ("log", "source"): "cites",
    ("log", "actor"): "mentions",
    ("log", "plan"): "reports on",
    # ── source ──
    ("source", "source"): "related to",
    ("source", "actor"): "mentioned by",
    # ── actor ──
    ("actor", "project"): "contributes to",
    ("actor", "activity"): "performs",
    ("actor", "note"): "creates",
    ("actor", "log"): "creates",
    ("actor", "source"): "mentions",
    ("actor", "actor"): "collaborates with",
    ("actor", "plan"): "owns",
    # ── plan ──
    ("plan", "project"): "targets",
    ("plan", "note"): "has note",
    ("plan", "plan"): "related to",
    ("plan", "collection"): "has collection",
    # ── collection ──
    ("collection", "source"): "contains",
    ("collection", "activity"): "contains",
    ("collection", "note"): "contains",
    ("collection", "project"): "contains",
    ("collection", "log"): "contains",
    ("collection", "actor"): "contains",
    ("collection", "plan"): "contains",
    ("collection", "collection"): "related to",
    ("source", "collection"): "appears in",
    ("activity", "collection"): "appears in",
    ("note", "collection"): "appears in",
    ("project", "collection"): "appears in",
    ("log", "collection"): "appears in",
    ("actor", "collection"): "curates",
    ("plan", "collection"): "appears in",
}

SEMANTIC_RELATIONS: dict[str, list[dict[str, str]]] = {
    "Meaning": [
        {"key": "defines", "forward": "defines", "reverse": "defined by"},
        {"key": "exemplifies", "forward": "exemplifies", "reverse": "exemplified by"},
        {"key": "contrasts with", "forward": "contrasts with", "reverse": "contrasts with"},
        {"key": "synonymous with", "forward": "synonymous with", "reverse": "synonymous with"},
    ],
    "Reasoning": [
        {"key": "supports", "forward": "supports", "reverse": "supported by"},
        {"key": "contradicts", "forward": "contradicts", "reverse": "contradicted by"},
        {"key": "assumes", "forward": "assumes", "reverse": "assumed by"},
        {"key": "implies", "forward": "implies", "reverse": "implied by"},
    ],
    "Causality": [
        {"key": "causes", "forward": "causes", "reverse": "caused by"},
        {"key": "enables", "forward": "enables", "reverse": "enabled by"},
        {"key": "prevents", "forward": "prevents", "reverse": "prevented by"},
        {"key": "depends on", "forward": "depends on", "reverse": "depended on by"},
    ],
    "Process": [
        {"key": "precedes", "forward": "precedes", "reverse": "follows"},
        {"key": "transforms into", "forward": "transforms into", "reverse": "transformed from"},
        {"key": "implements", "forward": "implements", "reverse": "implemented by"},
        {"key": "extends", "forward": "extends", "reverse": "extended by"},
    ],
    "Planning": [
        {"key": "blocks", "forward": "blocks", "reverse": "blocked by"},
        {"key": "prioritizes", "forward": "prioritizes", "reverse": "prioritized by"},
        {"key": "decomposes into", "forward": "decomposes into", "reverse": "part of"},
        {"key": "alternative to", "forward": "alternative to", "reverse": "alternative to"},
    ],
    "Evaluation": [
        {"key": "validates", "forward": "validates", "reverse": "validated by"},
        {"key": "critiques", "forward": "critiques", "reverse": "critiqued by"},
        {"key": "improves", "forward": "improves", "reverse": "improved by"},
        {"key": "supersedes", "forward": "supersedes", "reverse": "superseded by"},
    ],
    "Participation": [
        {"key": "attends", "forward": "attends", "reverse": "attended by"},
        {"key": "chairs", "forward": "chairs", "reverse": "chaired by"},
        {"key": "presents at", "forward": "presents at", "reverse": "presented by"},
    ],
}


def get_structural_predicate(source_type: str, target_type: str) -> str:
    """Return the default structural predicate for a (source, target) type pair."""
    return STRUCTURAL_PREDICATES.get((source_type, target_type), "related to")
