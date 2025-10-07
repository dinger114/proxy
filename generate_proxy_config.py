#!/usr/bin/env python3
"""
Opera Proxy to Clash Configuration Generator
"""

import subprocess
import os
import re
import yaml
from datetime import datetime
from typing import List, Dict, Optional, Tuple

class ProxyConfigGenerator:
    def __init__(self):
        self.timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
        self.region_map = {
            'AM': '美国',
            'AS': '新加坡', 
            'EU': '挪威'
        }
        
    def download_opera_proxy(self):
        """下载 opera-proxy 工具"""
        print("下载 opera-proxy 工具...")
        url = "https://github.com/Snawoot/opera-proxy/releases/download/v1.11.2/opera-proxy.linux-amd64"
        
        try:
            subprocess.run([
                'wget', '-q', url, '-O', 'opera-proxy'
            ], check=True)
            
            subprocess.run(['chmod', '+x', 'opera-proxy'], check=True)
            print("opera-proxy 下载完成")
        except subprocess.CalledProcessError as e:
            print(f"下载 opera-proxy 失败: {e}")
            raise

    def generate_proxy_configs(self) -> Dict[str, List[str]]:
        """为每个区域生成代理配置"""
        print("生成代理配置...")
        regions = ['EU', 'AS', 'AM']
        region_files = {}
        
        for region in regions:
            output_file = f"{region}_proxy_output.txt"
            try:
                with open(output_file, 'w') as f:
                    subprocess.run([
                        './opera-proxy', '-country', region, '-list-proxies'
                    ], stdout=f, check=True)
                
                region_files[region] = output_file
                print(f"{region} 区域配置生成完成")
                
            except subprocess.CalledProcessError as e:
                print(f"生成 {region} 区域配置失败: {e}")
                continue
                
        return region_files

    def parse_proxy_credentials(self, region_files: Dict[str, List[str]]) -> Tuple[str, str]:
        """从区域文件中解析代理凭据"""
        print("解析代理凭据...")
        login = ""
        password = ""
        
        for region, filename in region_files.items():
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 查找登录信息
                login_match = re.search(r'Proxy login:\s*(\S+)', content)
                password_match = re.search(r'Proxy password:\s*(\S+)', content)
                
                if login_match and not login:
                    login = login_match.group(1)
                if password_match and not password:
                    password = password_match.group(1)
                    
                if login and password:
                    break
                    
            except Exception as e:
                print(f"解析 {region} 文件失败: {e}")
                continue
        
        print(f"凭据解析完成 - 用户名: {login}, 密码: {'*' * len(password) if password else '未找到'}")
        return login, password

    def parse_proxy_servers(self, filename: str) -> List[Dict]:
        """解析代理服务器列表"""
        servers = []
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 匹配 host,ip,port 格式
                    if re.match(r'^[^,]+,[^,]+,[^,]+$', line):
                        parts = line.split(',')
                        if len(parts) == 3:
                            host, ip, port = parts
                            servers.append({
                                'host': host.strip(),
                                'ip': ip.strip(),
                                'port': port.strip()
                            })
        except Exception as e:
            print(f"解析服务器文件 {filename} 失败: {e}")
            
        return servers

    def generate_clash_config(self, region_files: Dict[str, List[str]], login: str, password: str):
        """生成 Clash 配置文件"""
        print("生成 Clash 配置...")
        
        clash_config = {'proxies': []}
        
        for region, filename in region_files.items():
            country_cn = self.region_map.get(region, region)
            servers = self.parse_proxy_servers(filename)
            
            print(f"处理 {region} 区域，找到 {len(servers)} 个服务器")
            
            for server in servers:
                prefix = server['host'][:3]
                proxy_name = f"{country_cn}-{prefix}"
                
                proxy_config = {
                    'name': proxy_name,
                    'type': 'http',
                    'server': server['ip'],
                    'port': int(server['port']),
                    'username': login,
                    'password': password,
                    'tls': True,
                    'skip-cert-verify': False,
                    'sni': server['host']
                }
                
                clash_config['proxies'].append(proxy_config)
        
        # 写入 YAML 文件
        with open('clash-config.yml', 'w', encoding='utf-8') as f:
            yaml.dump(clash_config, f, allow_unicode=True, default_flow_style=False, indent=2)
            
        print(f"Clash 配置生成完成，共 {len(clash_config['proxies'])} 个代理")

    def cleanup(self, region_files: Dict[str, List[str]]):
        """清理临时文件"""
        print("清理临时文件...")
        
        # 删除区域文件
        for filename in region_files.values():
            try:
                if os.path.exists(filename):
                    os.remove(filename)
            except Exception as e:
                print(f"删除文件 {filename} 失败: {e}")
        
        # 删除 opera-proxy 可执行文件
        try:
            if os.path.exists('opera-proxy'):
                os.remove('opera-proxy')
        except Exception as e:
            print(f"删除 opera-proxy 失败: {e}")

    def run(self):
        """主运行方法"""
        try:
            # 步骤1: 下载工具
            self.download_opera_proxy()
            
            # 步骤2: 生成代理配置
            region_files = self.generate_proxy_configs()
            
            if not region_files:
                print("错误: 没有成功生成任何区域配置")
                return False
            
            # 步骤3: 解析凭据
            login, password = self.parse_proxy_credentials(region_files)
            
            if not login or not password:
                print("警告: 未找到完整的代理凭据")
            
            # 步骤4: 生成 Clash 配置
            self.generate_clash_config(region_files, login, password)
            
            # 步骤5: 清理
            self.cleanup(region_files)
            
            print("代理配置生成完成!")
            return True
            
        except Exception as e:
            print(f"生成配置过程中发生错误: {e}")
            return False

if __name__ == "__main__":
    generator = ProxyConfigGenerator()
    success = generator.run()
    exit(0 if success else 1)
