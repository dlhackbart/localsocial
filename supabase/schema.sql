-- Local Social — Supabase schema (MVP, device-ID based, no auth yet)
-- Run in Supabase SQL editor.

create table if not exists public.users (
  device_id     text primary key,
  created_at    timestamptz not null default now(),
  plan          text not null default 'free' check (plan in ('free','paid'))
);

create table if not exists public.preferences (
  device_id     text primary key references public.users(device_id) on delete cascade,
  home_area     text not null,
  enabled_zones text[] not null default '{}',
  goal          text not null check (goal in ('dating','social','both')),
  vibe          text not null check (vibe in ('quiet','balanced','high')),
  updated_at    timestamptz not null default now()
);

create table if not exists public.logs (
  id              text primary key,
  device_id       text not null references public.users(device_id) on delete cascade,
  date            date not null,
  went_out        boolean not null,
  venue           text not null,
  crowd_grade     text check (crowd_grade in ('A','B','C')),
  would_go_again  text check (would_go_again in ('yes','maybe','no')),
  created_at      timestamptz not null default now()
);

create index if not exists logs_device_date_idx on public.logs (device_id, date desc);

create table if not exists public.venues (
  id                    bigserial primary key,
  name                  text not null,
  area                  text not null,
  repeat_friendly       boolean not null default false,
  conversation_friendly boolean not null default false,
  energy                text not null check (energy in ('low','medium','high')),
  low_social_value      boolean not null default false,
  unique (name, area)
);

create table if not exists public.events (
  id            bigserial primary key,
  venue_id      bigint not null references public.venues(id) on delete cascade,
  day           text not null check (day in ('Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday')),
  type          text not null,
  time          text not null,
  broad_appeal  boolean not null default false
);

-- Crowdsourced iCal source registry — one row per (area, url).
-- Populated by rule-based probes, LLM discovery, and user submissions.
create table if not exists public.sources (
  id                    bigserial primary key,
  area_slug             text not null,       -- lowercase, normalized: "bend-or", "del-mar-ca"
  area_label            text not null,       -- human-readable: "Bend, OR"
  name                  text not null,
  url                   text not null,
  default_category      text not null check (default_category in (
    'hiking_outdoor','classes_workshops','community_civic','live_music_small',
    'art_galleries','food_drink','book_clubs','markets','theater_small',
    'movies_indie','meetups_clubs','wellness'
  )),
  intimate              boolean not null default true,
  conversation_friendly boolean not null default true,
  repeat_friendly       boolean not null default false,
  discovery_method      text not null check (discovery_method in ('probe','llm','user','seed')),
  contributed_by        text,                -- device_id when discovery_method = 'user'
  verified_at           timestamptz,
  last_fetch_ok         boolean not null default false,
  last_fetch_at         timestamptz,
  last_event_count      int not null default 0,
  created_at            timestamptz not null default now(),
  unique (area_slug, url)
);

create index if not exists sources_area_idx on public.sources (area_slug) where last_fetch_ok = true;

-- Tracks which areas have already been through discovery so we don't re-run it.
create table if not exists public.area_discovery (
  area_slug       text primary key,
  area_label      text not null,
  discovered_at   timestamptz not null default now(),
  sources_found   int not null default 0,
  method_used     text not null
);

alter table public.sources         enable row level security;
alter table public.area_discovery  enable row level security;

drop policy if exists "mvp_read_sources"           on public.sources;
drop policy if exists "mvp_insert_sources"         on public.sources;
drop policy if exists "mvp_read_area_discovery"    on public.area_discovery;

create policy "mvp_read_sources"        on public.sources        for select using (true);
create policy "mvp_insert_sources"      on public.sources        for insert with check (true);
create policy "mvp_read_area_discovery" on public.area_discovery for select using (true);
-- Writes to sources and area_discovery during auto-discovery go through the
-- Edge Function using the service role key, which bypasses RLS.

-- RLS: permissive for MVP (device_id-based, no auth).
-- Tighten once real auth lands.
alter table public.users       enable row level security;
alter table public.preferences enable row level security;
alter table public.logs        enable row level security;
alter table public.venues      enable row level security;
alter table public.events      enable row level security;

drop policy if exists "mvp_open_users"       on public.users;
drop policy if exists "mvp_open_preferences" on public.preferences;
drop policy if exists "mvp_open_logs"        on public.logs;
drop policy if exists "mvp_read_venues"      on public.venues;
drop policy if exists "mvp_read_events"      on public.events;

create policy "mvp_open_users"       on public.users       for all using (true) with check (true);
create policy "mvp_open_preferences" on public.preferences for all using (true) with check (true);
create policy "mvp_open_logs"        on public.logs        for all using (true) with check (true);
create policy "mvp_read_venues"      on public.venues      for select using (true);
create policy "mvp_read_events"      on public.events      for select using (true);
