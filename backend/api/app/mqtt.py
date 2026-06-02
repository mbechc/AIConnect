TOPIC_PREFIX = "aic/v1"


def claim_request_topic() -> str:
    return f"{TOPIC_PREFIX}/claim/request"


def claim_response_topic(device_id: str) -> str:
    return f"{TOPIC_PREFIX}/claim/response/{device_id}"


def device_status_topic(device_id: str) -> str:
    return f"{TOPIC_PREFIX}/devices/{device_id}/status"


def device_heartbeat_topic(device_id: str) -> str:
    return f"{TOPIC_PREFIX}/devices/{device_id}/heartbeat"


def device_factory_reset_topic(device_id: str) -> str:
    return f"{TOPIC_PREFIX}/devices/{device_id}/commands/factory-reset"


def session_topic(device_id: str, session_id: str, action: str) -> str:
    return f"{TOPIC_PREFIX}/devices/{device_id}/sessions/{session_id}/{action}"
