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
    "reading_list",
    "learning_track",
]

# All 64 (source_type, target_type) pairs → default predicate verb.
# Includes self-type pairs (e.g. project→project).
STRUCTURAL_PREDICATES: dict[tuple[str, str], str] = {
    # project →
    ("project", "project"): "HAS_SUBPROJECT",
    ("project", "activity"): "includes",
    ("project", "note"): "produces",
    ("project", "log"): "generates",
    ("project", "source"): "uses",
    ("project", "reading_list"): "references",
    ("project", "learning_track"): "follows",
    ("project", "actor"): "involves",
    # activity →
    ("activity", "project"): "belong to",
    ("activity", "activity"): "HAS_SUBACTIVITY",
    ("activity", "note"): "produce",
    ("activity", "log"): "generate",
    ("activity", "source"): "use",
    ("activity", "reading_list"): "reference",
    ("activity", "learning_track"): "support",
    ("activity", "actor"): "involve",
    # note →
    ("note", "project"): "belong to",
    ("note", "activity"): "belong to",
    ("note", "note"): "LINKS_TO",
    ("note", "log"): "document",
    ("note", "source"): "cite",
    ("note", "reading_list"): "reference",
    ("note", "learning_track"): "support",
    ("note", "actor"): "mention",
    # log →
    ("log", "project"): "belong to",
    ("log", "activity"): "belong to",
    ("log", "note"): "reference",
    ("log", "log"): "CONTINUES",
    ("log", "source"): "cite",
    ("log", "reading_list"): "reference",
    ("log", "learning_track"): "support",
    ("log", "actor"): "mention",
    # source →
    ("source", "project"): "inform",
    ("source", "activity"): "inform",
    ("source", "note"): "inspire",
    ("source", "log"): "inspire",
    ("source", "source"): "RELATED_SOURCE",
    ("source", "reading_list"): "appear in",
    ("source", "learning_track"): "appear in",
    ("source", "actor"): "authored by",
    # actor →
    ("actor", "project"): "participate in",
    ("actor", "activity"): "participate in",
    ("actor", "note"): "author",
    ("actor", "log"): "author",
    ("actor", "source"): "create",
    ("actor", "actor"): "COLLABORATES_WITH",
    ("actor", "reading_list"): "curate",
    ("actor", "learning_track"): "mentor",
    # reading_list →
    ("reading_list", "project"): "support",
    ("reading_list", "activity"): "support",
    ("reading_list", "note"): "collect",
    ("reading_list", "log"): "collect",
    ("reading_list", "source"): "contain",
    ("reading_list", "actor"): "curated by",
    ("reading_list", "reading_list"): "RELATED_LIST",
    ("reading_list", "learning_track"): "feed",
    # learning_track →
    ("learning_track", "project"): "support",
    ("learning_track", "activity"): "support",
    ("learning_track", "note"): "produce",
    ("learning_track", "log"): "produce",
    ("learning_track", "source"): "contain",
    ("learning_track", "actor"): "mentored by",
    ("learning_track", "reading_list"): "include",
    ("learning_track", "learning_track"): "PREREQUISITE_OF",
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
}


def get_structural_predicate(source_type: str, target_type: str) -> str:
    """Return the default structural predicate for a (source, target) type pair."""
    return STRUCTURAL_PREDICATES.get((source_type, target_type), "related to")
