#!/bin/bash

# RAG Test Runner Script
# Render'da kullanılan environment variables ile test çalıştır

echo "========================================"
echo "  RAG COMPREHENSIVE TEST RUNNER"
echo "========================================"
echo ""

# Environment variables (Render'dan kopyala)
export QDRANT_HOST="https://pentagent-rag-qdrant.hf.space"
export QDRANT_API_KEY="iM-z0e_4bNbfO0M-9Xl5DM5LwL80q0OTv2UX5S7Q18XyvAVJQVQNEg"
export HUGGINGFACE_TOKEN="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"

echo "[*] Configuration:"
echo "    QDRANT_HOST: $QDRANT_HOST"
echo "    QDRANT_API_KEY: ${QDRANT_API_KEY:0:20}..."
echo "    HUGGINGFACE_TOKEN: ${HUGGINGFACE_TOKEN:0:20}..."
echo ""

# Run test
echo "[*] Starting comprehensive RAG test..."
echo ""

python test_rag_comprehensive.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "[+] Test completed successfully!"
    exit 0
else
    echo ""
    echo "[-] Test failed with errors"
    exit 1
fi

