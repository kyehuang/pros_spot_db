#!/bin/bash
set -e

echo "[INFO] Waiting for PostgreSQL to be ready..."

# Wait for PostgreSQL to be ready
until pg_isready -h postgres -U "$POSTGRES_USER"; do
  sleep 1
done

echo "[INFO] Connected. Starting to create databases..."

# Check if POSTGRES_MULTIPLE_DATABASES is set
if [ -z "$POSTGRES_MULTIPLE_DATABASES" ]; then
  echo "[INFO] No databases to create. Exiting."
  exit 0
fi

# Create databases
for db in $(echo "$POSTGRES_MULTIPLE_DATABASES" | tr ',' ' '); do
  echo "[INFO] Creating database: $db"
  PGPASSWORD="$POSTGRES_PASSWORD" psql -h postgres -U "$POSTGRES_USER" -d postgres <<-EOSQL
    SELECT 'CREATE DATABASE "$db"' WHERE NOT EXISTS (
      SELECT FROM pg_database WHERE datname = '$db'
    )\gexec
EOSQL
done

echo "[INFO] Database creation done."
