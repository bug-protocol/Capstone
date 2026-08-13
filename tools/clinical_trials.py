import requests
from strands import tool


@tool
def search_clinical_trials(
    drug_name: str,
    page_size: int = 5,
):
    url = "https://clinicaltrials.gov/api/v2/studies"

    params = {
        "query.term": drug_name,
        "pageSize": page_size,
    }

    response = requests.get(
        url,
        params=params,
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    studies = []

    for study in data.get("studies", []):

        protocol = study.get("protocolSection", {})

        identification = protocol.get(
            "identificationModule",
            {}
        )

        status = protocol.get(
            "statusModule",
            {}
        )

        design = protocol.get(
            "designModule",
            {}
        )

        studies.append(
            {
                "NCT ID": identification.get("nctId"),
                "Title": identification.get("briefTitle"),
                "Status": status.get("overallStatus"),
                "Phase": ", ".join(
                    design.get("phases", [])
                ) or "Not Specified",
            }
        )

    return studies