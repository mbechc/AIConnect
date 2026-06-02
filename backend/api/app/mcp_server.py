import atexit
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import paho.mqtt.client as mqtt
from mcp.server.fastmcp import FastMCP
from psycopg.rows import dict_row

from app.config import settings
from app.db import close_pool, ensure_mqtt_service_credentials, open_pool, pool
from app.device_reset import request_factory_reset
from app.mqtt import session_topic
from app.routes.devices import add_presence
from app.serial_audit import decode_base64, encode_text, find_active_session, log_serial_event, log_serial_payload


mcp = FastMCP("AI Connect", json_response=True, host=settings.mcp_host, port=settings.mcp_port)


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def hash_claim_code(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode("utf-8")).hexdigest()


def publish_mqtt(topic: str, payload: dict[str, Any]) -> dict[str, Any]:
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"{settings.mqtt_mcp_client_id}-{secrets.token_hex(3)}",
        clean_session=True,
    )
    client.username_pw_set(settings.mqtt_backend_username, settings.mqtt_backend_password)
    client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=30)
    client.loop_start()
    try:
        result = client.publish(topic, json.dumps(payload), qos=1, retain=False)
        result.wait_for_publish(timeout=5)
    finally:
        client.loop_stop()
        client.disconnect()
    return {"topic": topic, "published": result.is_published(), "rc": result.rc}


@mcp.tool()
def platform_summary() -> dict[str, Any]:
    """Show backend readiness, onboarding counts, and device health summary."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("select count(*) as count from organizations")
            organizations = cur.fetchone()["count"]
            cur.execute("select count(*) as count from sites")
            sites = cur.fetchone()["count"]
            cur.execute("select state, count(*) as count from devices group by state order by state")
            device_states = list(cur.fetchall())
            cur.execute("select state, count(*) as count from claim_codes group by state order by state")
            claim_states = list(cur.fetchall())
            cur.execute(
                """
                select count(*) as count
                from devices
                where state = 'claimed'
                  and last_seen_at >= now() - make_interval(secs => %s)
                """,
                (settings.device_online_freshness_seconds,),
            )
            online_devices = cur.fetchone()["count"]
    return jsonable(
        {
            "organizations": organizations,
            "sites": sites,
            "device_states": device_states,
            "claim_code_states": claim_states,
            "online_devices": online_devices,
            "online_freshness_seconds": settings.device_online_freshness_seconds,
            "public_base_url": settings.public_base_url,
        }
    )


@mcp.tool()
def create_organization(name: str) -> dict[str, Any]:
    """Create an organization that can own sites and devices."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "insert into organizations (name) values (%s) returning id, name, created_at",
                (name,),
            )
            return jsonable(cur.fetchone())


@mcp.tool()
def list_organizations() -> list[dict[str, Any]]:
    """List organizations."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("select id, name, created_at from organizations order by created_at desc limit 200")
            return jsonable(list(cur.fetchall()))


@mcp.tool()
def rename_organization(organization_id: str, name: str) -> dict[str, Any]:
    """Rename an existing organization without moving devices or sites."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                update organizations
                set name = %s
                where id = %s
                returning id, name, created_at
                """,
                (name, organization_id),
            )
            row = cur.fetchone()
    if row is None:
        return {"error": "organization-not-found"}
    return jsonable(row)


@mcp.tool()
def create_site(organization_id: str, name: str) -> dict[str, Any]:
    """Create a site under an organization for device onboarding."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("select id from organizations where id = %s", (organization_id,))
            if cur.fetchone() is None:
                return {"error": "organization-not-found"}
            cur.execute(
                """
                insert into sites (organization_id, name)
                values (%s, %s)
                returning id, organization_id, name, created_at
                """,
                (organization_id, name),
            )
            return jsonable(cur.fetchone())


@mcp.tool()
def rename_site(site_id: str, name: str) -> dict[str, Any]:
    """Rename an existing site without moving attached devices or claim codes."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                update sites
                set name = %s
                where id = %s
                returning id, organization_id, name, created_at
                """,
                (name, site_id),
            )
            row = cur.fetchone()
    if row is None:
        return {"error": "site-not-found"}
    return jsonable(row)


