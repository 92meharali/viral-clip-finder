#!/usr/bin/env bash
# Run the Next.js frontend using the Node.js binary in ~/.local (no Homebrew required).
set -euo pipefail

NODE_DIR="$HOME/.local/node-v22.12.0-darwin-arm64/bin"
if [[ ! -x "$NODE_DIR/node" ]]; then
  echo "Node.js not found at $NODE_DIR"
  echo "Install it with:"
  echo '  curl -fsSL https://nodejs.org/dist/v22.12.0/node-v22.12.0-darwin-arm64.tar.gz -o /tmp/node.tar.gz'
  echo '  mkdir -p ~/.local && tar -xzf /tmp/node.tar.gz -C ~/.local'
  exit 1
fi

export PATH="$NODE_DIR:$PATH"
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -f .env.local ]]; then
  cp .env.example .env.local
fi

if [[ ! -d node_modules ]]; then
  npm install
fi

npm run dev
