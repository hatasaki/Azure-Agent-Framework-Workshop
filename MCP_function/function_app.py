import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import azure.functions as func

app = func.FunctionApp()

_tool_properties_timezone = json.dumps(
    [
        {
            "propertyName": "timezone",
            "propertyType": "string",
            "description": "IANA timezone identifier such as 'Asia/Tokyo' or 'America/New_York'.",
            "required": True,
        }
    ]
)


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="current_time",
    description="Return the current time for the requested IANA timezone.",
    toolProperties=_tool_properties_timezone,
)
def current_time_tool(context: str) -> str:
    """Return the current time in the requested timezone for MCP clients."""
    if not context:
        return _build_error("missing_context", "Trigger context payload was empty.")

    try:
        payload = json.loads(context)
    except json.JSONDecodeError:
        logging.warning("Received malformed MCP context: %s", context)
        return _build_error("invalid_context", "Trigger context must be valid JSON.")

    arguments = payload.get("arguments") or {}
    timezone_name = arguments.get("timezone")

    if not timezone_name:
        return _build_error(
            "missing_timezone",
            "Provide the 'timezone' argument using an IANA timezone like 'Asia/Tokyo'.",
        )

    try:
        tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        logging.info("Timezone not found: %s", timezone_name)
        return _build_error(
            "unknown_timezone",
            f"Timezone '{timezone_name}' is not recognized. Use a valid IANA timezone identifier.",
        )

    current_time = datetime.now(tz)
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S %Z")

    result = {
        "timezone": timezone_name,
        "currentTimeIso": current_time.isoformat(),
        "currentTimeDisplay": formatted_time,
        "note": "Time generated with Python zoneinfo based on system tzdata.",
    }

    return json.dumps(result)


def _build_error(code: str, message: str) -> str:
    """Return a consistent error payload for MCP tool responses."""
    return json.dumps({"error": code, "message": message})