@mcp.tool()
def list_sites(organization_id: str | None = None) -> list[dict[str, Any]]:
    """List sites, optionally filtered by organization."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if organization_id:
                cur.execute(
                    """
                    select s.id, s.organization_id, o.name as organization_name, s.name, s.created_at
                    from sites s
                    join organizations o on o.id = s.organization_id
                    where s.organization_id = %s
                    order by s.created_at desc
                    limit 500
                    """,
                    (organization_id,),
                )
            else:
                cur.execute(
                    """
                    select s.id, s.organization_id, o.name as organization_name, s.name, s.created_at
                    from sites s
                    join organizations o on o.id = s.organization_id
                    order by s.created_at desc
                    limit 500
                    """
                )
            return jsonable(list(cur.fetchall()))


@mcp.tool()
def create_claim_code(site_id: str, expires_in_hours: int = 24, note: str | None = None) -> dict[str, Any]:
    """Create a random one-time device claim code for a site."""
    if expires_in_hours < 1 or expires_in_hours > 24 * 30:
        return {"error": "expires-in-hours-out-of-range"}

    code = f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("select id from sites where id = %s", (site_id,))
            if cur.fetchone() is None:
                return {"error": "site-not-found"}
            cur.execute(
                """
                insert into claim_codes (code_hash, site_id, expires_at, note)
                values (%s, %s, %s, %s)
                returning id, state, site_id, expires_at, note, created_at
                """,
                (hash_claim_code(code), site_id, expires_at, note),
            )
            row = cur.fetchone()
            cur.execute(
                """
                insert into audit_events (actor_type, action, target_type, target_id, payload_json)
                values ('mcp', 'claim_code.created', 'claim_code', %s, %s::jsonb)
                """,
                (str(row["id"]), json.dumps({"site_id": site_id})),
            )
            return jsonable({"code": code, **row})


@mcp.tool()
def list_claim_codes(site_id: str | None = None) -> list[dict[str, Any]]:
    """List claim codes without exposing the secret code material."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if site_id:
                cur.execute(
                    """
                    select id, state, site_id, expires_at, used_by_device_id, used_at, note, created_at
                    from claim_codes
                    where site_id = %s
                    order by created_at desc
                    limit 200
                    """,
                    (site_id,),
                )
            else:
                cur.execute(
                    """
                    select id, state, site_id, expires_at, used_by_device_id, used_at, note, created_at
                    from claim_codes
                    order by created_at desc
                    limit 200
                    """
                )
            return jsonable(list(cur.fetchall()))


@mcp.tool()
def list_devices(presence: str | None = None) -> list[dict[str, Any]]:
    """List devices with derived online/stale presence."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("select * from devices order by created_at desc limit 500")
            now = datetime.now(timezone.utc)
            rows = [add_presence(row, now) for row in cur.fetchall()]
    if presence:
        rows = [row for row in rows if row["presence"] == presence]
    return jsonable(rows)


@mcp.tool()
def get_device(device_id: str) -> dict[str, Any]:
    """Get one device with derived presence information."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("select * from devices where device_id = %s", (device_id,))
            row = cur.fetchone()
    if row is None:
        return {"error": "device-not-found"}
    return jsonable(add_presence(row))


