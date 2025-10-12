"""
Target Validator - Hedef URL/Domain doğrulama ve extraction
"""

import re
from urllib.parse import urlparse
from typing import Optional, Tuple


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
    
    query = query.strip()
    
    # 1. URL varsa direkt al
    url_pattern = r'https?://[^\s]+'
    url_match = re.search(url_pattern, query)
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

