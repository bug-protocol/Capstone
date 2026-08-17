from mcp.server.fastmcp import FastMCP
import requests
from collections import Counter

mcp = FastMCP("Capstone-Medical-Gateway")


@mcp.tool()
def search_adverse_events_mcp(drug_name: str, limit: int = 20) -> dict:
    url = "https://api.fda.gov/drug/event.json"
    params = {
        "search": f'patient.drug.medicinalproduct:"{drug_name}"',
        "limit": limit,
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return {"error": f"openFDA request failed: {str(e)}"}

    counter = Counter()
    for report in data.get("results", []):
        reactions = report.get("patient", {}).get("reaction", [])
        for reaction in reactions:
            name = reaction.get("reactionmeddrapt")
            if name:
                counter[name] += 1

    return {
        "drug": drug_name,
        "sample_size": len(data.get("results", [])),
        "frequently_reported_reactions": dict(counter.most_common(10)),
        "source": "openFDA Drug Event API (via AgentCore Gateway MCP)",
        "caveat": "Reported adverse-event frequencies are based on spontaneous reports and do not establish causality."
    }


@mcp.tool()
def search_clinical_trials_mcp(drug_name: str, page_size: int = 5) -> dict:
    url = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        "query.term": drug_name,
        "pageSize": page_size,
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return {"error": f"ClinicalTrials.gov request failed: {str(e)}"}

    studies = []
    for study in data.get("studies", []):
        protocol = study.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        design = protocol.get("designModule", {})

        studies.append({
            "nct_id": identification.get("nctId"),
            "title": identification.get("briefTitle"),
            "status": status.get("overallStatus"),
            "phase": ", ".join(design.get("phases", [])) or "Not Specified",
        })

    return {
        "drug": drug_name,
        "total_studies_returned": len(studies),
        "studies": studies,
        "source": "ClinicalTrials.gov API v2 (via AgentCore Gateway MCP)"
    }


if __name__ == "__main__":
    mcp.run()
