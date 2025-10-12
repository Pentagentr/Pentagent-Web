"""
Test AI Target Extraction
"""

import asyncio
import logging
import google.generativeai as genai
from config import config
from agent_core.target_validator import smart_target_extraction, ai_extract_target

logging.basicConfig(level=logging.INFO)

async def test_extraction():
    """Test AI target extraction"""
    
    # Setup AI model
    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Test cases
    test_cases = [
        # Basit (regex ile bulunur)
        "example.com tara",
        "https://mysite.com SQL injection",
        "192.168.1.1 port scan",
        
        # AI gerekli (marka isimleri)
        "google tara",
        "twitter api testi",
        "amazon sitesini analiz et",
        "facebook zafiyet taraması",
        "github için güvenlik testi",
        "netflix api kontrolü",
        
        # Target yok
        "merhaba",
        "tarama yap",
        "güvenlik testi yapabilir misin",
    ]
    
    print("\n" + "="*70)
    print(">>> AI TARGET EXTRACTION TEST <<<")
    print("="*70 + "\n")
    
    for i, query in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}] Query: '{query}'")
        
        # Smart extraction
        target, method = await smart_target_extraction(query, model)
        
        if target:
            print(f"   [+] Target: {target} (method: {method})")
        else:
            print(f"   [-] No target found")
        print()
    
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_extraction())

