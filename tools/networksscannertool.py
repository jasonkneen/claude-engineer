from tools.base import BaseTool
from scapy.all import ARP, Ether, srp
import nmap
import requests
from mac_vendor_lookup import MacLookup
import ipaddress
import time
from typing import Dict, List
import socket
import json

class NetworkScannerTool(BaseTool):
    name = "networksscannertool"
    description = '''
    Network discovery and analysis tool that:
    - Discovers active devices using ARP/ICMP
    - Performs port scanning on discovered devices
    - Identifies device manufacturers via MAC lookup
    - Detects common IoT and network device APIs
    - Provides detailed device and service reporting
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "target_network": {
                "type": "string",
                "description": "Network range to scan (CIDR format e.g. 192.168.1.0/24)"
            },
            "exclude_ips": {
                "type": "array",
                "items": {"type": "string"},
                "description": "IP addresses to exclude from scan"
            },
            "scan_timeout": {
                "type": "integer",
                "default": 3,
                "description": "Timeout in seconds for each scan operation"
            },
            "rate_limit": {
                "type": "integer",
                "default": 100,
                "description": "Maximum number of packets per second"
            }
        },
        "required": ["target_network"]
    }

    def __init__(self):
        super().__init__()
        self.mac_lookup = MacLookup()
        self.common_ports = [80, 443, 8080, 8443, 22, 23, 21, 25, 53]
        self.nm = nmap.PortScanner()

    def discover_devices(self, network: str, exclude_ips: List[str]) -> List[Dict]:
        devices = []
        arp = ARP(pdst=network)
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = ether/arp

        try:
            result = srp(packet, timeout=2, verbose=False)[0]
            for sent, received in result:
                if received.psrc not in exclude_ips:
                    devices.append({
                        'ip': received.psrc,
                        'mac': received.hwsrc
                    })
        except Exception as e:
            self.logger.error(f"Error during device discovery: {str(e)}")
        
        return devices

    def get_manufacturer(self, mac: str) -> str:
        try:
            return self.mac_lookup.lookup(mac)
        except:
            return "Unknown"

    def scan_ports(self, ip: str, timeout: int) -> Dict:
        try:
            result = self.nm.scan(ip, arguments=f'-p{",".join(map(str, self.common_ports))} -sT -T4')
            if ip in self.nm.all_hosts():
                return self.nm[ip].get('tcp', {})
        except Exception as e:
            self.logger.error(f"Error during port scan of {ip}: {str(e)}")
        return {}

    def detect_apis(self, ip: str, open_ports: Dict) -> Dict:
        apis = {}
        for port in open_ports:
            try:
                url = f"http://{ip}:{port}"
                response = requests.get(url, timeout=2)
                apis[port] = {
                    'headers': dict(response.headers),
                    'status': response.status_code
                }
            except:
                continue
        return apis

    def execute(self, **kwargs) -> str:
        target_network = kwargs['target_network']
        exclude_ips = kwargs.get('exclude_ips', [])
        scan_timeout = kwargs.get('scan_timeout', 3)
        rate_limit = kwargs.get('rate_limit', 100)

        results = []
        
        try:
            devices = self.discover_devices(target_network, exclude_ips)
            
            for device in devices:
                time.sleep(1/rate_limit)  # Rate limiting
                
                device_info = {
                    'ip': device['ip'],
                    'mac': device['mac'],
                    'manufacturer': self.get_manufacturer(device['mac']),
                    'ports': {},
                    'apis': {}
                }

                ports = self.scan_ports(device['ip'], scan_timeout)
                device_info['ports'] = ports
                
                if ports:
                    device_info['apis'] = self.detect_apis(device['ip'], ports)
                
                results.append(device_info)

        except Exception as e:
            return json.dumps({
                'error': str(e),
                'status': 'failed'
            })

        return json.dumps({
            'status': 'success',
            'devices': results
        }, indent=2)