#!/usr/bin/env python3
import scapy.all as scapy
import nmap
import netifaces
from datetime import datetime

def get_default_gateway():
    gws = netifaces.gateways()
    return gws['default'][netifaces.AF_INET][0]

def scan_network(ip_range):
    print(f'\nScanning network {ip_range}...')
    print('=' * 50)
    
    # ARP scan using scapy
    arp_request = scapy.ARP(pdst=ip_range)
    broadcast = scapy.Ether(dst='ff:ff:ff:ff:ff:ff')
    arp_request_broadcast = broadcast/arp_request
    answered_list = scapy.srp(arp_request_broadcast, timeout=1, verbose=False)[0]
    
    devices = []
    for element in answered_list:
        device_info = {
            'ip': element[1].psrc,
            'mac': element[1].hwsrc
        }
        devices.append(device_info)
    
    # Print results
    print('Active devices in network:')
    print('IP Address\t\tMAC Address')
    print('-' * 50)
    for device in devices:
        print(f"{device['ip']}\t\t{device['mac']}")
    
    # Basic port scan using nmap
    print('\nPerforming basic port scan on discovered devices...')
    nm = nmap.PortScanner()
    for device in devices:
        try:
            print(f"\nScanning ports on {device['ip']}...")
            nm.scan(device['ip'], arguments='-F')  # Fast scan of common ports
            for proto in nm[device['ip']].all_protocols():
                ports = nm[device['ip']][proto].keys()
                for port in ports:
                    state = nm[device['ip']][proto][port]['state']
                    if state == 'open':
                        print(f'Port {port} ({proto}): {state}')
        except Exception as e:
            print(f"Could not scan ports on {device['ip']}: {str(e)}")

if __name__ == '__main__':
    try:
        gateway = get_default_gateway()
        network = f'{gateway}/24'  # Scanning the local subnet
        print(f'Starting network scan at {datetime.now()}')
        print(f'Default gateway: {gateway}')
        scan_network(network)
    except Exception as e:
        print(f'An error occurred: {str(e)}')