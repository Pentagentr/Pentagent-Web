# RAG Test Runner Script (PowerShell)
# Render'da kullanılan environment variables ile test çalıştır

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RAG COMPREHENSIVE TEST RUNNER" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Environment variables (Render'dan kopyala)
$env:QDRANT_HOST = "https://pentagent-rag-qdrant.hf.space"
$env:QDRANT_API_KEY = "iM-z0e_4bNbfO0M-9Xl5DM5LwL80q0OTv2UX5S7Q18XyvAVJQVQNEg"
$env:HUGGINGFACE_TOKEN = "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"

Write-Host "[*] Configuration:" -ForegroundColor Yellow
Write-Host "    QDRANT_HOST: $($env:QDRANT_HOST)"
Write-Host "    QDRANT_API_KEY: $($env:QDRANT_API_KEY.Substring(0,20))..."
Write-Host "    HUGGINGFACE_TOKEN: $($env:HUGGINGFACE_TOKEN.Substring(0,20))..."
Write-Host ""

# Run test
Write-Host "[*] Starting comprehensive RAG test..." -ForegroundColor Yellow
Write-Host ""

python test_rag_comprehensive.py

# Check exit code
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[+] Test completed successfully!" -ForegroundColor Green
    exit 0
} else {
    Write-Host ""
    Write-Host "[-] Test failed with errors" -ForegroundColor Red
    exit 1
}