@mcp.tool()
def disable_device(device_id: str) -> dict[str, Any]:
    """Disable a claimed device so it can no longer be treated as active."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "update devices set state = 'disabled', updated_at = now() where device_id = %s returning *",
                (device_id,),
            )
            row = cur.fetchone()
    if row is None:
        return {"error": "device-not-found"}
    return jsonable(add_presence(row))


@mcp.tool()
def request_device_factory_reset(
    device_id: str,
    reason: str | None = None,
    delete_record: bool = False,
) -> dict[str, Any]:
    """Revoke a device, invalidate credentials, close sessions, and publish factory reset if online."""
    return jsonable(
        request_factory_reset(
            device_id=device_id,
            reason=reason,
            delete_record=delete_record,
            actor_type="mcp",
        )
    )


@mcp.tool()
def open_serial_session(
    device_id: str,
    baud: int = 9600,
    data_bits: int = 8,
    parity: str = "none",
    stop_bits: int = 1,
    flow_control: str = "none",
) -> dict[str, Any]:
    """Open a serial session request for a claimed device and publish it to MQTT."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("select id from devices where device_id = %s and state = 'claimed'", (device_id,))
            if cur.fetchone() is None:
                return {"error": "claimed-device-not-found"}
            cur.execute(
                """
                select id from serial_sessions
                where device_id = %s and state in ('opening', 'active')
                limit 1
                """,
                (device_id,),
            )
            if cur.fetchone() is not None:
                return {"error": "device-already-has-active-session"}
            cur.execute(
                """
                insert into serial_sessions (device_id, state, baud, data_bits, parity, stop_bits, flow_control)
                values (%s, 'opening', %s, %s, %s, %s, %s)
                returning *
                """,
                (device_id, baud, data_bits, parity, stop_bits, flow_control),
            )
            session = cur.fetchone()
            log_serial_event(
                cur,
                session["id"],
                device_id,
                "session.open_requested",
                actor_type="mcp",
                metadata={
                    "baud": baud,
                    "data_bits": data_bits,
                    "parity": parity,
                    "stop_bits": stop_bits,
                    "flow_control": flow_control,
                },
            )

    topic = session_topic(device_id, str(session["id"]), "open")
    publish = publish_mqtt(
        topic,
        {
            "session_id": str(session["id"]),
            "device_id": device_id,
            "baud": baud,
            "data_bits": data_bits,
            "parity": parity,
            "stop_bits": stop_bits,
            "flow_control": flow_control,
        },
    )
    return jsonable({**session, "mqtt": publish})


@mcp.tool()
def send_serial_text(session_id: str, text: str, seq: int | None = None) -> dict[str, Any]:
    """Send text to a serial session behind the bridge."""
    data_base64, _data = encode_text(text)
    return send_serial_base64(session_id, data_base64, seq)


@mcp.tool()
def send_serial_base64(session_id: str, data_base64: str, seq: int | None = None) -> dict[str, Any]:
    """Send base64-encoded bytes to a serial session behind the bridge."""
    try:
        decoded = decode_base64(data_base64)
    except ValueError:
        return {"error": "invalid-base64"}

    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            session = find_active_session(cur, session_id)
            if session is None:
                return {"error": "active-session-not-found"}
            log_row = log_serial_payload(
                cur,
                session_id,
                session["device_id"],
                "tx",
                data_base64,
                actor_type="mcp",
                metadata={"seq": seq},
            )

    topic = session_topic(session["device_id"], session_id, "tx")
    publish = publish_mqtt(topic, {"session_id": session_id, "data_base64": data_base64, "seq": seq})
    return jsonable({**log_row, "byte_count": len(decoded), "seq": seq, "mqtt": publish})


@mcp.tool()
def close_serial_session(session_id: str, reason: str = "mcp-request") -> dict[str, Any]:
    """Close a serial session and publish the close request to the device."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                update serial_sessions
                set state = 'closing', close_reason = %s, updated_at = now()
                where id = %s
                  and state in ('opening', 'active')
                  and exists (
                    select 1
                    from devices
                    where devices.device_id = serial_sessions.device_id
                      and devices.state = 'claimed'
                  )
                returning *
                """,
                (reason, session_id),
            )
            session = cur.fetchone()
            if session is not None:
                log_serial_event(
                    cur,
                    session_id,
                    session["device_id"],
                    "session.close_requested",
                    actor_type="mcp",
                    metadata={"reason": reason},
                )
    if session is None:
        return {"error": "active-session-not-found"}

    topic = session_topic(session["device_id"], session_id, "close")
    publish = publish_mqtt(topic, {"session_id": session_id, "reason": reason})
    return jsonable({**session, "mqtt": publish})


@mcp.tool()
def get_session_log(session_id: str, limit: int = 200) -> list[dict[str, Any]]:
    """Read recent serial session log entries."""
    limit = max(1, min(limit, 1000))
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select id, session_id, device_id, actor_type, actor_id, direction,
                       payload_base64, payload_text_preview, byte_count, metadata_json, created_at
                from serial_session_logs
                where session_id = %s
                order by created_at desc, id desc
                limit %s
                """,
                (session_id, limit),
            )
            return jsonable(list(cur.fetchall()))


if __name__ == "__main__":
    open_pool()
    ensure_mqtt_service_credentials()
    atexit.register(close_pool)
    mcp.run(transport="streamable-http")
