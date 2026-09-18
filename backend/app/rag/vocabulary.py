"""Controlled scientific vocabulary and deterministic tagging logic for environmental variables and topics."""

import re
from typing import Dict, List, Set, Tuple

# Controlled vocabulary for target environmental variables
ENVIRONMENTAL_VARIABLES = {
    "soil_ph": [
        r"\bsoil\s*ph\b",
        r"\bph\s*(?:level|value|scale|range)?\s*(?:of\s*)?(?:[0-9]+(?:\.[0-9]+)?)\b",
        r"\b(?:soil\s*)?acidification\b",
        r"\balkalinity\b",
        r"\bacidic\s*soil\b",
    ],
    "soil_organic_carbon": [
        r"\bsoil\s*organic\s*carbon\b",
        r"\bsoc\b",
        r"\bsoil\s*organic\s*matter\b",
        r"\bsom\b",
        r"\bcarbon\s*sequestration\s*(?:in\s*soils?)?\b",
        r"\bhumus\b",
        r"\bsoil\s*carbon\s*stocks?\b",
    ],
    "soil_moisture": [
        r"\bsoil\s*moisture\b",
        r"\bsoil\s*water\s*(?:content|retention|availability|storage)\b",
        r"\bvolumetric\s*water\s*content\b",
        r"\bfield\s*capacity\b",
        r"\bwilting\s*point\b",
    ],
    "temperature": [
        r"\btemperature\b",
        r"\bthermal\s*(?:stress|gradient|regime)\b",
        r"\bambient\s*heat\b",
        r"\bwarming\b",
        r"\bdegrees\s*celsius\b",
        r"\b°\s*c\b",
    ],
    "rainfall": [
        r"\brainfall\b",
        r"\bprecipitation\b",
        r"\bannual\s*rainfall\b",
        r"\bseasonal\s*rains?\b",
        r"\bmonsoon\b",
        r"\bdrought\b",
        r"\baridity\b",
        r"\bprecipitation\s*deficit\b",
    ],
    "land_use": [
        r"\bland\s*use\b",
        r"\bagricultural\s*(?:practices?|land|systems?)\b",
        r"\bmonoculture\b",
        r"\bpolyculture\b",
        r"\bagroforestry\b",
        r"\bpasture\b",
        r"\bgrazing\b",
        r"\btillage\b",
        r"\bcrop\s*rotation\b",
    ],
    "land_cover": [
        r"\bland\s*cover\b",
        r"\bcanopy\s*cover\b",
        r"\bforest\s*cover\b",
        r"\bvegetation\s*cover\b",
        r"\bgrassland\b",
        r"\bshrubland\b",
        r"\bwetland\b",
        r"\bbare\s*soil\b",
    ],
    "species_richness": [
        r"\bspecies\s*richness\b",
        r"\bspecies\s*(?:count|abundance|numbers?)\b",
        r"\btaxa\s*richness\b",
        r"\bfloral\s*diversity\b",
        r"\bfaunal\s*diversity\b",
        r"\bmicrobial\s*(?:richness|biomass)\b",
        r"\bmacrofauna\b",
    ],
    "habitat_diversity": [
        r"\bhabitat\s*(?:diversity|heterogeneity|complexity)\b",
        r"\becological\s*niches?\b",
        r"\bhabitat\s*fragmentation\b",
        r"\bstructural\s*diversity\b",
    ],
    "pollution": [
        r"\bpollution\b",
        r"\bcontaminat(?:ion|ed|s)\b",
        r"\bheavy\s*metals?\b",
        r"\bpesticide\s*residues?\b",
        r"\bfertilizer\s*runoff\b",
        r"\beutrophication\b",
        r"\bchemical\s*toxicity\b",
    ],
    "deforestation": [
        r"\bdeforestation\b",
        r"\bforest\s*clearance\b",
        r"\bforest\s*loss\b",
        r"\bland\s*degradation\b",
        r"\btree\s*felling\b",
        r"\bcanopy\s*removal\b",
    ],
}

# Controlled vocabulary for high-level ecological topics
CORE_TOPICS = {
    "soil": [
        r"\bsoil\b",
        r"\bpedolog(?:y|ical)\b",
        r"\bhorizon\b",
        r"\bmycorrhizae?\b",
        r"\brhizosphere\b",
    ],
    "climate": [
        r"\bclimate\b",
        r"\bweather\b",
        r"\batmospher(?:e|ic)\b",
        r"\bmeteorolog(?:y|ical)\b",
        r"\brainfall\b",
        r"\bprecipitation\b",
        r"\bdrought\b",
    ],
    "biodiversity": [
        r"\bbiodiversity\b",
        r"\bbiota\b",
        r"\bspecies\b",
        r"\bbiological\s*communities?\b",
        r"\bornithological\b",
        r"\bentomological\b",
    ],
    "land": [
        r"\bland\b",
        r"\bterrain\b",
        r"\blandscape\b",
        r"\btopograph(?:y|ic)\b",
        r"\bgeomorpholog(?:y|ical)\b",
    ],
    "water": [
        r"\bwater\b",
        r"\bhydrolog(?:y|ical)\b",
        r"\baquifer\b",
        r"\brunoff\b",
        r"\binfiltration\b",
        r"\bwatershed\b",
    ],
    "agriculture": [
        r"\bagricultur(?:e|al)\b",
        r"\bfarming\b",
        r"\bcropp?ing\b",
        r"\bagroecosystem\b",
        r"\bagronomy\b",
    ],
    "human_impact": [
        r"\banthropogenic\b",
        r"\bhuman\s*(?:impact|pressure|influence|disturbance)\b",
        r"\bland\s*use\s*change\b",
        r"\bdegradation\b",
    ],
    "ecosystem": [
        r"\becosystem\b",
        r"\becolog(?:y|ical)\b",
        r"\bbiome\b",
        r"\bhabitat\b",
        r"\btrophic\b",
    ],
}

# Pre-compile regular expressions for efficiency
COMPILED_VARIABLES = {
    var: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for var, patterns in ENVIRONMENTAL_VARIABLES.items()
}

COMPILED_TOPICS = {
    topic: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for topic, patterns in CORE_TOPICS.items()
}


def tag_text(text: str) -> Tuple[List[str], List[str]]:
    """Identifies environmental variables and core ecological topics in text using deterministic patterns.
    
    Returns:
        Tuple of (matched_variables, matched_topics), alphabetically sorted.
    """
    if not text or not text.strip():
        return [], []

    matched_vars: Set[str] = set()
    for var_name, patterns in COMPILED_VARIABLES.items():
        for pattern in patterns:
            if pattern.search(text):
                matched_vars.add(var_name)
                break

    matched_topics: Set[str] = set()
    for topic_name, patterns in COMPILED_TOPICS.items():
        for pattern in patterns:
            if pattern.search(text):
                matched_topics.add(topic_name)
                break

    return sorted(list(matched_vars)), sorted(list(matched_topics))
