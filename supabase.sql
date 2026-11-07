-- Table de sauvegarde de Foulée.
-- À coller dans Supabase › SQL Editor › New query, puis « Run ».

create table if not exists public.foulee (
  cle    text primary key,
  valeur jsonb not null,
  maj    timestamptz not null default now()
);

-- Sécurité : on active RLS SANS aucune règle.
-- Résultat : personne ne peut lire la table depuis l'extérieur,
-- seule ta clé secrète (rangée dans les secrets Streamlit) y a accès.
alter table public.foulee enable row level security;
