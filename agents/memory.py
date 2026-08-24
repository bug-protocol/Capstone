import json
import os
import boto3
import logging
from typing import Dict, Any, Optional, List, Union
from dotenv import load_dotenv
load_dotenv()

from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager
)
from bedrock_agentcore.memory.integrations.strands.config import (
    AgentCoreMemoryConfig
)

logger = logging.getLogger("capstone.memory")   

class LongTermMemoryStore:
    def __init__(self):
        self.memory_id = os.getenv("AGENTCORE_MEMORY_ID")
        self.region = (
            os.getenv("AWS_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or "ap-south-1"
        )

        if not self.memory_id:
            raise ValueError(
                "AGENTCORE_MEMORY_ID is not configured."
            )
    
    def get_actor_facts(
        self,
        actor_id: str,
        query: str = "user profile, drug allergies, medical conditions, clinical role"
    ) -> Union[Dict[str, Any], List[Any]]:

        try:
            client = MemoryClient(region_name=self.region)

            records = client.retrieve_memories(
                memory_id=self.memory_id,
                namespace_path=f"/{actor_id}/",
                query=query,
                top_k=5,
            )

            if records:
                logger.info(
                    f"Retrieved {len(records)} memory records "
                    f"from AWS AgentCore Memory for actor '{actor_id}'"
                )

            return records or []

        except Exception as e:
            logger.error(
                f"Could not fetch AgentCore Memory LTM "
                f"for actor '{actor_id}': {e}"
            )
            return []

    def set_actor_fact(
        self,
        actor_id: str,
        key: str,
        value: Any,
        session_id: str = "ltm-profile"
    ):
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
                        "user",
                        f"Patient/User Fact Update - {key}: {val_str}"
                    ),
                    (
                        "assistant",
                        f"Acknowledged. Updated persistent profile "
                        f"record for {key} = {val_str}"
                    )
                ]
            )

            logger.info(
                f"Persisted memory fact '{key}' for actor "
                f"'{actor_id}' to AWS AgentCore Memory."
            )

        except Exception as e:
            logger.error(
                f"Could not push fact to AWS AgentCore Memory "
                f"for actor '{actor_id}': {e}"
            )

    def format_ltm_context(self, actor_id: str) -> str:
        facts = self.get_actor_facts(actor_id)

        if not facts:
            return ""

        lines = []

        if isinstance(facts, list):
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

        elif isinstance(facts, dict):
            for key, value in facts.items():
                formatted_key = key.replace("_", " ").title()

                if isinstance(value, list):
                    value = ", ".join(str(x) for x in value)

                lines.append(f"- {formatted_key}: {value}")

        else:
            lines.append(f"- {str(facts)}")

        return (
            "\n\n[Durable User Profile & Long-Term Memory (LTM)]:\n"
            + "\n".join(lines)
        )


ltm_store = LongTermMemoryStore()


def get_short_term_session_manager(
    session_id: str,
    actor_id: str = "default-user"
):
    boto_session = boto3.Session(
        profile_name = "default",
        region_name = ltm_store.region,
    )
    config = AgentCoreMemoryConfig(
        memory_id=ltm_store.memory_id,
        session_id=session_id,
        actor_id=actor_id,
    )

    logger.info(
        f"Initializing AWS AgentCoreMemorySessionManager "
        f"(Memory ID: {ltm_store.memory_id}, "
        f"Region: {ltm_store.region}, "
        f"Session: {session_id}, "
        f"Actor: {actor_id})"
    )

    return AgentCoreMemorySessionManager(
        agentcore_memory_config=config,
        region_name=ltm_store.region,
        boto_session=boto_session,
    )