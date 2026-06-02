create table if not exists organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

alter table sites
  add column if not exists organization_id uuid references organizations(id);

create index if not exists sites_organization_idx on sites(organization_id);
create index if not exists claim_codes_site_idx on claim_codes(site_id);

create unique index if not exists devices_efuse_mac_claimed_idx
  on devices(efuse_mac)
  where state in ('claimed', 'disabled', 'revoked');
