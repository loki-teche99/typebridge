from zeroconf import ServiceInfo, Zeroconf, NonUniqueNameException
import socket
import json
import os
from app.core.config import ConfigManager
from app.core.logger import StructuredLogger

class DiscoveryManager:
    def __init__(self):
        self.zeroconf = None
        self.config = ConfigManager()
        self.service_info = None
        self.logger = StructuredLogger()
        
    def get_local_ip(self):
        """Get the best local IP, preferring real LAN over Docker/WSL/VM interfaces."""
        import ipaddress
        try:
            # Enumerate all interfaces via socket connections to multiple targets
            candidates = []
            for target in ['10.255.255.255', '8.8.8.8', '192.168.1.1']:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.settimeout(0.1)
                    s.connect((target, 1))
                    ip = s.getsockname()[0]
                    s.close()
                    if ip and ip != '127.0.0.1' and ip not in candidates:
                        candidates.append(ip)
                except Exception:
                    pass
            
            # Filter out Docker, WSL, and VM ranges
            preferred = []
            for ip in candidates:
                addr = ipaddress.ip_address(ip)
                # Skip Docker default bridge (172.17.x.x)
                if addr in ipaddress.ip_network('172.17.0.0/16'):
                    continue
                # Skip common Docker networks (172.18-31.x.x)
                if addr in ipaddress.ip_network('172.16.0.0/12') and addr not in ipaddress.ip_network('172.16.0.0/16'):
                    continue
                preferred.append(ip)
            
            if preferred:
                # Prefer 192.168.x.x (most common home LAN)
                for ip in preferred:
                    if ip.startswith('192.168.'):
                        return ip
                return preferred[0]
            
            if candidates:
                return candidates[0]
                
        except Exception:
            pass
        
        # Final fallback
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP
        
    def start(self):
        try:
            ip = self.get_local_ip()
            port = self.config.get('server_port')
            desc = {'version': self.config.get('app_version', '1.0.3')}
            # Make the service instance name unique to prevent collisions across restarts or multiple instances
            import os, uuid
            host_tag = socket.gethostname().split('.')[0]
            instance_name = f"TypeBridge Desktop ({host_tag}-{os.getpid()})._typebridge._tcp.local."
            self.service_info = ServiceInfo(
                "_typebridge._tcp.local.",
                instance_name,
                addresses=[socket.inet_aton(ip)],
                port=port,
                properties=desc,
                server=f"typebridge-{os.getpid()}.local.",
            )
            self.zeroconf = Zeroconf()
            try:
                self.zeroconf.register_service(
                    self.service_info,
                    cooperating_responders=True,
                    allow_name_change=True
                )
            except Exception:
                # Fallback to random suffix if collision still occurs
                rnd = uuid.uuid4().hex[:4]
                self.service_info = ServiceInfo(
                    "_typebridge._tcp.local.",
                    f"TypeBridge Desktop ({host_tag}-{rnd})._typebridge._tcp.local.",
                    addresses=[socket.inet_aton(ip)],
                    port=port,
                    properties=desc,
                    server=f"typebridge-{rnd}.local.",
                )
                self.zeroconf.register_service(
                    self.service_info,
                    cooperating_responders=True,
                    allow_name_change=True
                )
        except Exception as e:
            self.logger.warning(f"Zeroconf mDNS advertisement notice: {e}")
        
    def stop(self):
        try:
            if self.zeroconf and self.service_info:
                self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()
                self.zeroconf = None
                self.service_info = None
        except Exception as e:
            self.logger.debug(f"Zeroconf unregister notice: {e}")
