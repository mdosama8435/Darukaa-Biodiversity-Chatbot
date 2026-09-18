"""Deterministic registry of scientifically grounded environmental relationships.

All relationships are strictly grounded in authoritative, verified scientific literature:
- FAO State of Knowledge of Soil Biodiversity (2020) [DOI: 10.4060/cb1924en]
- IPCC Special Report on Climate Change and Land (2019) [DOI: 10.1017/9781009157988.006]
"""

from typing import Dict
from app.environmental.schemas import (
    RelationshipType,
    RelationshipDirection,
    MetricRelationshipDefinition,
)

ENVIRONMENTAL_RELATIONSHIPS: Dict[str, MetricRelationshipDefinition] = {
    # -------------------------------------------------------------------------
    # Pairwise Grounded Relationships
    # -------------------------------------------------------------------------
    "soc_soil_biodiversity": MetricRelationshipDefinition(
        relationship_id="soc_soil_biodiversity",
        variables=["soil_organic_carbon", "species_richness"],
        required_variables=["soil_organic_carbon"],
        relationship_type=RelationshipType.ASSOCIATED_WITH,
        direction=RelationshipDirection.POSITIVE,
        mechanism=(
            "Soil organic carbon provides primary chemical energy substrates fueling heterotrophic microbial, "
            "mesofaunal, and macrofaunal food webs; depleted SOC suppresses saprophytic fungi and earthworm populations."
        ),
        evidence_required=True,
        evidence_document_ids=["fao_soil_biodiversity_report_2020"],
        evidence_chunk_ids=["fao_soil_biodiversity_report_2020_c2"],
        source_urls=["https://doi.org/10.4060/cb1924en"],
        doi=["10.4060/cb1924en"],
        publication_titles=["State of Knowledge of Soil Biodiversity: Status, Challenges and Potentialities (FAO 2020)"],
        topics=["soil", "biodiversity"],
    ),
    "rainfall_soil_moisture_stress": MetricRelationshipDefinition(
        relationship_id="rainfall_soil_moisture_stress",
        variables=["rainfall", "soil_moisture"],
        required_variables=["rainfall"],
        relationship_type=RelationshipType.INFLUENCES,
        direction=RelationshipDirection.POSITIVE,
        mechanism=(
            "Precipitation deficits directly deplete volumetric root-zone soil moisture below field capacity, "
            "halting extracellular enzyme diffusion and precipitating cellular desiccation in the soil microbiome."
        ),
        evidence_required=True,
        evidence_document_ids=["fao_soil_biodiversity_report_2020", "ipcc_srccl_land_degradation_2019"],
        evidence_chunk_ids=["fao_soil_biodiversity_report_2020_c4", "ipcc_srccl_land_degradation_2019_c2"],
        source_urls=["https://doi.org/10.4060/cb1924en", "https://www.ipcc.ch/srccl/chapter/chapter-4/"],
        doi=["10.4060/cb1924en", "10.1017/9781009157988.006"],
        publication_titles=[
            "State of Knowledge of Soil Biodiversity (FAO 2020)",
            "IPCC SRCCL: Chapter 4 — Land Degradation (IPCC 2019)",
        ],
        topics=["climate", "soil", "water"],
    ),
    "ph_microbial_structure": MetricRelationshipDefinition(
        relationship_id="ph_microbial_structure",
        variables=["soil_ph", "species_richness"],
        required_variables=["soil_ph"],
        relationship_type=RelationshipType.INFLUENCES,
        direction=RelationshipDirection.NON_LINEAR,
        mechanism=(
            "Extreme soil acidification (pH < 5.5) induces proton and aluminum toxicity that sharply reduces bacterial "
            "taxa richness, whereas optimal bacterial diversity and enzymatic mineralisation occur between pH 6.0 and 7.5."
        ),
        evidence_required=True,
        evidence_document_ids=["fao_soil_biodiversity_report_2020"],
        evidence_chunk_ids=["fao_soil_biodiversity_report_2020_c3"],
        source_urls=["https://doi.org/10.4060/cb1924en"],
        doi=["10.4060/cb1924en"],
        publication_titles=["State of Knowledge of Soil Biodiversity (FAO 2020)"],
        topics=["soil", "biodiversity"],
    ),
    "temp_soil_carbon_oxidation": MetricRelationshipDefinition(
        relationship_id="temp_soil_carbon_oxidation",
        variables=["temperature", "soil_organic_carbon"],
        required_variables=["temperature", "soil_organic_carbon"],
        relationship_type=RelationshipType.CAN_REDUCE,
        direction=RelationshipDirection.NEGATIVE,
        mechanism=(
            "Elevated ambient and topsoil temperatures accelerate heterotrophic microbial respiration, promoting thermal "
            "oxidation of organic carbon stocks and diminishing soil humus persistence."
        ),
        evidence_required=True,
        evidence_document_ids=["ipcc_srccl_land_degradation_2019"],
        evidence_chunk_ids=["ipcc_srccl_land_degradation_2019_c3"],
        source_urls=["https://www.ipcc.ch/srccl/chapter/chapter-4/"],
        doi=["10.1017/9781009157988.006"],
        publication_titles=["IPCC SRCCL: Chapter 4 — Land Degradation (IPCC 2019)"],
        topics=["climate", "soil"],
    ),
    "land_use_habitat_diversity": MetricRelationshipDefinition(
        relationship_id="land_use_habitat_diversity",
        variables=["land_use", "habitat_diversity"],
        required_variables=["land_use"],
        relationship_type=RelationshipType.INFLUENCES,
        direction=RelationshipDirection.COMPLEX,
        mechanism=(
            "Continuous annual monocultures eliminate canopy layering and structural complexity, whereas diversified "
            "cropping, rotational grazing, and agroforestry supply multi-tier niches that foster predator and pollinator diversity."
        ),
        evidence_required=True,
        evidence_document_ids=["ipcc_srccl_land_degradation_2019", "fao_soil_biodiversity_report_2020"],
        evidence_chunk_ids=["ipcc_srccl_land_degradation_2019_c1", "fao_soil_biodiversity_report_2020_c1"],
        source_urls=["https://www.ipcc.ch/srccl/chapter/chapter-4/", "https://doi.org/10.4060/cb1924en"],
        doi=["10.1017/9781009157988.006", "10.4060/cb1924en"],
        publication_titles=[
            "IPCC SRCCL: Chapter 4 — Land Degradation (IPCC 2019)",
            "State of Knowledge of Soil Biodiversity (FAO 2020)",
        ],
        topics=["land", "biodiversity", "agriculture"],
    ),
    "deforestation_soil_erosion": MetricRelationshipDefinition(
        relationship_id="deforestation_soil_erosion",
        variables=["deforestation", "soil_organic_carbon"],
        required_variables=["deforestation", "soil_organic_carbon"],
        relationship_type=RelationshipType.CAN_REDUCE,
        direction=RelationshipDirection.NEGATIVE,
        mechanism=(
            "Loss of forest canopy cover exposes mineral topsoil directly to rainfall kinetic energy, precipitating "
            "severe runoff, sheet erosion, and loss of particulate organic carbon."
        ),
        evidence_required=True,
        evidence_document_ids=["ipcc_srccl_land_degradation_2019"],
        evidence_chunk_ids=["ipcc_srccl_land_degradation_2019_c1", "ipcc_srccl_land_degradation_2019_c2"],
        source_urls=["https://www.ipcc.ch/srccl/chapter/chapter-4/"],
        doi=["10.1017/9781009157988.006"],
        publication_titles=["IPCC SRCCL: Chapter 4 — Land Degradation (IPCC 2019)"],
        topics=["land", "soil", "ecosystem"],
    ),
    "pollution_biodiversity": MetricRelationshipDefinition(
        relationship_id="pollution_biodiversity",
        variables=["pollution", "species_richness"],
        required_variables=["pollution"],
        relationship_type=RelationshipType.CAN_REDUCE,
        direction=RelationshipDirection.NEGATIVE,
        mechanism=(
            "Chemical contaminants, heavy metals, and persistent agrochemicals exert direct toxic stress on sensitive "
            "soil micro-arthropods, nitrifying bacteria, and mycorrhizal symbionts."
        ),
        evidence_required=True,
        evidence_document_ids=["fao_soil_biodiversity_report_2020"],
        evidence_chunk_ids=["fao_soil_biodiversity_report_2020_c1"],
        source_urls=["https://doi.org/10.4060/cb1924en"],
        doi=["10.4060/cb1924en"],
        publication_titles=["State of Knowledge of Soil Biodiversity (FAO 2020)"],
        topics=["human_impact", "biodiversity", "soil"],
    ),

    # -------------------------------------------------------------------------
    # Compound Multi-Metric Relationships (>= 3 variables simultaneously)
    # -------------------------------------------------------------------------
    "soc_rainfall_monoculture_stress": MetricRelationshipDefinition(
        relationship_id="soc_rainfall_monoculture_stress",
        variables=["soil_organic_carbon", "rainfall", "land_use"],
        required_variables=["soil_organic_carbon", "rainfall", "land_use"],
        practice_keywords=["monoculture", "wheat", "maize", "annual", "crop", "conventional", "tillage"],
        relationship_type=RelationshipType.EXACERBATES,
        direction=RelationshipDirection.NEGATIVE,
        mechanism=(
            "Depleted soil organic carbon combined with low precipitation under continuous monoculture cropping "
            "exacerbates soil structure collapse, reduces aggregate water-holding capacity, suppresses subterranean "
            "microbial respiration, and heightens overall ecological vulnerability."
        ),
        evidence_required=True,
        evidence_document_ids=[
            "fao_soil_biodiversity_report_2020",
            "ipcc_srccl_land_degradation_2019",
        ],
        evidence_chunk_ids=[
            "fao_soil_biodiversity_report_2020_c2",
            "ipcc_srccl_land_degradation_2019_c2",
        ],
        source_urls=[
            "https://doi.org/10.4060/cb1924en",
            "https://www.ipcc.ch/srccl/chapter/chapter-4/",
        ],
        doi=[
            "10.4060/cb1924en",
            "10.1017/9781009157988.006",
        ],
        publication_titles=[
            "State of Knowledge of Soil Biodiversity (FAO 2020)",
            "IPCC SRCCL: Chapter 4 — Land Degradation (IPCC 2019)",
        ],
        topics=["soil", "climate", "agriculture", "biodiversity"],
    ),
    "temp_rainfall_vegetation_stress": MetricRelationshipDefinition(
        relationship_id="temp_rainfall_vegetation_stress",
        variables=["temperature", "rainfall", "species_richness"],
        required_variables=["temperature", "rainfall"],
        relationship_type=RelationshipType.EXACERBATES,
        direction=RelationshipDirection.NEGATIVE,
        mechanism=(
            "The simultaneous occurrence of elevated ambient temperatures and rainfall deficits elevates vapor pressure "
            "deficits and accelerates soil organic carbon oxidation, driving widespread floral and microbial species decline."
        ),
        evidence_required=True,
        evidence_document_ids=["ipcc_srccl_land_degradation_2019", "fao_soil_biodiversity_report_2020"],
        evidence_chunk_ids=["ipcc_srccl_land_degradation_2019_c3", "fao_soil_biodiversity_report_2020_c4"],
        source_urls=["https://www.ipcc.ch/srccl/chapter/chapter-4/", "https://doi.org/10.4060/cb1924en"],
        doi=["10.1017/9781009157988.006", "10.4060/cb1924en"],
        publication_titles=[
            "IPCC SRCCL: Chapter 4 — Land Degradation (IPCC 2019)",
            "State of Knowledge of Soil Biodiversity (FAO 2020)",
        ],
        topics=["climate", "biodiversity", "soil"],
    ),
    "agroforestry_soc_water_buffering": MetricRelationshipDefinition(
        relationship_id="agroforestry_soc_water_buffering",
        variables=["land_use", "soil_organic_carbon", "soil_moisture", "species_richness"],
        required_variables=["land_use", "soil_organic_carbon"],
        practice_keywords=["agroforest", "tree", "silvopasture", "woody", "perennial"],
        relationship_type=RelationshipType.ENHANCES,
        direction=RelationshipDirection.POSITIVE,
        mechanism=(
            "Integrating perennial woody species into croplands provides thermal insulation, reduces runoff velocity, "
            "preserves soil carbon horizons, and maintains root-zone microclimates that protect biological diversity "
            "as documented in IPCC SRCCL Chapter 4."
        ),
        evidence_required=True,
        evidence_document_ids=["ipcc_srccl_land_degradation_2019", "fao_soil_biodiversity_report_2020"],
        evidence_chunk_ids=[
            "ipcc_srccl_land_degradation_2019_c1",
            "ipcc_srccl_land_degradation_2019_c3",
            "fao_soil_biodiversity_report_2020_c2",
        ],
        source_urls=["https://www.ipcc.ch/srccl/chapter/chapter-4/", "https://doi.org/10.4060/cb1924en"],
        doi=["10.1017/9781009157988.006", "10.4060/cb1924en"],
        publication_titles=[
            "IPCC SRCCL: Chapter 4 — Land Degradation (IPCC 2019)",
            "State of Knowledge of Soil Biodiversity (FAO 2020)",
        ],
        topics=["agriculture", "soil", "water", "biodiversity"],
    ),
    "deforestation_erosion_biodiversity": MetricRelationshipDefinition(
        relationship_id="deforestation_erosion_biodiversity",
        variables=["deforestation", "rainfall", "soil_organic_carbon", "species_richness"],
        required_variables=["deforestation", "rainfall", "soil_organic_carbon"],
        relationship_type=RelationshipType.CAN_REDUCE,
        direction=RelationshipDirection.NEGATIVE,
        mechanism=(
            "Canopy removal combined with erosive precipitation strips topsoil carbon horizons and disrupts underground "
            "fungal and macrofaunal communities, leading to cascading habitat fragmentation and species loss."
        ),
        evidence_required=True,
        evidence_document_ids=["ipcc_srccl_land_degradation_2019"],
        evidence_chunk_ids=["ipcc_srccl_land_degradation_2019_c1", "ipcc_srccl_land_degradation_2019_c2"],
        source_urls=["https://www.ipcc.ch/srccl/chapter/chapter-4/"],
        doi=["10.1017/9781009157988.006"],
        publication_titles=["IPCC SRCCL: Chapter 4 — Land Degradation (IPCC 2019)"],
        topics=["land", "climate", "soil", "biodiversity"],
    ),
    "intercropping_habitat_diversity": MetricRelationshipDefinition(
        relationship_id="intercropping_habitat_diversity",
        variables=["land_use", "species_richness", "habitat_diversity"],
        required_variables=["land_use"],
        practice_keywords=["intercrop", "polyculture", "diversif", "companion"],
        relationship_type=RelationshipType.ENHANCES,
        direction=RelationshipDirection.POSITIVE,
        mechanism=(
            "Diversified intercropping replaces continuous monoculture with multi-species crop canopy and rooting layers, "
            "fostering pollinator, predatory insect, and below-ground microbial community diversity."
        ),
        evidence_required=True,
        evidence_document_ids=["fao_soil_biodiversity_report_2020", "ipcc_srccl_land_degradation_2019"],
        evidence_chunk_ids=["fao_soil_biodiversity_report_2020_c1", "ipcc_srccl_land_degradation_2019_c1"],
        source_urls=["https://doi.org/10.4060/cb1924en", "https://www.ipcc.ch/srccl/chapter/chapter-4/"],
        doi=["10.4060/cb1924en", "10.1017/9781009157988.006"],
        publication_titles=[
            "State of Knowledge of Soil Biodiversity (FAO 2020)",
            "IPCC SRCCL: Chapter 4 — Land Degradation (IPCC 2019)",
        ],
        topics=["agriculture", "biodiversity", "land"],
    ),
    "cover_crop_soil_carbon_retention": MetricRelationshipDefinition(
        relationship_id="cover_crop_soil_carbon_retention",
        variables=["land_use", "soil_organic_carbon", "soil_moisture"],
        required_variables=["land_use", "soil_organic_carbon"],
        practice_keywords=["cover crop", "residue", "mulch", "no-till"],
        relationship_type=RelationshipType.ENHANCES,
        direction=RelationshipDirection.POSITIVE,
        mechanism=(
            "Cover cropping and continuous surface residue retention protect mineral soil from direct raindrop impact erosion, "
            "supply fresh organic substrates that stimulate microbial respiration, and promote aggregate stability."
        ),
        evidence_required=True,
        evidence_document_ids=["fao_soil_biodiversity_report_2020", "ipcc_srccl_land_degradation_2019"],
        evidence_chunk_ids=["fao_soil_biodiversity_report_2020_c2", "ipcc_srccl_land_degradation_2019_c2"],
        source_urls=["https://doi.org/10.4060/cb1924en", "https://www.ipcc.ch/srccl/chapter/chapter-4/"],
        doi=["10.4060/cb1924en", "10.1017/9781009157988.006"],
        publication_titles=[
            "State of Knowledge of Soil Biodiversity (FAO 2020)",
            "IPCC SRCCL: Chapter 4 — Land Degradation (IPCC 2019)",
        ],
        topics=["soil", "agriculture", "climate"],
    ),
    "temp_rise_moisture_compound_stress": MetricRelationshipDefinition(
        relationship_id="temp_rise_moisture_compound_stress",
        variables=["temperature", "rainfall", "soil_moisture", "species_richness"],
        required_variables=["temperature", "rainfall"],
        relationship_type=RelationshipType.EXACERBATES,
        direction=RelationshipDirection.NEGATIVE,
        mechanism=(
            "Concurrent ambient temperature rise and precipitation deficits exacerbate vapor pressure deficits, "
            "accelerate surface soil desiccation below permanent wilting point, and cause widespread mortality across soil mesofauna."
        ),
        evidence_required=True,
        evidence_document_ids=["ipcc_srccl_land_degradation_2019", "fao_soil_biodiversity_report_2020"],
        evidence_chunk_ids=["ipcc_srccl_land_degradation_2019_c3", "fao_soil_biodiversity_report_2020_c4"],
        source_urls=["https://www.ipcc.ch/srccl/chapter/chapter-4/", "https://doi.org/10.4060/cb1924en"],
        doi=["10.1017/9781009157988.006", "10.4060/cb1924en"],
        publication_titles=[
            "IPCC SRCCL: Chapter 4 — Land Degradation (IPCC 2019)",
            "State of Knowledge of Soil Biodiversity (FAO 2020)",
        ],
        topics=["climate", "soil", "biodiversity"],
    ),
}

