-- Create the category the client asked for on 2026-09-02.
--
-- NOT APPLIED. This needs Afaq's decision before it runs, because creating a
-- category is not labelling — it changes the taxonomy the model is trained
-- against, and it affects the release gate.
--
-- WHY. The client's chart of accounts has "Impuestos, comisiones, multas". It
-- was dropped at intake, and the reason is recorded in
-- Data/current_context_2026_06_30/excluded_categories.csv:
--
--   ADM-EXCLUDED, IMPUESTOS Y MULTAS, "Impuestos, comisiones, multas",
--     "Taxes, Commissions and Fines | Territorial, comisiones feria,
--      imp transferencia | normalmente no tienen xml"
--
-- That rationale is measurably wrong. 120 lines in the current dataset match
-- this family, worth CLP 8,333,892, and every one of them came from a real XML
-- invoice. The client confirmed it himself on 2026-09-02:
--
--   "I'm sorry for this, you re right, they should go 'impuestos comisiones y
--    multas', there can be some expenses in this category that dont have xml
--    but the ones you mention do."
--
-- Note his own description already named "comisiones feria" — auction
-- commissions. That is the Tattersall Ganado line (COMISION BOVINOS
-- REPOSICION, CLP 5,441), which is currently in EXP-1.1 and still in review.
-- It belongs here too. The email to him treated it as an exception; his
-- description had already covered it.
--
-- CODE CHOICE. ADM-1.1 through ADM-1.10 are the ADMINISTRACION group and
-- ADM-2.1 through ADM-2.3 are SEGUROS. The client's own sheet puts this under
-- a separate parent, "IMPUESTOS Y MULTAS", so it starts a third group rather
-- than extending ADMINISTRACION: ADM-3.1.
--
-- CONSEQUENCE FOR THE MODEL, and this is the part that needs a decision.
-- A new category has zero training rows. CLAUDE.md: "A class with fewer than 2
-- examples cannot be trained and must fail loudly." So on the next retrain this
-- must be handled the same way as the six categories in D-028 — rule-assigned,
-- never predicted, and marked so the trainer does not try. Creating the row
-- without doing that will trip the retrain.

insert into categories (code, name)
values ('ADM-3.1', 'Impuestos, comisiones, multas')
on conflict (code) do nothing
returning categories_id, code, name;

-- Then put the returned categories_id into
-- reports/client_reply_2026_09_02/commissions_proposal.jsonl and run
-- scripts/98 (not yet written — it is blocked on this).

-- ROLLBACK, only while no line references it:
--   delete from categories where code = 'ADM-3.1';
