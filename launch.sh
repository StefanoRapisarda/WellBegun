#!/bin/bash

APP_DIR="/Users/stefano.rapisarda/StefanoHome/Projects/Programming/WellBegun"
LOG_DIR="/tmp/wellbegun"
BACKEND_PORT=8000
FRONTEND_PORT=5173

mkdir -p "$LOG_DIR"

export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh" 2>/dev/null

if ! command -v node &>/dev/null; then
    osascript -e 'display alert "WellBegun" message "node not found. Install Node.js via nvm." as critical'
    exit 1
fi

lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null
lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null
sleep 0.5

rm -rf "$APP_DIR/frontend/node_modules/.vite"

cd "$APP_DIR"
PYTHONPATH=src .venv/bin/uvicorn wellbegun.main:app --reload --port $BACKEND_PORT > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

for i in $(seq 1 30); do
    curl -s "http://localhost:$BACKEND_PORT/api/health" > /dev/null 2>&1 && break
    kill -0 $BACKEND_PID 2>/dev/null || { osascript -e "display alert \"WellBegun\" message \"Backend failed. See $LOG_DIR/backend.log\" as critical"; exit 1; }
    sleep 1
done

cd "$APP_DIR/frontend"
npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!

for i in $(seq 1 20); do
    curl -s "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1 && break
    kill -0 $FRONTEND_PID 2>/dev/null || { osascript -e "display alert \"WellBegun\" message \"Frontend failed. See $LOG_DIR/frontend.log\" as critical"; kill $BACKEND_PID 2>/dev/null; exit 1; }
    sleep 1
done

open "http://localhost:$FRONTEND_PORT"
