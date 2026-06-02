create extension if not exists pgcrypto;

create table if not exists sites (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

create table if not exists devices (
  id uuid primary key default gen_random_uuid(),
  device_id text not null unique,
  efuse_mac text not null unique,
  display_name text,
  state text not null default 'unclaimed' check (state in ('unclaimed', 'claimed', 'disabled', 'revoked')),
  site_id uuid references sites(id),
  firmware_version text,
  hardware_model text not null default 'm5atom-lite-rs232',
  serial_baud_default integer not null default 9600,
  mqtt_username text unique,
  mqtt_password_hash text,
  certificate_fingerprint text,
  first_seen_at timestamptz,
  last_seen_at timestamptz,
  claimed_at timestamptz default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists claim_codes (
  id uuid primary key default gen_random_uuid(),
  code_hash text not null unique,
  state text not null default 'unused' check (state in ('unused', 'used', 'expired', 'revoked')),
  site_id uuid references sites(id),
  expires_at timestamptz not null,
  used_by_device_id text references devices(device_id),
  used_at timestamptz,
  note text,
  created_at timestamptz not null default now()
);

create table if not exists device_events (
  id bigserial primary key,
  device_id text not null references devices(device_id),
  event_type text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists serial_sessions (
  id uuid primary key default gen_random_uuid(),
  device_id text not null references devices(device_id),
  state text not null default 'opening' check (state in ('opening', 'active', 'closing', 'closed', 'failed')),
  baud integer not null default 9600,
  data_bits integer not null default 8,
  parity text not null default 'none',
  stop_bits integer not null default 1,
  flow_control text not null default 'none',
  opened_at timestamptz,
  closed_at timestamptz,
  close_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists serial_session_logs (
  id bigserial primary key,
  session_id uuid not null references serial_sessions(id) on delete cascade,
  direction text not null check (direction in ('rx', 'tx', 'event')),
  payload_base64 text,
  payload_text_preview text,
  byte_count integer not null default 0,
  created_at timestamptz not null default now()
);

create table if not exists audit_events (
  id bigserial primary key,
  actor_type text not null default 'api',
  actor_id text,
  action text not null,
  target_type text,
  target_id text,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists devices_state_idx on devices(state);
create index if not exists devices_last_seen_idx on devices(last_seen_at);
create index if not exists claim_codes_state_idx on claim_codes(state);
create index if not exists serial_sessions_device_state_idx on serial_sessions(device_id, state);
create index if not exists serial_session_logs_session_idx on serial_session_logs(session_id, created_at);
create index if not exists device_events_device_created_idx on device_events(device_id, created_at);
