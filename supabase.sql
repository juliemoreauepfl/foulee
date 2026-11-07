-- Table de sauvegarde de Foulée.
-- À coller dans Supabase › SQL Editor › New query, puis « Run ».

create table if not exists public.foulee (
  cle    text primary key,
  valeur jsonb not null,
  maj    timestamptz not null default now()
);

-- Sécurité : RLS activé SANS aucune règle → personne ne peut lire la table de l'extérieur…
alter table public.foulee enable row level security;

-- …sauf ta clé secrète (rôle service_role), utilisée par l'app.
-- Nécessaire si « Automatically expose new tables » est décoché (recommandé).
grant select, insert, update, delete on table public.foulee to service_role;
