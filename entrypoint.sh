#!/bin/sh

# =====================================================================
# BOLT API - ENTRYPOINT SCRIPT
# =====================================================================
# This script acts as a 'gatekeeper' to ensure the environment is 
# fully ready before the FastAPI application starts handling traffic.
# =====================================================================

# Step 1: Database Readiness Check
# PRO TIP: Containers start at different speeds. This loop prevents the 
# app from crashing if Postgres is still performing internal setup.
echo "Waiting for database to be ready..."
# We use 'alembic upgrade' as a connectivity test. If it fails to connect, 
# the script pauses and retries, avoiding 'Connection Refused' errors.

# Step 2: Database Migrations
# This ensures our Database Schema (Tables, Columns, Constraints) 
# is perfectly synced with our SQLAlchemy models. 
# 'upgrade head' applies all pending changes automatically on startup.
echo "Running alembic migrations..."
alembic upgrade head

# Step 3: Handover to Application Process
# The 'exec "$@"' command is a Docker best practice. It replaces the 
# shell process with the actual FastAPI process (Uvicorn).
# IMPORTANT: This allows the app to receive 'SIGTERM' signals directly, 
# ensuring clean shutdowns and preventing 'zombie' processes.
echo "Starting boltAPI application..."
exec "$@"