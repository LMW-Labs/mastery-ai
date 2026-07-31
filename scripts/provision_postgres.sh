#!/usr/bin/env bash
# Provision PostgreSQL for Mastery OS on a fresh Ubuntu host.
#
# Idempotent: safe to re-run, and safe to run on a rebuilt droplet. Every step
# checks for its own result first, so a second run reports "already" rather than
# failing or duplicating.
#
# Deliberately NOT exposed to the network. `listen_addresses` stays on localhost
# and no firewall rule is opened. A remote operator reaches it the same way they
# reach the box at all -- over SSH:
#
#     ssh -N -L 5433:localhost:5432 root@<host>
#     psql "postgresql://mastery@localhost:5433/mastery"
#
# That keeps the "usable from a VPS and a mobile shell" requirement true (a phone
# shell SSHes in and talks to localhost) without widening exposure, which would
# be an approval gate in layer 1 and plain bad practice in layer 3.
#
# Usage:  bash provision_postgres.sh
set -euo pipefail

DB_NAME="${MASTERY_DB_NAME:-mastery}"
DB_USER="${MASTERY_DB_USER:-mastery}"
ENV_FILE="${MASTERY_DB_ENV:-/root/.mastery/postgres.env}"

say() { printf '%s %s\n' "==>" "$*"; }

# -- 1. package ---------------------------------------------------------------
if command -v psql >/dev/null 2>&1; then
    say "postgresql already installed: $(psql --version)"
else
    say "installing postgresql"
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq postgresql postgresql-contrib >/dev/null
    say "installed: $(psql --version)"
fi

systemctl enable --now postgresql >/dev/null 2>&1 || true
systemctl is-active --quiet postgresql || { echo "postgresql failed to start"; exit 1; }
say "postgresql service active"

# -- 2. role ------------------------------------------------------------------
# The password is generated here and never printed to stdout, so it does not end
# up in a terminal scrollback or a CI log. It is written to $ENV_FILE at 0600.
role_exists=$(sudo -u postgres psql -tAc \
    "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" || true)

if [ "$role_exists" = "1" ]; then
    say "role '${DB_USER}' already exists (password left unchanged)"
else
    PGPASS="$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)"
    sudo -u postgres psql -qc \
        "CREATE ROLE ${DB_USER} LOGIN PASSWORD '${PGPASS}'" >/dev/null
    mkdir -p "$(dirname "$ENV_FILE")"
    umask 077
    cat > "$ENV_FILE" <<ENVEOF
# Written by scripts/provision_postgres.sh. Mode 0600, root only.
MASTERY_DATABASE_URL=postgresql://${DB_USER}:${PGPASS}@localhost:5432/${DB_NAME}
ENVEOF
    chmod 600 "$ENV_FILE"
    say "role '${DB_USER}' created; connection string written to ${ENV_FILE}"
fi

# -- 3. database --------------------------------------------------------------
db_exists=$(sudo -u postgres psql -tAc \
    "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" || true)

if [ "$db_exists" = "1" ]; then
    say "database '${DB_NAME}' already exists"
else
    sudo -u postgres createdb -O "${DB_USER}" "${DB_NAME}"
    say "database '${DB_NAME}' created, owned by '${DB_USER}'"
fi

# -- 4. confirm it is not listening beyond localhost --------------------------
listen=$(sudo -u postgres psql -tAc "SHOW listen_addresses")
say "listen_addresses = ${listen}"
case "$listen" in
    localhost|127.0.0.1) : ;;
    *) echo "WARNING: postgres is listening on '${listen}', not just localhost." ;;
esac

# -- 5. schema ----------------------------------------------------------------
SCHEMA="$(dirname "$0")/postgres_schema.sql"
if [ -f "$SCHEMA" ]; then
    say "applying schema from ${SCHEMA}"
    sudo -u postgres psql -q -v ON_ERROR_STOP=1 -d "${DB_NAME}" -f "$SCHEMA"
    say "schema applied"
else
    say "no schema file at ${SCHEMA}; skipping (run again after copying it over)"
fi

# -- 6. grants ----------------------------------------------------------------
# The schema above is applied by the postgres superuser, because that needs no
# password and therefore works on a re-run when $ENV_FILE is gone. The cost is
# that every object it creates is owned by `postgres`, and the application role
# gets nothing -- not even SELECT. That is not a theoretical gap: without this
# block the app connects fine and then fails "permission denied for table
# events" on its first real query.
#
# Granted explicitly rather than by making the app role a superuser. ALL on the
# public schema's objects is what the ingester needs; it is not what a superuser
# has, and the difference matters if this database ever holds more than one app.
say "granting ${DB_USER} access to schema objects"
sudo -u postgres psql -q -v ON_ERROR_STOP=1 -d "${DB_NAME}" <<GRANTEOF
GRANT USAGE, CREATE ON SCHEMA public TO ${DB_USER};
GRANT ALL PRIVILEGES ON ALL TABLES    IN SCHEMA public TO ${DB_USER};
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${DB_USER};
-- Future objects too, so adding a view later does not silently lock the app out.
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES    TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${DB_USER};
GRANTEOF
say "grants applied"

say "done. Connection string is in ${ENV_FILE}"
