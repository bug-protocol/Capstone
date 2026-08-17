import json
import os
import logging
from typing import Dict, Any, Optional, List, Union
from dotenv import load_dotenv

# Ensure environment variables from .env are loaded
load_dotenv()

from strands.session import FileSessionManager

try:
    from bedrock_agentcore.memory import MemoryClient
    from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
    from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
    BEDROCK_MEMORY_AVAILABLE = True
except ImportError:
    BEDROCK_MEMORY_AVAILABLE = False

logger = logging.getLogger("capstone.memory")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSIONS_DIR = os.path.join(BASE_DIR, "data", "sessions")
LTM_FILE_PATH = os.path.join(BASE_DIR, "data", "ltm_store.json")


class LongTermMemoryStore:

    def __init__(self, file_path: str = LTM_FILE_PATH):
        self.file_path = file_path
        self._ensure_file()

    def _ensure_file(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({
                    "sample-user-001": {
                        "allergies": ["Penicillin", "Macrolide antibiotics"],
                        "chronic_conditions": ["Type 2 Diabetes", "Mild Hypertension"],
                        "role": "Clinician (Internal Medicine)"
                    }
                }, f, indent=2)

    def _read_data(self) -> Dict[str, Any]:
        self._ensure_file()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_data(self, data: Dict[str, Any]):
        self._ensure_file()
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_actor_facts(
        self,
        actor_id: str,
        query: str = "user profile, drug allergies, medical conditions, clinical role"
    ) -> Union[Dict[str, Any], List[Any]]:
        memory_id = os.getenv("AGENTCORE_MEMORY_ID")
        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
        
        # 1. Attempt retrieval from AWS Bedrock AgentCore Memory
        if BEDROCK_MEMORY_AVAILABLE and memory_id:
            try:
                client = MemoryClient(region_name=region)
                records = client.retrieve_memories(
                    memory_id=memory_id,
                    namespace_path=f"/{actor_id}/",
                    query=query,
                    top_k=5,
                )
                if records:
                    logger.info(f"Retrieved {len(records)} memory records from AWS AgentCore Memory for actor '{actor_id}'")
                    return records
            except Exception as e:
                logger.warning(f"Could not fetch AgentCore Memory LTM from AWS: {e}. Using local store.")

        # 2. Fallback to local store
        data = self._read_data()
        return data.get(actor_id, {})

    def set_actor_fact(self, actor_id: str, key: str, value: Any, session_id: str = "ltm-profile"):
        # 1. Save locally
        data = self._read_data()
        if actor_id not in data:
            data[actor_id] = {}
        data[actor_id][key] = value
        self._write_data(data)

        # 2. Persist to AWS Bedrock AgentCore Memory if configured
        memory_id = os.getenv("AGENTCORE_MEMORY_ID")
        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
        if BEDROCK_MEMORY_AVAILABLE and memory_id:
            try:
                client = MemoryClient(region_name=region)
                val_str = ", ".join(str(x) for x in value) if isinstance(value, list) else str(value)
                client.create_event(
                    memory_id=memory_id,
                    actor_id=actor_id,
                    session_id=session_id,
                    messages=[
                        ("user", f"Patient/User Fact Update - {key}: {val_str}"),
                        ("assistant", f"Acknowledged. Updated persistent profile record for {key} = {val_str}")
                    ]
                )
                logger.info(f"Persisted memory fact '{key}' for actor '{actor_id}' to AWS AgentCore Memory ID: {memory_id}")
            except Exception as e:
                logger.warning(f"Could not push fact to AWS Bedrock AgentCore Memory: {e}")

    def format_ltm_context(self, actor_id: str) -> str:
        facts = self.get_actor_facts(actor_id)
        if not facts:
            return ""
        
        lines = []
        if isinstance(facts, dict):
            for k, v in facts.items():
                formatted_key = k.replace("_", " ").title()
                if isinstance(v, list):
                    lines.append(f"- {formatted_key}: {', '.join(str(x) for x in v)}")
                else:
                    lines.append(f"- {formatted_key}: {v}")
        elif isinstance(facts, list):
            for item in facts:
                if isinstance(item, dict):
                    # AgentCore memory record structure parsing
                    content = item.get("content") or item.get("text") or item.get("fact") or str(item)
                    if isinstance(content, dict):
                        content = content.get("text") or str(content)
                    lines.append(f"- {content}")
                else:
                    lines.append(f"- {item}")
        else:
            lines.append(f"- {str(facts)}")
                
        return "\n\n[Durable User Profile & Long-Term Memory (LTM)]:\n" + "\n".join(lines)


ltm_store = LongTermMemoryStore()


def get_short_term_session_manager(session_id: str, actor_id: str = "default-user"):
    """
    Returns an AWS Bedrock AgentCoreMemorySessionManager when AGENTCORE_MEMORY_ID is configured,
    otherwise gracefully falls back to local FileSessionManager.
    """
    memory_id = os.getenv("AGENTCORE_MEMORY_ID")
    
    if BEDROCK_MEMORY_AVAILABLE and memory_id:
        try:
            config = AgentCoreMemoryConfig(
                memory_id=memory_id,
                session_id=session_id,
                actor_id=actor_id,
            )
            region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
            logger.info(f"Initializing AWS AgentCoreMemorySessionManager (Memory ID: {memory_id}, Region: {region}, Session: {session_id})")
            return AgentCoreMemorySessionManager(agentcore_memory_config=config, region_name=region)
        except Exception as e:
            logger.warning(f"AgentCore MemorySessionManager init failed ({e}). Falling back to FileSessionManager.")

    os.makedirs(SESSIONS_DIR, exist_ok=True)
    return FileSessionManager(session_id=session_id, storage_dir=SESSIONS_DIR)
