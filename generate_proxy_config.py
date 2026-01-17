#!/usr/bin/env python3
"""
Opera Proxy to Clash Config (Minimalist / Provider Version)
"""

import subprocess
import os
import re
import sys
import stat
import urllib.request
import yaml 

from typing import List, Dict, Tuple

class ProxyConfigGenerator:
    def __init__(self):

        self.output_filename = 'clash-config.yml'
        

        self.version = "v1.11.2"
        self.arch = "linux-amd64" 
        self.binary_name = "opera-proxy"
        self.base_url = f"https://github.com/Snawoot/opera-proxy/releases/download/{self.version}/opera-proxy.{self.arch}"
        
        self.region_map = {'AM': 'Americas', 'AS': 'Asia', 'EU': 'Europe'}

    def download_tool(self):
        print(f"::group::Download Tool")
        try:
            print(f"Downloading {self.binary_name}...")
            urllib.request.urlretrieve(self.base_url, self.binary_name)
            st = os.stat(self.binary_name)
            os.chmod(self.binary_name, st.st_mode | stat.S_IEXEC)
            print("Done.")
        except Exception as e:
            print(f"::error::Download failed: {e}")
            sys.exit(1)
        finally:
            print("::endgroup::")

    def fetch_proxies(self) -> Dict[str, str]:
        print(f"::group::Fetch Proxies")
        files = {}
        for region in self.region_map.keys():
            outfile = f"{region}_raw.txt"
            cmd = [f'./{self.binary_name}', '-country', region, '-list-proxies']
            try:
                with open(outfile, 'w') as f:
                    subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, check=True, text=True)
                files[region] = outfile
                print(f"[{region}] OK.")
            except subprocess.CalledProcessError as e:
                print(f"::warning::[{region}] Failed: {e.stderr}")
        print("::endgroup::")
        return files

    def parse_data(self, files: Dict[str, str]) -> Tuple[str, str, List[Dict]]:
        """解析数据"""
        login, password = "", ""
        servers = []
        
        for region, fpath in files.items():
            if not os.path.exists(fpath): continue
            try:
                with open(fpath, 'r') as f:
                    content = f.read()
                
                if not login:
                    m_log = re.search(r'Proxy login:\s*(\S+)', content)
                    m_pass = re.search(r'Proxy password:\s*(\S+)', content)
                    if m_log: login = m_log.group(1)
                    if m_pass: password = m_pass.group(1)
                
                for line in content.splitlines():
                    line = line.strip()
                    if re.match(r'^[^,]+,[^,]+,\d+$', line):
                        host, ip, port = line.split(',')
                        servers.append({
                            'region': region,
                            'host': host.strip(),
                            'ip': ip.strip(),
                            'port': int(port.strip())
                        })
            except Exception:
                pass 
                
        return login, password, servers

    def generate_yaml(self, login, password, servers):
        if not servers:
            print("::error::No servers found!")
            sys.exit(1)
            
        print(f"Generating minimal config for {len(servers)} proxies...")
        
        proxies = []
        names = []
        
        for s in servers:
            short_host = s['host'].split('.')[0]
            base_name = f"Opera-{s['region']}-{short_host[-2:]}"
            
            name = base_name
            idx = 1
            while name in names:
                name = f"{base_name}-{idx}"
                idx += 1
            names.append(name)
            
            proxies.append({
                'name': name,
                'type': 'http',
                'server': s['ip'],
                'port': s['port'],
                'username': login,
                'password': password,
                'tls': True,
                'skip-cert-verify': True,
                'sni': s['host']
            })


        config = {'proxies': proxies}
        
        with open(self.output_filename, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, sort_keys=False)
        
        print(f"::notice::Generated {self.output_filename} ({len(servers)} nodes).")

    def run(self):
        self.download_tool()
        files = self.fetch_proxies()
        if not files: sys.exit(1)
            
        login, pwd, servers = self.parse_data(files)
        if not login or not pwd:
            print("::error::No credentials found.")
            sys.exit(1)
            
        self.generate_yaml(login, pwd, servers)
        
        for f in files.values():
            if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    ProxyConfigGenerator().run()
