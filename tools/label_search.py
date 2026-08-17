import requests
from strands import tool

OPENFDA_URL = "https://api.fda.gov/drug/label.json"

SUPPORTED_DRUGS = {
    "azithromycin": "azithromycin",
    "ozempic": "ozempic",
    "paracetamol": "acetaminophen",
}


@tool
def search_drug_label(drug_name: str, section: str) -> dict:
    drug_name = drug_name.lower().strip()

    if drug_name not in SUPPORTED_DRUGS:
        return {
            "success": False,
            "error": (
                f"Unsupported drug: {drug_name}. "
                f"Supported drugs are: {', '.join(SUPPORTED_DRUGS.keys())}"
            )
        }

    allowed_sections = {
        "indications_and_usage",
        "contraindications",
        "warnings_and_cautions",
        "adverse_reactions",
        "dosage_and_administration",
        "boxed_warning",
    }

    if section not in allowed_sections:
        return {
            "success": False,
            "error": f"Unsupported section: {section}"
        }

    try:
        response = requests.get(
            OPENFDA_URL,
            params={
                "search": f'openfda.brand_name:"{SUPPORTED_DRUGS[drug_name]}"',
                "limit": 5,
            },
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()

    except requests.RequestException as e:
        return {
            "success": False,
            "error": f"openFDA request failed: {str(e)}"
        }

    results = data.get("results", [])

    if not results:
        return {
            "success": False,
            "error": f"No approved labeling found for {drug_name}."
        }

    evidence = []

    for result in results:
        values = result.get(section, [])

        if isinstance(values, str):
            values = [values]

        for value in values:
            evidence.append(value)

    if not evidence:
        return {
            "success": False,
            "error": (
                f"No information found for section "
                f"'{section}' in the retrieved labeling."
            )
        }

    result = results[0]

    openfda = result.get("openfda", {})

    return {
        "success": True,
        "drug": drug_name,
        "section": section,
        "evidence": evidence,
        "brand_name": openfda.get("brand_name", []),
        "generic_name": openfda.get("generic_name", []),
        "source": "openFDA Drug Label API",
    }