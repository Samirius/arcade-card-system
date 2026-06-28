#!/usr/bin/env bash
# Apply every migrations/*.sql to the target DB in order, reporting pass/fail.
# WARNING: wipes the public schema of the target DB. Point it at a throwaway DB.
set -u
URL="${1:-${DATABASE_URL:-}}"
[ -z "$URL" ] && { echo "usage: check_migrations.sh <postgres-url>  (or set DATABASE_URL)"; exit 2; }
MIG="$(cd "$(dirname "$0")/../migrations" && pwd)"
echo "Target: $URL"
echo "Resetting public schema (this WIPES the target DB)..."
psql "$URL" -qc 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;' >/dev/null
psql "$URL" -qc 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";' >/dev/null 2>&1
ORDER="create_tables.sql create_audit_logs_table.sql create_refresh_token_blacklist.sql create_companies_table.sql create_balance_ledger.sql create_offline_tables.sql add_token_version.sql fix_schema_orm_drift.sql"
fail=0
for f in $ORDER; do
  [ -f "$MIG/$f" ] || { echo "SKIP $f (missing)"; continue; }
  err=$(psql "$URL" -v ON_ERROR_STOP=1 -q -f "$MIG/$f" 2>&1 >/dev/null); rc=$?
  if [ $rc -eq 0 ]; then echo "OK   $f"; else echo "FAIL $f :: $(echo "$err" | grep -i 'error:' | head -1)"; fail=1; fi
done
exit $fail
