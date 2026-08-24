import os
import uuid
import boto3
import logging
from typing import Dict, Any, Optional, List, Union
from dotenv import load_dotenv
load_dotenv()

from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.integrations.strands.config import (
    AgentCoreMemoryConfig,
    RetrievalConfig
)
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager
)

logger = logging.getLogger("capstone.memory")

MEMORY_ID = (
    os.getenv("AGENTCORE_MEMORY_ID")
    or os.getenv("AGENTCORE_MEMORY_PHARMASENTRYAGENTMEMORY_ID")
    or os.getenv("MEMORY_PHARMASENTRYAGENTMEMORY_ID")
    or os.getenv("MEMORY_ID")
    or "capstone_agent_memory-I2PuWq9ZHm"
)
REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-south-1"

class LongTermMemoryStore:
    def __init__(self):
        self.memory_id = MEMORY_ID
        self.region = REGION

    def get_actor_facts(
        self,
        actor_id: Optional[str] = None,
        query: str = "user profile, drug allergies, medical conditions, clinical role",
        session_id: Optional[str] = None
    ) -> Union[Dict[str, Any], List[Any]]:
        actor_id = actor_id or os.getenv("AGENTCORE_ACTOR_ID") or "default-user"
        session_id = session_id or os.getenv("AGENTCORE_SESSION_ID") or "default-session"

        try:
            client = MemoryClient(region_name=self.region)
            strategies = client.get_memory_strategies(memory_id=self.memory_id) or []

            records = []
            for strategy in strategies:
                templates = strategy.get("namespaceTemplates") or strategy.get("namespaces") or []
                strategy_id = strategy.get("strategyId") or strategy.get("memoryStrategyId")
                for template in templates:
                    resolved_ns = template
                    resolved_ns = resolved_ns.replace("{memoryStrategyId}", str(strategy_id))
                    resolved_ns = resolved_ns.replace("{strategyId}", str(strategy_id))
                    resolved_ns = resolved_ns.replace("{actorId}", str(actor_id))
                    resolved_ns = resolved_ns.replace("{sessionId}", str(session_id))

                    # Normalize leading slash if needed
                    if not resolved_ns.startswith("/") and not resolved_ns.startswith("actors/"):
                        resolved_ns = "/" + resolved_ns

                    try:
                        strategy_records = client.retrieve_memories(
                            memory_id=self.memory_id,
                            namespace_path=resolved_ns,
                            query=query,
                            top_k=5,
                        )
                        if strategy_records:
                            records.extend(strategy_records)
                    except Exception as e:
                        logger.warning(
                            f"Could not fetch AgentCore Memory for strategy namespace '{resolved_ns}': {e}"
                        )

            return records

        except Exception as e:
            logger.error(
                f"Could not fetch AgentCore Memory LTM for actor '{actor_id}': {e}"
            )
            return []

    def set_actor_fact(
        self,
        actor_id: Optional[str] = None,
        key: Optional[str] = None,
        value: Any = None,
        session_id: Optional[str] = None
    ):
        actor_id = actor_id or os.getenv("AGENTCORE_ACTOR_ID") or "default-user"
        session_id = session_id or os.getenv("AGENTCORE_SESSION_ID") or "ltm-profile"

        try:
            client = MemoryClient(region_name=self.region)
            val_str = (
                ", ".join(str(x) for x in value)
                if isinstance(value, list)
                else str(value)
            )

            client.create_event(
                memory_id=self.memory_id,
                actor_id=actor_id,
                session_id=session_id,
                messages=[
                    (
                        f"Patient/User Fact Update - {key}: {val_str}",
                        "USER"
                    ),
                    (
                        f"Acknowledged. Updated persistent profile record for {key} = {val_str}",
                        "ASSISTANT"
                    )
                ]
            )

            logger.info(
                f"Persisted memory fact '{key}' for actor '{actor_id}' to AWS AgentCore Memory."
            )

        except Exception as e:
            logger.error(
                f"Could not push fact to AWS AgentCore Memory for actor '{actor_id}': {e}"
            )

    def format_ltm_context(self, actor_id: Optional[str] = None, session_id: Optional[str] = None) -> str:
        actor_id = actor_id or os.getenv("AGENTCORE_ACTOR_ID") or "default-user"
        session_id = session_id or os.getenv("AGENTCORE_SESSION_ID") or "default-session"
        facts = self.get_actor_facts(actor_id=actor_id, session_id=session_id)

        if not facts:
            return ""

        lines = []
        for item in facts:
            if isinstance(item, dict):
                content = (
                    item.get("content")
                    or item.get("text")
                    or item.get("fact")
                    or str(item)
                )
                if isinstance(content, dict):
                    content = content.get("text") or str(content)
                lines.append(f"- {content}")
            else:
                lines.append(f"- {item}")

        return (
            "\n\n[Durable User Profile & Long-Term Memory (LTM)]:\n"
            + "\n".join(lines)
        )

ltm_store = LongTermMemoryStore()

def get_memory_session_manager(
    session_id: Optional[str] = None,
    actor_id: Optional[str] = None
) -> Optional[AgentCoreMemorySessionManager]:
    if not MEMORY_ID or not actor_id or str(actor_id).strip().lower() in ("", "none", "null"):
        return None

    session_id = session_id or os.getenv("AGENTCORE_SESSION_ID") or uuid.uuid4().hex
    clean_actor = str(actor_id).strip()

    # Explicit strategy namespace configuration matching your AWS strategies
    retrieval_config = {
        f"/strategies/capstone_semantic-2CbrcO3j06/actors/{clean_actor}/": RetrievalConfig(top_k=5, relevance_score=0.2),
        f"/strategies/preference_builtin_2yg6b-YJnQu8GcEX/actors/{clean_actor}/": RetrievalConfig(top_k=5, relevance_score=0.2),
        f"/strategies/capstone_summary-925y3hHHx3/actors/{clean_actor}/sessions/{session_id}/": RetrievalConfig(top_k=5, relevance_score=0.2),
        f"actors/{clean_actor}/sessions/{session_id}/": RetrievalConfig(top_k=5, relevance_score=0.2),
        f"/actors/{clean_actor}/sessions/{session_id}/": RetrievalConfig(top_k=5, relevance_score=0.2),
        f"actors/{clean_actor}/": RetrievalConfig(top_k=5, relevance_score=0.2),
        f"/actors/{clean_actor}/": RetrievalConfig(top_k=5, relevance_score=0.2),
    }

    profile = os.getenv("AWS_PROFILE") or "default"
    try:
        boto_session = boto3.Session(
            profile_name=profile,
            region_name=REGION,
        )
    except Exception:
        boto_session = boto3.Session(
            region_name=REGION,
        )

    return AgentCoreMemorySessionManager(
        AgentCoreMemoryConfig(
            memory_id=MEMORY_ID,
            session_id=session_id,
            actor_id=clean_actor,
            retrieval_config=retrieval_config,
        ),
        region_name=REGION,
        boto_session=boto_session,
    )

def get_short_term_session_manager(
    session_id: Optional[str] = None,
    actor_id: Optional[str] = None
) -> Optional[AgentCoreMemorySessionManager]:
    return get_memory_session_manager(session_id=session_id, actor_id=actor_id)