-- STEP C — paste into the Supabase SQL editor. Step B (the PostgREST apply)
-- completed on 2026-08-26 and was verified against live. This is the closing
-- gate of the canonical catalog migration.
--
-- It restores uniqueness to item_catalog, stricter than what step A dropped:
-- step A's constraint was unique on the literal (item_name, description), which
-- still allowed "GASOLINA 93" and "Gasolina 93" to coexist. This one is unique
-- on the NORMALIZED name, which is what D-044 actually requires.
--
-- Its success IS the proof. If any duplicate normalized name survived the
-- migration, this index cannot be created and the CREATE fails loudly naming
-- the collision. Do not force it through by dropping rows — investigate.

begin;

create unique index if not exists item_catalog_normalized_name_uidx
  on public.item_catalog (public.catalog_normalize_label(item_name));

do $$
begin
  if (select count(*) from public.item_catalog) <> 4029 then
    raise exception 'catalog count is %, expected 4029',
      (select count(*) from public.item_catalog);
  end if;
  if (select count(*) from public.invoice_items) <> 11746 then
    raise exception 'invoice line count is %, expected 11746',
      (select count(*) from public.invoice_items);
  end if;
  if (select count(*) from public.item_aliases) <> 8 then
    raise exception 'alias count is %, expected 8',
      (select count(*) from public.item_aliases);
  end if;
  if exists (
    select 1 from public.invoice_items i
    left join public.item_catalog c using (catalog_item_id)
    where c.catalog_item_id is null
  ) then
    raise exception 'invoice lines reference a catalog row that does not exist';
  end if;
end $$;

commit;

select
  (select count(*) from public.item_catalog)  as catalog_expect_4029,
  (select count(*) from public.invoice_items) as lines_expect_11746,
  (select count(*) from public.item_aliases)  as aliases_expect_8;
