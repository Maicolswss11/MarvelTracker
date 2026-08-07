-- MarvelTracker: profili e stato sincronizzato.
-- Eseguire questo file nel SQL Editor di Supabase prima di attivare il frontend.

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default 'Lettore Marvel' check (char_length(display_name) between 1 and 40),
  avatar_color text not null default '#ed1d24',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.tracker_states (
  user_id uuid primary key references auth.users(id) on delete cascade,
  state jsonb not null default '{}'::jsonb,
  client_updated_at timestamptz,
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.tracker_states enable row level security;

drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own" on public.profiles for select to authenticated using ((select auth.uid()) = id);
drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own" on public.profiles for update to authenticated using ((select auth.uid()) = id) with check ((select auth.uid()) = id);

drop policy if exists "tracker_states_select_own" on public.tracker_states;
create policy "tracker_states_select_own" on public.tracker_states for select to authenticated using ((select auth.uid()) = user_id);
drop policy if exists "tracker_states_insert_own" on public.tracker_states;
create policy "tracker_states_insert_own" on public.tracker_states for insert to authenticated with check ((select auth.uid()) = user_id);
drop policy if exists "tracker_states_update_own" on public.tracker_states;
create policy "tracker_states_update_own" on public.tracker_states for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
drop policy if exists "tracker_states_delete_own" on public.tracker_states;
create policy "tracker_states_delete_own" on public.tracker_states for delete to authenticated using ((select auth.uid()) = user_id);

grant select, update on table public.profiles to authenticated;
grant select, insert, update, delete on table public.tracker_states to authenticated;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at before update on public.profiles for each row execute function public.set_updated_at();
drop trigger if exists tracker_states_set_updated_at on public.tracker_states;
create trigger tracker_states_set_updated_at before update on public.tracker_states for each row execute function public.set_updated_at();

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(nullif(trim(new.raw_user_meta_data ->> 'display_name'), ''), split_part(new.email, '@', 1)));
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users for each row execute function public.handle_new_user();
