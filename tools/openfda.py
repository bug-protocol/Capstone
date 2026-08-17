from collections import Counter
import requests
from strands import tool


@tool
def search_adverse_events(
    drug_name: str,
    limit: int = 20,
):
    url = "https://api.fda.gov/drug/event.json"

    params = {
        "search": f'patient.drug.medicinalproduct:"{drug_name}"',
        "limit": limit,
    }

    response = requests.get(
        url,
        params=params,
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    counter = Counter()

    for report in data.get("results", []):
        reactions = report.get("patient", {}).get("reaction", [])
        for reaction in reactions:
            name = reaction.get("reactionmeddrapt")
            if name:
                counter[name] += 1

    return dict(counter.most_common(10))