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

    def generate_proxy_configs(self) -> Dict[str, str]:
        """为每个区域生成代理配置"""
        print("生成代理配置...")
        regions = ['EU', 'AS', 'AM']
        region_files = {}
        
        for region in regions:
            output_file = f"{region}_proxy_output.txt"
            try:
                with open(output_file, 'w') as f:
                    result = subprocess.run([
                        './opera-proxy', '-country', region, '-list-proxies'
                    ], stdout=f, stderr=subprocess.PIPE, text=True)
                
                if result.returncode == 0:
                    region_files[region] = output_file
                    print(f"{region} 区域配置生成完成")
                else:
                    print(f"生成 {region} 区域配置失败: {result.stderr}")
                
            except subprocess.CalledProcessError as e:
                print(f"生成 {region} 区域配置失败: {e}")
                continue
                
        return region_files

    def parse_proxy_credentials(self, region_files: Dict[str, str]) -> Tuple[str, str]:
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
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    # 跳过空行和注释行
                    if not line or line.startswith('#'):
                        continue
                    
                    # 匹配 host,ip,port 格式
                    if re.match(r'^[^,]+,[^,]+,[^,]+$', line):
                        parts = line.split(',')
                        if len(parts) == 3:
                            host, ip, port = [part.strip() for part in parts]
                            
                            # 验证端口号
                            try:
                                port_int = int(port)
                                if 1 <= port_int <= 65535:
                                    servers.append({
                                        'host': host,
                                        'ip': ip,
                                        'port': port_int
                                    })
                                else:
                                    print(f"警告: 文件 {filename} 第 {line_num} 行端口号超出范围: {port}")
                            except ValueError:
                                print(f"警告: 文件 {filename} 第 {line_num} 行无效的端口号: {port}")
                    else:
                        print(f"调试: 跳过不匹配的行 {line_num}: {line}")
                        
        except Exception as e:
            print(f"解析服务器文件 {filename} 失败: {e}")
            
        print(f"从 {filename} 解析到 {len(servers)} 个有效服务器")
        return servers

    def debug_file_content(self, filename: str):
        """调试文件内容"""
        print(f"\n=== 调试文件 {filename} ===")
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"文件内容:\n{content}")
                print("=== 文件内容结束 ===\n")
        except Exception as e:
            print(f"读取调试文件失败: {e}")

    def generate_clash_config(self, region_files: Dict[str, str], login: str, password: str):
        """生成 Clash 配置文件"""
        print("生成 Clash 配置...")
        
        clash_config = {'proxies': []}
        total_servers = 0
        
        for region, filename in region_files.items():
            # 调试：先查看文件内容
            self.debug_file_content(filename)
            
            country_cn = self.region_map.get(region, region)
            servers = self.parse_proxy_servers(filename)
            
            print(f"处理 {region} 区域，找到 {len(servers)} 个服务器")
            
            for server in servers:
                prefix = server['host'][:3] if len(server['host']) >= 3 else server['host']
                proxy_name = f"{country_cn}-{prefix}"
                
                proxy_config = {
                    'name': proxy_name,
                    'type': 'http',
                    'server': server['ip'],
                    'port': server['port'],  # 这里已经是整数
                    'username': login,
                    'password': password,
                    'tls': True,
                    'skip-cert-verify': False,
                    'sni': server['host']
                }
                
                clash_config['proxies'].append(proxy_config)
                total_servers += 1
        
        # 写入 YAML 文件
        with open('clash-config.yml', 'w', encoding='utf-8') as f:
            yaml.dump(clash_config, f, allow_unicode=True, default_flow_style=False, indent=2)
            
        print(f"Clash 配置生成完成，共 {total_servers} 个代理")

    def cleanup(self, region_files: Dict[str, str]):
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
                # 设置默认值避免后续错误
                login = login or "default_user"
                password = password or "default_pass"
            
            # 步骤4: 生成 Clash 配置
            self.generate_clash_config(region_files, login, password)
            
            # 步骤5: 清理
            self.cleanup(region_files)
            
            print("代理配置生成完成!")
            return True
            
        except Exception as e:
            print(f"生成配置过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    generator = ProxyConfigGenerator()
    success = generator.run()
    exit(0 if success else 1)
