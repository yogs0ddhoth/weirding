# Migration Specialist

Review schema migrations, data migrations, and destructive data operations.
Skip this specialist entirely if no migration files are changed.

## Checklist

**Reversibility (HIGH if not reversible)**
- Does this migration have a corresponding rollback / `down` function?
- If a column is dropped or a table is removed, can it be restored without data loss?
- If data is transformed (backfill, type change), is the original preserved or recoverable?
- Is the rollback plan documented in the migration file or PR description?

**Lock duration (HIGH if long-lock, MEDIUM if short-lock)**
- Does `ALTER TABLE` add a new column WITHOUT a default value? (Safe on most engines)
- Does `ALTER TABLE` add a column WITH a default value on a large table? (Full table lock on some engines)
- Does the migration create an index without `CONCURRENTLY` (PostgreSQL) or equivalent?
- Is a foreign key added without a prior index on the referencing column?
- Does the migration hold an exclusive lock across a backfill of a large table?

**Backfill safety (MEDIUM)**
- Is a `NOT NULL` constraint added to a column that will be backfilled? (Risk: fails if backfill is not complete before constraint applies)
- Is a backfill done in a single `UPDATE` without batching? (Risk: long-running transaction)
- Is a new column with a non-null default added to a table with millions of rows without a phased approach?

**Application compatibility (HIGH if breaking)**
- Is the migration deployed before the application code that depends on it?
- Is old application code still running when the migration applies? (Deployment strategy)
- Does the migration remove a column that the current deployed application still reads?

**Data integrity**
- Does the migration assume a data invariant that may not hold for all existing rows?
- Are foreign key constraints being added without a prior data cleanup?
