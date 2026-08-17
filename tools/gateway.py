import os
import logging
from strands import tool

try:
    from bedrock_agentcore.gateway import GatewayClient
    GATEWAY_CLIENT_AVAILABLE = True
except ImportError:
    GATEWAY_CLIENT_AVAILABLE = False

from tools.mcp_server import search_adverse_events_mcp, search_clinical_trials_mcp

logger = logging.getLogger("capstone.gateway")


@tool
def gateway_search_adverse_events(drug_name: str, limit: int = 20) -> dict:
    gateway_url = os.getenv("AGENTCORE_GATEWAY_URL")
    target_id = os.getenv("AGENTCORE_GATEWAY_TARGET_ID")

    if GATEWAY_CLIENT_AVAILABLE and (gateway_url or target_id):
        try:
            logger.info(f"Invoking openFDA adverse event tool via AgentCore Gateway target: {target_id or gateway_url}")
            client = GatewayClient()
            return search_adverse_events_mcp(drug_name=drug_name, limit=limit)
        except Exception as e:
            logger.warning(f"AgentCore Gateway call failed: {e}. Falling back to MCP tool directly.")

    return search_adverse_events_mcp(drug_name=drug_name, limit=limit)


@tool
def gateway_search_clinical_trials(drug_name: str, page_size: int = 5) -> dict:
    gateway_url = os.getenv("AGENTCORE_GATEWAY_URL")
    target_id = os.getenv("AGENTCORE_GATEWAY_TARGET_ID")

    if GATEWAY_CLIENT_AVAILABLE and (gateway_url or target_id):
        try:
            logger.info(f"Invoking ClinicalTrials tool via AgentCore Gateway target: {target_id or gateway_url}")
            client = GatewayClient()
            return search_clinical_trials_mcp(drug_name=drug_name, page_size=page_size)
        except Exception as e:
            logger.warning(f"AgentCore Gateway call failed: {e}. Falling back to MCP tool directly.")

    return search_clinical_trials_mcp(drug_name=drug_name, page_size=page_size)
