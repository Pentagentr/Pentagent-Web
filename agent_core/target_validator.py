"""
Target Validator - AI-Powered Hedef URL/Domain doğrulama ve extraction
Gemini AI ile akıllı target extraction
"""

import re
import logging
from urllib.parse import urlparse
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)


def is_valid_domain(text: str) -> bool:
    """Domain geçerli mi kontrol et"""
    # Domain pattern: example.com, subdomain.example.com
    domain_pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    return bool(re.match(domain_pattern, text))


def is_valid_url(text: str) -> bool:
    """URL geçerli mi kontrol et"""
    try:
        result = urlparse(text)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except:
        return False


def is_valid_ip(text: str) -> bool:
    """IP adresi geçerli mi kontrol et"""
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(ip_pattern, text):
        return False
    # Her octet 0-255 arası olmalı
    octets = text.split('.')
    return all(0 <= int(octet) <= 255 for octet in octets)


def extract_target_from_query(query: str) -> Optional[str]:
    """Kullanıcı sorgusundan target çıkar"""
    if not query or not isinstance(query, str):
        return None
    
    query = query.strip().lower()
    
    # 1. URL varsa direkt al
    url_pattern = r'https?://[^\s]+'
    url_match = re.search(url_pattern, query, re.IGNORECASE)
    if url_match:
        return url_match.group(0)
    
    # 2. Domain varsa al
    domain_pattern = r'\b([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'
    domain_match = re.search(domain_pattern, query)
    if domain_match:
        domain = domain_match.group(0)
        # www. kaldır
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    
    # 3. IP adresi varsa al
    ip_pattern = r'\b(\d{1,3}\.){3}\d{1,3}\b'
    ip_match = re.search(ip_pattern, query)
    if ip_match:
        ip = ip_match.group(0)
        if is_valid_ip(ip):
            return ip
    
    # 4. Bilinen marka isimlerini domain'e çevir
    brand_to_domain = {
        'google': 'google.com',
        'twitter': 'twitter.com',
        'facebook': 'facebook.com',
        'amazon': 'amazon.com',
        'microsoft': 'microsoft.com',
        'apple': 'apple.com',
        'netflix': 'netflix.com',
        'youtube': 'youtube.com',
        'instagram': 'instagram.com',
        'linkedin': 'linkedin.com',
        'github': 'github.com',
        'reddit': 'reddit.com',
        'stackoverflow': 'stackoverflow.com',
        'medium': 'medium.com',
        'yahoo': 'yahoo.com',
        'bing': 'bing.com'
    }
    
    # Türkçe karakterleri temizle
    turkish_map = str.maketrans('ıİğĞüÜşŞöÖçÇ', 'iIgGuUsSOoCc')
    query_clean = query.translate(turkish_map)
    
    # Kelime kelime kontrol et
    words = re.findall(r'\b[a-z]+\b', query_clean)
    for word in words:
        if word in brand_to_domain:
            logger.info(f"✅ Marka ismi tespit edildi: {word} → {brand_to_domain[word]}")
            return brand_to_domain[word]
    
    return None


