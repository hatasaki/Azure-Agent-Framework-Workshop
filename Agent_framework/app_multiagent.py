import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request

from agent_framework import ChatAgent, SequentialBuilder, AgentExecutor
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

WRITER_NAME = os.environ.get("WORKSHOP_WRITER_AGENT_NAME", "WorkshopWriter")
REVIEWER_NAME = os.environ.get("WORKSHOP_REVIEWER_AGENT_NAME", "WorkshopReviewer")
WRITER_INSTRUCTIONS = os.environ.get(
    "WORKSHOP_WRITER_INSTRUCTIONS",
    (
        "最新の調査結果とレビューコメントを統合して、日本語で非専門家にも分かりやすいレポートを作成してください。"
        "構成は必ず『概要』『最新動向』『課題』『推奨事項』の見出しを含め、最新情報の出典や根拠を簡潔に明記します。"
        "レビューの指摘がある場合は必ず内容に反映し、明瞭で論理的な文章に整えてください。"
    ),
)
REVIEWER_INSTRUCTIONS = os.environ.get(
    "WORKSHOP_REVIEWER_INSTRUCTIONS",
    (
        "レポート案の論理性、最新性、非専門家への分かりやすさを検証してください。"
        "不足している重要ポイントや曖昧な表現があれば指摘し、改善のための箇条書きフィードバックを簡潔に提示します。"
        "指摘は敬意を持った日本語で記述し、Writerが修正しやすい具体的な提案を含めてください。"
    ),
)

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
            researcher_agent: ChatAgent = ChatAgent(chat_client=client, name=AGENT_NAME)
        else:
            client = AzureAIAgentClient(**base_client_kwargs)
            researcher_agent = client.create_agent(
                name=AGENT_NAME,
                instructions=AGENT_INSTRUCTIONS if AGENT_INSTRUCTIONS else None,
            )

        # Create writer and reviewer agents
        writer_agent = client.create_agent(
            name=WRITER_NAME,
            instructions=WRITER_INSTRUCTIONS if WRITER_INSTRUCTIONS else None,
        )
        reviewer_agent = client.create_agent(
            name=REVIEWER_NAME,
            instructions=REVIEWER_INSTRUCTIONS if REVIEWER_INSTRUCTIONS else None,
        )

        executors: List[AgentExecutor] = []
        agent_flow = [researcher_agent, writer_agent, reviewer_agent, writer_agent, reviewer_agent, writer_agent]
        for i, agent in enumerate(agent_flow):
            executors.append(AgentExecutor(agent, id=f"agent_{i}"))

        # Build sequential workflow
        workflow = SequentialBuilder().participants(executors).build()

        response = await workflow.run(message)
        outputs = response.get_outputs()
        final_response = outputs[-1]

        # Keep newly created agents alive so follow-up turns can reuse them.
        if created_new_agent and hasattr(client, "_should_delete_agent"):
            client._should_delete_agent = False  # type: ignore[attr-defined]

        agent_id_result = client.agent_id
        if not agent_id_result:
            raise RuntimeError("Azure agent id was not assigned by the service")

        final_reply = ""
        if isinstance(final_response, list):
            for message in reversed(final_response):
                text_value = getattr(message, "text", None)
                if text_value:
                    final_reply = text_value
                    break
                contents = getattr(message, "contents", None)
                if contents:
                    for content in reversed(contents):
                        content_text = getattr(content, "text", None)
                        if content_text:
                            final_reply = content_text
                            break
                    if final_reply:
                        break
        else:
            final_reply = getattr(final_response, "text", None) or str(final_response)

        final_reply = final_reply or str(final_response)
        #print("Final response:", final_reply)

        return {
            "reply": final_reply,
            "agentId": agent_id_result,
            "thread": "",
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
