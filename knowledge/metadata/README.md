# Knowledge Metadata Registry

This directory holds JSON-formatted companion metadata for every scientific document in `knowledge/sources/`.

## Metadata Schema
Each metadata file conforms to the `DocumentMetadata` Pydantic schema (`app.rag.schemas.DocumentMetadata`):

```json
{
  "title": "Full Document Title",
  "source": "Publishing Organization (e.g. FAO, IPCC, Research Paper)",
  "document_type": "report | paper | summary",
  "publication_year": 2020,
  "authors": ["Author 1", "Author 2"],
  "doi": "10.xxxx/xxxx",
  "journal": "Journal Name (if applicable)",
  "url": "https://doi.org/...",
  "license": "Creative Commons / Open Access Terms",
  "geographic_scope": "global | regional",
  "topics": ["soil", "biodiversity", "water", "climate"],
  "variables": ["soil_organic_carbon", "soil_ph", "species_richness"]
}
```

The ingestion pipeline automatically matches each document with its corresponding metadata file using stem naming (e.g., `doc_name.pdf` matches `doc_name.json`).
