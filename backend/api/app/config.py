from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    api_admin_token: str = "change-me-long-random-token"
    mqtt_host: str = "emqx"
    mqtt_port: int = 1883
    mqtt_tls_port: int = 8883
    mqtt_api_client_id: str = "aiconnect-controller"
    mqtt_device_events_client_id: str = "aiconnect-device-events"
    mqtt_mcp_client_id: str = "aiconnect-mcp"
    mqtt_backend_username: str = "aiconnect-backend"
    mqtt_backend_password: str = "change-me-backend-mqtt-password"
    mqtt_provisioning_username: str = "aiconnect-provisioning"
    mqtt_provisioning_password: str = "change-me-provisioning-mqtt-password"
    device_online_freshness_seconds: int = 120
    public_base_url: str = "https://mqtts.itego.dk"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8001

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
