import re
from urllib.parse import urlparse
import ipaddress
import socket

def is_safe_github_url(url: str) -> bool:
    """
    Validates the GitHub URL for security requirements:
    1. Scheme must be HTTP or HTTPS
    2. Hostname must be github.com or a valid subdomain
    3. Hostname must not resolve to localhost or private network IPs
    4. Reject shell injection characters (; & | ` $ < > \ etc)
    """
    if not url:
        return False
        
    url = url.strip()
    
    # Check for shell injection signatures
    unsafe_chars = [";", "&", "|", "`", "$", "<", ">", "\n", "\r", "\\", "*", "?", "(", ")", "[", "]", "{", "}"]
    if any(char in url for char in unsafe_chars):
        return False
        
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
            
        hostname = parsed.hostname
        if not hostname:
            return False
            
        hostname = hostname.lower()
        
        # Only allow github.com (or subdomains of it, or other valid git hostnames if needed, but requirements say GitHub repository URL)
        # We can support github.com and raw.githubusercontent.com etc.
        if hostname != "github.com" and not hostname.endswith(".github.com"):
            return False
            
        # Check for localhost/loopback
        if hostname in ("localhost", "127.0.0.1", "::1"):
            return False
            
        # Try to resolve IP and verify it's not private
        try:
            ip_str = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback:
                return False
        except socket.gaierror:
            # If resolution fails, we still allow it to pass validation in case of DNS transient failures, 
            # but usually github.com resolves. Let's just check if hostname parses as IP.
            pass
            
        # Also check if hostname itself is a raw private IP
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback:
                return False
        except ValueError:
            pass

        # Validate path has at least org and repo
        path_parts = [p for p in parsed.path.split("/") if p]
        if len(path_parts) < 2:
            return False

        return True
    except Exception:
        return False
