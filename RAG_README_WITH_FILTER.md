# CVE RAG (Pentagent)

## Overview
CVE RAG is a Retrieval-Augmented Generation (RAG) component for vulnerability research. It indexes NVD CVE records into a vector database and provides hybrid retrieval (dense + sparse) with reranking to return high-relevance CVEs for security investigations.

## Key Features
- **Hybrid search**: Dense semantic retrieval combined with sparse keyword matching.
- **Reranking**: Improves relevance for top results.
- **AI query optimization**: Extracts intent and constraints from the user query.
- **Strict filtering**: Filters results by year, product, vendor, language/ecosystem, domain, negative keywords, and protocol/type signals.
- **Entity-mismatch resilience**: If strict filters eliminate all candidates, the system can relax constraints and retry to avoid false “no results”.
- **API-ready**: Designed to be consumed by the Pentagent backend/frontend.

## Filtering Rules (High Level)
The system can apply filters derived from the query and context:
- **Year**: Keeps CVEs whose CVE ID year or published year matches the requested year.
- **Product/Vendor**: Prefers and/or enforces matches in structured fields or description content.
- **Language/Ecosystem**: Focuses results (e.g., Python, Java, PHP, JavaScript) when indicated.
- **Domain**: Applies domain hints (e.g., container, OS, cloud, IoT) to reduce off-topic results.
- **Negative keywords**: Excludes results that contain explicitly unwanted terms.
- **Protocol/type signals**: Distinguishes protocol vulnerabilities from OS/mechanism-only matches when the query implies it.

## Data & Pipeline
- Data source: **NVD CVE** dataset (and optional enrichment from referenced sources).
- Processing: normalization, metadata extraction, quality filtering, embedding generation, indexing into Qdrant.

## Deployment Notes
- Backend must allow the production frontend origin via CORS.
- Keep query years intact when optimizing queries (do not drop CVE years).

## License
See the repository license.


