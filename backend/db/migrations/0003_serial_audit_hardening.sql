alter table serial_session_logs
  add column if not exists device_id text,
  add column if not exists actor_type text,
  add column if not exists actor_id text,
  add column if not exists metadata_json jsonb not null default '{}'::jsonb;

update serial_session_logs l
set device_id = s.device_id
from serial_sessions s
where l.session_id = s.id
  and l.device_id is null;

update serial_session_logs
set actor_type = case
  when direction = 'rx' then 'device'
  else 'unknown'
end
where actor_type is null;

create index if not exists serial_session_logs_device_created_idx
  on serial_session_logs(device_id, created_at);

create index if not exists serial_session_logs_actor_created_idx
  on serial_session_logs(actor_type, actor_id, created_at);
