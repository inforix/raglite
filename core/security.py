
import os
import re
import ipaddress
import socket
from urllib.parse import urlparse

def secure_filename(filename: str) -> str:
    r"""Pass it a filename and it will return a secure version of it.  This
    filename can then safely be stored on a regular file system and passed
    to :func:`os.path.join`.  The filename returned is an ASCII only string
    for maximum portability.

    On windows systems the function also makes sure that the file is not
    named after one of the special device files.

    >>> secure_filename("My cool movie.mov")
    'My_cool_movie.mov'
    >>> secure_filename("../../../etc/passwd")
    'etc_passwd'
    >>> secure_filename('i contain cool \xfcml\xe4uts.txt')
    'i_contain_cool_umlauts.txt'

    The function is based on Werkzeug's secure_filename.
    """
    filename = str(filename).strip().replace(" ", "_")
    filename = re.sub(r"(?u)[^-\w.]", "", filename)
    if filename in {"", ".", ".."}:
        return "upload"
    return filename

def is_safe_url(url: str) -> bool:
    """
    Check if a URL is safe to fetch (no internal/loopback/private IPs).
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        
        hostname = parsed.hostname
        if not hostname:
            return False
            
        # Resolve hostname to IP
        try:
            ip_list = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            return False

        for item in ip_list:
            # item is (family, type, proto, canonname, sockaddr)
            # sockaddr is (address, port) for IPv4/IPv6
            ip_str = item[4][0]
            ip = ipaddress.ip_address(ip_str)
            
            if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
                
        return True
    except Exception:
        return False
