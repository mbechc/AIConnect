create table if not exists mqtt_service_credentials (
  username text primary key,
  password_hash text not null,
  role text not null check (role in ('backend', 'provisioning')),
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace view mqtt_auth_users as
select username, password_hash, ''::text as salt, false as is_superuser
from mqtt_service_credentials
where enabled
union all
select mqtt_username as username, mqtt_password_hash as password_hash, ''::text as salt, false as is_superuser
from devices
where state = 'claimed'
  and mqtt_username is not null
  and mqtt_password_hash is not null;

create or replace view mqtt_acl_rules as
select username, 'allow'::text as permission, 'all'::text as action, 'aic/v1/#'::text as topic
from mqtt_service_credentials
where enabled and role = 'backend'

union all
select username, 'allow', 'publish', 'aic/v1/claim/request'
from mqtt_service_credentials
where enabled and role = 'provisioning'

union all
select username, 'allow', 'subscribe', 'aic/v1/claim/response/${clientid}'
from mqtt_service_credentials
where enabled and role = 'provisioning'

union all
select mqtt_username, 'allow', 'publish', topic
from devices
cross join (
  values
    ('aic/v1/devices/${username}/heartbeat'),
    ('aic/v1/devices/${username}/status'),
    ('aic/v1/devices/${username}/event'),
    ('aic/v1/devices/${username}/events'),
    ('aic/v1/devices/${username}/sessions/+/rx'),
    ('aic/v1/devices/${username}/sessions/+/opened'),
    ('aic/v1/devices/${username}/sessions/+/closed'),
    ('aic/v1/devices/${username}/sessions/+/event')
) as allowed(topic)
where state = 'claimed'
  and mqtt_username is not null
  and mqtt_password_hash is not null

union all
select mqtt_username, 'allow', 'subscribe', topic
from devices
cross join (
  values
    ('aic/v1/devices/${username}/config/set'),
    ('aic/v1/devices/${username}/commands/factory-reset'),
    ('aic/v1/devices/${username}/sessions/+/open'),
    ('aic/v1/devices/${username}/sessions/+/tx'),
    ('aic/v1/devices/${username}/sessions/+/close')
) as allowed(topic)
where state = 'claimed'
  and mqtt_username is not null
  and mqtt_password_hash is not null;
