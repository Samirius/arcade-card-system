#!/usr/bin/env bash
#
# run_migrations.sh — apply all SQL migrations in order.
#
# Usage:
#   ./run_migrations.sh [DATABASE_URL]
#
# If DATABASE_URL is not passed as an argument, it is read from the
# DATABASE_URL environment variable.

set -euo pipefail

URL="${1:-${DATABASE_URL:-}}"

if [[ -z "$URL" ]]; then
    echo "Usage: $0 <DATABASE_URL>" >&2
    echo "  (or set the DATABASE_URL environment variable)" >&2
    exit 1
fi

# Resolve the migrations directory relative to this script's location,
# so the script works regardless of the caller's current directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MIGRATIONS=(
    "create_tables.sql"
    "create_audit_logs_table.sql"
    "create_refresh_token_blacklist.sql"
    "create_companies_table.sql"
    "create_balance_ledger.sql"
    "create_offline_tables.sql"
    "add_token_version.sql"
    "fix_schema_orm_drift.sql"
)

echo "Ensuring required extensions exist..."
psql "$URL" -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'

for file in "${MIGRATIONS[@]}"; do
    path="$SCRIPT_DIR/$file"
    echo "Applying migration: $file"
    psql "$URL" -v ON_ERROR_STOP=1 -f "$path"
done

echo "All migrations applied successfully."
