import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request

from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential, DefaultAzureCredential
from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="")


def _get_required_setting(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. "
            "Set the value before calling the chat API."
        )
    return value


def _env_flag(name: str, default: str = "false") -> bool:
    value = os.environ.get(name, default)
    return value.strip().lower() in {"1", "true", "yes", "on"}


PROJECT_ENDPOINT_ENV = "AZURE_AI_PROJECT_ENDPOINT"
MODEL_DEPLOYMENT_ENV = "AZURE_AI_MODEL_DEPLOYMENT_NAME"
AGENT_NAME = os.environ.get("WORKSHOP_AGENT_NAME", "WorkshopAssistant")
AGENT_INSTRUCTIONS = os.environ.get(
    "WORKSHOP_AGENT_INSTRUCTIONS",
    "You are a helpful Japanese-speaking AI assistant for an Azure AI Foundry workshop.",
)
CREATE_NEW_AGENT = _env_flag("CREATE_NEW_AGENT", "true")

# MCP関連の環境変数
MCP_FUNCTION_URL = os.environ.get("MCP_FUNCTION_URL")
MCP_FUNCTION_KEY = os.environ.get("MCP_FUNCTION_KEY")


@asynccontextmanager
async def get_credential():
    """Yield an async credential, preferring Azure CLI when available."""
    prefer_cli = os.environ.get("USE_AZURE_CLI_CREDENTIAL", "true").lower() in {
        "1",
        "true",
        "yes",
    }
    credential = (
        AzureCliCredential()
        if prefer_cli
        else DefaultAzureCredential(exclude_interactive_browser_credential=False)
    )
    async with credential:
        yield credential


async def run_agent_interaction(
    message: str,
    *,
    incoming_agent_id: Optional[str] = None,
    serialized_thread: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    project_endpoint = _get_required_setting(PROJECT_ENDPOINT_ENV)
    model_deployment_name = _get_required_setting(MODEL_DEPLOYMENT_ENV)

    async with get_credential() as credential:
        base_client_kwargs = {
            "async_credential": credential,
            "project_endpoint": project_endpoint,
            "model_deployment_name": model_deployment_name,
        }
        agent_id_to_use: Optional[str] = incoming_agent_id
        if agent_id_to_use is None and not CREATE_NEW_AGENT:
            agent_id_to_use = _get_required_setting("WORKSHOP_AGENT_ID")

        created_new_agent = agent_id_to_use is None
        if agent_id_to_use:
            client = AzureAIAgentClient(agent_id=agent_id_to_use, **base_client_kwargs)
            chat_agent_manager: ChatAgent = ChatAgent(chat_client=client, name=AGENT_NAME)
        else:
            client = AzureAIAgentClient(**base_client_kwargs)
            chat_agent_manager = client.create_agent(
                name=AGENT_NAME,
                instructions=AGENT_INSTRUCTIONS if AGENT_INSTRUCTIONS else None,
            )

        mcp_tool = None
        if MCP_FUNCTION_URL:
            tool_kwargs = {
                "name": "Microsoft Docs MCP",
                "url": MCP_FUNCTION_URL,
            }
            # Functions キーがある場合のみヘッダーを付与する（公開Docs MCPには不要）
            if MCP_FUNCTION_KEY:
                tool_kwargs["headers"] = {"x-functions-key": MCP_FUNCTION_KEY}
            mcp_tool = MCPStreamableHTTPTool(**tool_kwargs)

        async with chat_agent_manager as agent:

            if serialized_thread:
                thread = await agent.deserialize_thread(serialized_thread)
            else:
                thread = agent.get_new_thread()
            # MCPツールがある場合は、それも含めてコンテキストマネージャーで管理
            if mcp_tool:
                response = await agent.run(message, thread=thread, tools=mcp_tool, store=True)
            else:
                response = await agent.run(message, thread=thread, store=True)

            # Keep newly created agents alive so follow-up turns can reuse them.
            if created_new_agent and hasattr(client, "_should_delete_agent"):
                client._should_delete_agent = False  # type: ignore[attr-defined]

            serialized = await thread.serialize()
            agent_id_result = client.agent_id
            if not agent_id_result:
                raise RuntimeError("Azure agent id was not assigned by the service")

            return {
                "reply": response.text,
                "agentId": agent_id_result,
                "thread": serialized,
            }


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    agent_id = payload.get("agentId")
    thread_state = payload.get("thread")

    try:
        result = asyncio.run(
            run_agent_interaction(
                message,
                incoming_agent_id=agent_id,
                serialized_thread=thread_state,
            )
        )
    except RuntimeError as exc:
        logger.exception("Configuration error: %s", exc)
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.exception("Agent call failed")
        return jsonify({"error": "Failed to contact Azure AI Agent", "details": str(exc)}), 502

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
