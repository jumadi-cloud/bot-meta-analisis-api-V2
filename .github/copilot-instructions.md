# Copilot Instructions for API AI AGENT - RAG

## Project Overview
- **Purpose:** REST API for Facebook Ads analytics, using Google Sheets as the main data source, Gemini AI (LangChain) for LLM-based narrative analysis, and ChromaDB for vector search (RAG).
- **Main Components:**
  - `app.py`: Flask app entry point, registers routes and configures services.
  - `routes/`: API endpoints (chat, health, history, sheet, etc.).
  - `services/`: Business logic, aggregation, LLM summary, vector store.
  - `utils/`: Common helpers/utilities.
  - `workflows/`: Workflow orchestration (e.g., aggregation).
- **Data Flow:**
  1. User query → `/chat` endpoint
  2. Data fetched from Google Sheets (with caching)
  3. Aggregation/analysis in `services/`
  4. LLM (Gemini) generates narrative insight
  5. Response returned via Flask

## Key Patterns & Conventions
- **Additive Logic:** New features must not break or remove old logic; always extend existing capabilities.
- **Segmented Filters:** All analytics can be filtered by gender, age, adset, ad, date, week, month, metric. Combine filters as needed.
- **Debug Logging:** Every segmented filter and query is logged for troubleshooting. Check logs for filter/data issues.
- **Insight Format:** Always return narrative, actionable insights (not raw data tables).
- **Fallbacks:** If data is missing, return the closest available insight or a summary, never fabricate data.

## Developer Workflows
- **Run Locally:**
  - `python app.py` (Flask dev server)
- **API Endpoints:**
  - `POST /chat` – Main analytics chatbot
  - `GET /cache/status` – Google Sheets cache status
  - `POST /cache/clear` – Clear cache manually
- **Debugging:**
  - Check server logs for filter application and data processing details.
  - Use log output to audit segmented queries and troubleshoot edge cases.
- **Performance:**
  - Google Sheets calls are cached (default: 5 min) for speed and efficiency.
  - Caching and memory management are handled in the service layer.

## Integration Points
- **Google Sheets:** Main data source, updated in real-time.
- **Gemini AI (LangChain):** Used for generating narrative insights.
- **ChromaDB:** Vector store for RAG (retrieval augmented generation).

## Examples & References
- See `README.md` for query examples, edge cases, and logic explanations.
- Architecture diagram: `architecture_diagram.html` (if available).
- Example segmented query: "Berapa cost tertinggi dari wanita usia 45-54 di bulan September?"

## Project-Specific Advice
- Never remove or break existing logic when adding features (additive only).
- Always log segmented filters and queries for traceability.
- Prefer narrative, actionable responses over raw data.
- If data is missing, provide the closest available summary, not fabricated results.

---
For more details, see `README.md` and the architecture diagram. If unsure about a pattern, check recent code in `routes/` and `services/` for examples.
