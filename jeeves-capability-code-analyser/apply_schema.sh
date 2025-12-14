#!/bin/bash
# Apply code analysis schema to PostgreSQL database

POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-assistant}"
POSTGRES_DB="${POSTGRES_DATABASE:-assistant}"

echo "Applying code analysis schema to ${POSTGRES_DB}..."
echo "Host: ${POSTGRES_HOST}:${POSTGRES_PORT}"

PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -f database/schemas/002_code_analysis_schema.sql

if [ $? -eq 0 ]; then
    echo "✅ Schema applied successfully"
else
    echo "❌ Schema application failed"
    exit 1
fi