def validate_target(target: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Target'ı doğrula ve normalize et
    
    Returns:
        (is_valid, normalized_target, error_message)
    """
    if not target or not isinstance(target, str):
        return False, None, "Target boş veya geçersiz"
    
    target = target.strip()
    
    # Minimum uzunluk kontrolü
    if len(target) < 4:
        return False, None, "Target çok kısa"
    
    # URL ise
    if target.startswith(('http://', 'https://')):
        if is_valid_url(target):
            return True, target, None
        else:
            return False, None, "Geçersiz URL formatı"
    
    # Domain ise
    if is_valid_domain(target):
        # www. kaldır
        if target.startswith('www.'):
            target = target[4:]
        return True, target, None
    
    # IP ise
    if is_valid_ip(target):
        return True, target, None
    
    # Domain pattern içeren uzun metin ise domain'i çıkar
    extracted = extract_target_from_query(target)
    if extracted:
        return True, extracted, None
    
    # Hiçbiri değilse geçersiz
    return False, None, "Geçerli bir URL, domain veya IP adresi bulunamadı"


def has_target_in_query(query: str) -> bool:
    """Kullanıcı sorgusunda hedef var mı kontrol et"""
    if not query:
        return False
    
    extracted = extract_target_from_query(query)
    return extracted is not None


async def ai_extract_target(query: str, ai_model) -> Optional[str]:
    """
    🤖 AI ile akıllı target extraction
    
    AI kullanarak query'den target çıkarır:
    - "google tara" → "google.com"
    - "twitter api test" → "twitter.com"
    - "amazon sitesini analiz et" → "amazon.com"
    - "facebook için zafiyet" → "facebook.com"
    - "google ı xss için değerlendir" → "google.com"
    
    Args:
        query: Kullanıcı sorgusu
        ai_model: AI model instance
    
    Returns:
        Target (domain/URL/IP) veya None
    """
    try:
        prompt = f"""Sen bir siber güvenlik asistanısın. Kullanıcının sorgusundan TARANACAK HEDEF domain/URL/IP'yi çıkar.

KULLANICI SORGUSU: "{query}"

GÖREV:
1. Query'de bir hedef (domain, URL, IP, marka ismi) var mı belirle
2. Varsa normalize et ve döndür (sadece domain, URL veya IP)
3. Yoksa "NO_TARGET" döndür

KURALLAR:
- Marka/şirket ismi varsa domain'e çevir:
  * google/Google → google.com
  * twitter/Twitter → twitter.com
  * facebook/Facebook → facebook.com
  * amazon/Amazon → amazon.com
  * microsoft/Microsoft → microsoft.com
  * apple/Apple → apple.com
  * netflix/Netflix → netflix.com
  * youtube/YouTube → youtube.com
- URL varsa domain çıkar (https://example.com/page → example.com)
- www. kaldır (www.example.com → example.com)
- Türkçe karakterler temizle (ı→i, ş→s, ğ→g, ü→u, ö→o, ç→c)
- Sadece target döndür, açıklama yapma
- Belirsiz ise NO_TARGET döndür

ÖRNEKLER:
"google.com tara" → google.com
"google tara" → google.com
"google ı xss için değerlendir" → google.com
"twitter api testi" → twitter.com
"amazon sitesini analiz et" → amazon.com
"facebook için zafiyet tara" → facebook.com
"https://mysite.com/admin tara" → mysite.com
"192.168.1.1 port scan" → 192.168.1.1
"example.com sql injection" → example.com
"test.example.com" → test.example.com
"tarama yap" → NO_TARGET
"merhaba" → NO_TARGET
"nasılsın" → NO_TARGET

SADECE TARGET DÖNDÜR (tek satır, başka bir şey yazma):"""

        response = await ai_model.generate_content_async(prompt)
        result = response.text.strip()
        
        # NO_TARGET ise None döndür
        if "NO_TARGET" in result.upper():
            logger.info(f"🤖 AI: Query'de target bulunamadı")
            return None
        
        # Sonucu temizle (fazladan text varsa)
        # Sadece ilk satırı al
        target_candidate = result.split('\n')[0].strip()
        
        # Tırnak işaretlerini kaldır
        target_candidate = target_candidate.strip('"\'` ')
        
        # Validate et
        is_valid, normalized, error = validate_target(target_candidate)
        if is_valid:
            logger.info(f"🤖 AI target extraction başarılı: {normalized}")
            return normalized
        else:
            logger.warning(f"🤖 AI extraction başarısız: {error}")
            return None
            
    except Exception as e:
        logger.error(f"AI target extraction hatası: {e}")
        return None


async def smart_target_extraction(query: str, ai_model=None) -> Tuple[Optional[str], str]:
    """
    🧠 AKILLI TARGET EXTRACTION - 2 Fazlı Sistem
    
    PHASE 1: Regex-based (hızlı)
    PHASE 2: AI-powered (akıllı)
    
    Returns:
        (target, method) - method: "regex" veya "ai"
    """
    # PHASE 1: Basit regex extraction
    regex_target = extract_target_from_query(query)
    if regex_target:
        is_valid, normalized, _ = validate_target(regex_target)
        if is_valid:
            logger.info(f"✅ Target (regex): {normalized}")
            return normalized, "regex"
    
    # PHASE 2: AI extraction (regex başarısız olduysa)
    if ai_model:
        logger.info("🤖 AI ile target extraction deneniyor...")
        ai_target = await ai_extract_target(query, ai_model)
        if ai_target:
            logger.info(f"✅ Target (AI): {ai_target}")
            return ai_target, "ai"
    
    # Her ikisi de başarısız
    logger.warning("❌ Target extraction başarısız (regex + AI)")
    return None, "none"

