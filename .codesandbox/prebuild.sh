#!/bin/bash
set -e

echo "🔧 Setting up Ghostclaw development environment..."

# Install all dependencies including QMD, complexity, semantic, etc.
echo "📦 Installing dependencies..."
pip install -e ".[full]"

# Warm up embedding model to avoid first-run delay
echo "🤖 Pre-loading embedding model (fastembed)..."
python - << 'EOF'
try:
    from ghostclaw.qmd.embedding import EmbeddingManager
    emb = EmbeddingManager(model="all-MiniLM-L6-v2")
    print("✅ Embedding model loaded successfully")
except Exception as e:
    print(f"⚠️  Could not pre-load embedding model: {e}")
    print("   This is okay - it will download on first use")
EOF

echo "✨ Setup complete! You can now run tasks from the codesandbox UI."
