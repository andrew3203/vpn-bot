import requests
import json

import subprocess

class VPNConnector(object):
    
    def __init__(self, secret: str, link: str) -> None:
        self.base_url = f'{link}/v1' + '{method}'
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {secret}'
        }
        self.total_trafic()
        
    def __generate_preshared_key(self) -> str:
        preshkey = subprocess.check_output("wg genkey", shell=True).decode("utf-8").strip()
        return preshkey
    
    def total_trafic(self):
        method = f'/devices/'
        url = self.base_url.format(method=method)
        resp = requests.get(url, headers=self.headers)
        assert int(resp.status_code) in [200, 201, 204], f'Conection error to VPN server {url}'
        total = 0
        for intr in resp.json():
            total += intr['total_receive_bytes'] + intr['total_transmit_bytes']
        return total
    
    def __get_next_ips(self, allowed_ips: list) -> list:
        def parse_ip(ip):
            splited_ip = ip.split('.')
            num = 1 + int(splited_ip[-1].split('/')[0])
            splited_ip[-1] = f'{num}/{splited_ip[-1].split("/")[-1]}'
            return '.'.join(splited_ip)

        ip1, ip2 = allowed_ips
        ip2 = ip2.replace('::', '.')
        new_ip1 = parse_ip(ip1)
        new_ip2 = parse_ip(ip2).replace('.', '::')
        return [new_ip1, new_ip2]        
    
    def create_peer(self, prev_ips: list = None) -> str:
        if prev_ips is None:
            p = self.peers_list()
            prev_ips = p[-1]['allowed_ips'] if len(p) > 0 else ['10.66.66.1/32', 'fd42:42:42::1/128']
            
        url = self.base_url.format(method='/devices/wg0/peers/')
        preshkey = self.__generate_preshared_key()
        data = {
            'allowed_ips': self.__get_next_ips(prev_ips),
            'preshared_key': preshkey,
            'persistent_keepalive_interval': "24s"
        }
        resp = requests.post(url, headers=self.headers, data=json.dumps(data))
        assert int(resp.status_code) in [200, 201, 204], f'Error in CREATE PEER via {url}'
        return preshkey
    
    def delete_peer(self, url_safe_public_key: str) -> bool:
        method = f'/devices/wg0/peers/{url_safe_public_key}/'
        url = self.base_url.format(method=method)
        resp = requests.delete(url, headers=self.headers)
        print(int(resp.status_code))
        return int(resp.status_code) in [200, 201, 204]
    
    def peers_list(self) -> dict:
        method = '/devices/wg0/peers/'
        url = self.base_url.format(method=method)
        resp = requests.get(url, headers=self.headers)
        assert int(resp.status_code) in [200, 201, 204], f'Error in PEERs LIST via {url}'
        return resp.json()
    
    def get_peer(self, url_safe_public_key: str) -> bytes:
        method = f'/devices/wg0/peers/{url_safe_public_key}/'
        url = self.base_url.format(method=method)
        resp = requests.get(url, headers=self.headers)
        assert int(resp.status_code) in [200, 201, 204], f'Error in GET PEER via {url}'
        return resp.json()
    
    def get_peer_qr(self, url_safe_public_key: str) -> bytes:
        method = f'/devices/wg0/peers/{url_safe_public_key}/quick.conf.png?width=256'
        url = self.base_url.format(method=method)
        resp = requests.get(url, headers=self.headers)
        assert int(resp.status_code) in [200, 201, 204], f'Error in GET PEER QR via {url}'
        return resp.content
    
    def get_peer_conf(self, url_safe_public_key: str) -> bytes:
        method = f'/devices/wg0/peers/{url_safe_public_key}/quick.conf'
        url = self.base_url.format(method=method)
        resp = requests.get(url, headers=self.headers)
        assert int(resp.status_code) in [200, 201, 204], f'Error in GET PEER CONF via {url}'
        return resp.text
    