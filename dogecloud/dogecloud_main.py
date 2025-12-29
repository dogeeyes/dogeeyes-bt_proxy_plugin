# dogecloud/dogecloud_main.py
#!/usr/bin/python
# coding: utf-8
import sys
import os
import json
import re
import traceback
import io
import base64
import uuid
import time
import shutil
import random
import psutil
import socket
import copy
from abc import ABCMeta, abstractmethod

# 设置面板路径
os.chdir("/www/server/panel")
sys.path.insert(0, "class/")
import public

# 引入模板
sys.path.append('/www/server/panel/plugin/dogecloud')
try:
    if 'dogecloud_templates' in sys.modules:
        del sys.modules['dogecloud_templates']
    from dogecloud_templates import DogeTemplates
except:
    pass

# ==========================================
# 架构层：协议策略基类 (Strategy Interface)
# ==========================================
class BaseProtocol:
    __metaclass__ = ABCMeta

    def __init__(self, main_context, meta):
        self.ctx = main_context
        self.meta = meta

    # --- 抽象方法：必须由子类实现 ---
    @abstractmethod
    def parse_config(self):
        """解析配置文件，返回字典"""
        pass

    @abstractmethod
    def generate_share_link(self, conf, public_ip):
        """生成分享链接和客户端配置文本"""
        pass

    @abstractmethod
    def generate_clash_proxy(self, conf, public_ip):
        """生成 Clash Meta 代理配置对象"""
        pass

    # --- 核心架构优化：统一配置保存逻辑 ---
    
    @abstractmethod
    def _get_template(self):
        """[Hook] 获取配置模板 (Dict 或 String)"""
        pass

    @abstractmethod
    def _fill_template(self, template, data):
        """[Hook] 填充模板数据，返回填充后的对象"""
        pass

    def save_config(self, data):
        """[Template Method] 统一的配置保存流程"""
        raw_tpl = self._get_template()
        
        # 自动处理深拷贝，防止污染全局模板
        if isinstance(raw_tpl, dict):
            tpl_copy = copy.deepcopy(raw_tpl)
            final_conf = self._fill_template(tpl_copy, data)
            self._save_json_config(final_conf)
        else:
            # 字符串模板直接传递
            final_conf = self._fill_template(raw_tpl, data)
            self._save_text_config(final_conf)

    def generate_default_config(self, uuid_val, port):
        """[Template Method] 生成默认配置 (子类可覆盖)"""
        pass

    # --- 钩子方法：子类定义具体行为 ---
    def can_generate_clash(self):
        """[Hook] 是否支持生成 Clash 配置"""
        return True

    def _get_service_desc(self):
        """[Hook] 服务描述"""
        return self.meta['name'] + " Server"

    def _get_service_cmd(self):
        """[Hook] 启动命令"""
        return '/bin/bash -c "{} -c {} >> {} 2>&1"'.format(self.meta['bin'], self.meta['conf'], self.meta['log'])

    def _get_service_env(self):
        """[Hook] 环境变量"""
        return ""

    def _get_service_reload(self):
        """[Hook] 重载命令"""
        return ""

    def _get_install_type(self):
        """[Hook] 安装类型: naive, single, zip, tar"""
        return "single"

    def get_batch_defaults(self, site_name, cert_path, key_path):
        """[Hook] 获取批量安装时的特定默认参数"""
        return {}

    # --- 模板方法：复用逻辑 ---
    def get_service_content(self):
        """[Template] 获取 Systemd 服务文件内容"""
        return DogeTemplates.SERVICE_FILE.format(
            desc=self._get_service_desc(),
            work_dir=self.ctx.get_conf_dir(),
            env_vars=self._get_service_env(),
            exec_start=self._get_service_cmd(),
            exec_reload=self._get_service_reload()
        )

    def get_install_script_snippet(self):
        """[Template] 获取安装脚本片段"""
        i_type = self._get_install_type()
        template_map = {
            'naive': DogeTemplates.INSTALL_STEP_NAIVE,
            'single': DogeTemplates.INSTALL_STEP_SINGLE_BIN,
            'zip': DogeTemplates.INSTALL_STEP_UNZIP,
            'tar': DogeTemplates.INSTALL_STEP_TAR_XZ
        }
        tpl = template_map.get(i_type, DogeTemplates.INSTALL_STEP_SINGLE_BIN)
        
        params = {
            'url': self.meta['url'],
            'bin_path': self.meta['bin'],
            'service_name': self.meta['svc'],
            'service_content': self.get_service_content(),
            'name': self.meta['name'].lower().replace(' ', '-'),
            'bin_name': os.path.basename(self.meta['bin']),
            'asset_path': self.ctx.get_conf_dir()
        }
        
        if i_type == 'zip':
            if 'xray' in self.meta['svc']: params['bin_name'] = 'xray'
            elif 'trojan' in self.meta['svc']: params['bin_name'] = 'trojan-go'
            elif 'juicity' in self.meta['svc']: params['bin_name'] = 'juicity-server'
            
        if i_type == 'tar':
            if 'shadowsocks' in self.meta['svc']: params['bin_name'] = 'ssserver'

        return tpl.format(**params)

    # --- 辅助工具方法 ---
    def _get_val(self, obj, key, default=''):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _save_json_config(self, data_dict):
        public.writeFile(self.meta['conf'], json.dumps(data_dict, indent=4))

    def _save_text_config(self, text_content):
        public.writeFile(self.meta['conf'], text_content)

    def _load_json_conf(self, default_dict):
        content = public.readFile(self.meta['conf'])
        if not content: return default_dict
        try:
            return json.loads(content)
        except:
            return default_dict

# ==========================================
# 实现层：具体协议策略 (Concrete Strategies)
# ==========================================

class NaiveProtocol(BaseProtocol):
    def can_generate_clash(self): return False # Clash 不支持 Naive
    def _get_service_desc(self): return "Caddy NaiveProxy"
    def _get_service_cmd(self): return "{} run --environ --config {}".format(self.meta['bin'], self.meta['conf'])
    def _get_service_reload(self): return "ExecReload={} reload --config {}".format(self.meta['bin'], self.meta['conf'])
    def _get_install_type(self): return "naive"

    def get_batch_defaults(self, site_name, cert_path, key_path):
        return {
            'http_port': '33372', 'domain': site_name, 
            'proxy_site': 'maimai.sega.jp', 'user': 'dogecloud'
        }

    def _get_template(self):
        return DogeTemplates.CONF_NAIVE_FULL

    def _fill_template(self, template, data):
        http_port = self._get_val(data, 'http_port') or '33372'
        cert_path = self._get_val(data, 'cert_path')
        key_path = self._get_val(data, 'key_path')
        
        tls_config = "tls admin@example.com"
        if cert_path and key_path: tls_config = "tls {} {}".format(cert_path, key_path)
        
        port = self._get_val(data, 'port')
        listen_block = ":{}, 127.0.0.1:{}".format(port, port)
        
        return template.format(
            http_port=http_port, domain=self._get_val(data, 'domain'), log=self.meta['log'],
            listen=listen_block, tls=tls_config, user=self._get_val(data, 'user'),
            password=self._get_val(data, 'password'), site=self._get_val(data, 'proxy_site')
        )

    def generate_default_config(self, uuid_val, port):
        self._save_text_config(DogeTemplates.CONF_NAIVE.format(log_path=self.meta['log'], uuid=uuid_val, port=port))

    def parse_config(self):
        defaults = {'port': '8001', 'http_port': '33372', 'domain': '', 'user': 'user', 'password': 'pass', 'proxy_site': 'maimai.sega.jp', 'cert_path': '', 'key_path': ''}
        content = public.readFile(self.meta['conf'])
        if not content: return defaults
        config = defaults.copy()
        try:
            hp = re.search(r'http_port\s+(\d+)', content)
            if hp: config['http_port'] = hp.group(1)
            dm = re.search(r'#\s*domain:\s*(\S+)', content)
            if dm: config['domain'] = dm.group(1)
            auth = re.search(r'basic_auth\s+(\S+)\s+(\S+)', content)
            if auth: config['user'], config['password'] = auth.group(1), auth.group(2)
            proxy = re.search(r'reverse_proxy\s+(https://)?(\S+)', content)
            if proxy: config['proxy_site'] = proxy.group(2).replace('{', '').strip()
            tls = re.search(r'tls\s+([^\s]+)\s+([^\s]+)', content)
            if tls and '@' not in tls.group(1): config['cert_path'], config['key_path'] = tls.group(1), tls.group(2)
            lines = content.split('\n')
            for line in lines:
                if line.strip().endswith('{') and ',' in line:
                    parts = line.split(',')
                    first = parts[0].strip()
                    if ':' in first:
                        if first.startswith(':'): config['port'] = first.replace(':', '')
                        else: config['port'] = first.split(':')[1]
                    break
        except: pass
        return config

    def generate_share_link(self, conf, public_ip):
        host = conf['domain'] if conf.get('domain') and conf['domain'] != 'localhost' else public_ip
        remark = "Naive-{}".format(host)
        url = "naive+https://{}:{}@{}:{}?padding=true#{}".format(conf['user'], conf['password'], host, conf['port'], remark)
        client = {
            "listen": "socks://127.0.0.1:1080",
            "proxy": "https://{}:{}@{}:{}".format(conf['user'], conf['password'], host, conf['port'])
        }
        return {'url': url, 'config': json.dumps(client, indent=2)}

    def generate_clash_proxy(self, conf, ip):
        return None

class Hy2Protocol(BaseProtocol):
    def _get_service_desc(self): return "Hysteria2 Server"
    def _get_service_cmd(self): return '/bin/bash -c "{} server -c {} >> {} 2>&1"'.format(self.meta['bin'], self.meta['conf'], self.meta['log'])
    def _get_install_type(self): return "single"

    def get_batch_defaults(self, site_name, cert_path, key_path):
        return {
            'up_mbps': '100', 'down_mbps': '100', 'masquerade_url': 'https://www.bing.com/'
        }

    def _get_template(self):
        return DogeTemplates.CONF_HY2_FULL

    def _fill_template(self, template, data):
        return template.format(
            port=self._get_val(data, 'port'), up_mbps=self._get_val(data, 'up_mbps', '100'),
            down_mbps=self._get_val(data, 'down_mbps', '100'), cert_path=self._get_val(data, 'cert_path'),
            key_path=self._get_val(data, 'key_path'), password=self._get_val(data, 'password'),
            masquerade_url=self._get_val(data, 'masquerade_url')
        )

    def generate_default_config(self, uuid_val, port):
        self._save_text_config(DogeTemplates.CONF_HY2.format(uuid=uuid_val, plugin_path=self.ctx.get_conf_dir(), port=port))

    def parse_config(self):
        defaults = {'port': '8002', 'password': 'password', 'cert_path': '', 'key_path': '', 'masquerade_url': 'https://www.bing.com/', 'up_mbps': '100', 'down_mbps': '100', 'cert_domain': ''}
        content = public.readFile(self.meta['conf'])
        if not content: return defaults
        config = defaults.copy()
        try:
            port = re.search(r'listen:\s*:(\d+)', content)
            if port: config['port'] = port.group(1)
            pwd = re.search(r'password:\s*(\S+)', content)
            if pwd: config['password'] = pwd.group(1)
            cert = re.search(r'cert:\s*(\S+)', content)
            if cert: config['cert_path'] = cert.group(1)
            key = re.search(r'key:\s*(\S+)', content)
            if key: config['key_path'] = key.group(1)
            url = re.search(r'url:\s*(\S+)', content)
            if url: config['masquerade_url'] = url.group(1)
            up = re.search(r'up:\s*(\d+)', content)
            if up: config['up_mbps'] = up.group(1)
            down = re.search(r'down:\s*(\d+)', content)
            if down: config['down_mbps'] = down.group(1)
            if config['cert_path']:
                base = os.path.basename(config['cert_path'])
                if 'fullchain' not in base and '.' in base: config['cert_domain'] = base.replace('.crt', '').replace('.pem', '')
        except: pass
        return config

    def generate_share_link(self, conf, ip):
        host = conf['cert_domain'] if conf.get('cert_domain') else ip
        remark = "Hysteria2-{}".format(host)
        bw = "\nBandwidth: {}/{} Mbps".format(conf.get('up_mbps'), conf.get('down_mbps')) if conf.get('up_mbps') else ""
        url = "hysteria2://{}@{}:{}?insecure=1&sni={}&obfs=none#{}".format(conf['password'], host, conf['port'], host, remark)
        cfg = "Server: {}\nPort: {}\nAuth: {}\nSNI: {}{}".format(host, conf['port'], conf['password'], host, bw)
        return {'url': url, 'config': cfg}

    def generate_clash_proxy(self, conf, ip):
        host = conf['cert_domain'] if conf.get('cert_domain') else ip
        name = "{} - {}".format(self.meta['name'], conf['port'])
        return {
            "name": name, "type": "hysteria2", "server": ip, "port": int(conf['port']),
            "password": conf['password'], "sni": host, "skip-cert-verify": True
        }

class TuicProtocol(BaseProtocol):
    def _get_service_desc(self): return "Tuic V5 Server"
    def _get_service_cmd(self): return '/bin/bash -c "{} -c {} >> {} 2>&1"'.format(self.meta['bin'], self.meta['conf'], self.meta['log'])
    def _get_install_type(self): return "single"

    def get_batch_defaults(self, site_name, cert_path, key_path):
        return {'congestion_control': 'bbr'}

    def _get_template(self):
        return DogeTemplates.CONF_TUIC_DICT

    def _fill_template(self, conf, data):
        conf['server'] = "0.0.0.0:" + str(self._get_val(data, 'port'))
        conf['users'] = { self._get_val(data, 'uuid'): self._get_val(data, 'password') }
        conf['certificate'] = self._get_val(data, 'cert_path')
        conf['private_key'] = self._get_val(data, 'key_path')
        conf['congestion_control'] = self._get_val(data, 'congestion_control', 'bbr')
        return conf

    def generate_default_config(self, uuid_val, port):
        conf = copy.deepcopy(DogeTemplates.CONF_TUIC_DICT)
        conf['server'] = "0.0.0.0:" + str(port)
        conf['users'] = {uuid_val: uuid_val}
        self._save_json_config(conf)

    def parse_config(self):
        defaults = {'port': '8003', 'uuid': '', 'password': '', 'cert_path': '', 'key_path': '', 'congestion_control': 'bbr'}
        j = self._load_json_conf({})
        if not j: return defaults
        config = defaults.copy()
        try:
            server = j.get('server', '')
            if ':' in server: config['port'] = server.split(':')[-1]
            config['cert_path'] = j.get('certificate', '')
            config['key_path'] = j.get('private_key', '')
            config['congestion_control'] = j.get('congestion_control', 'bbr')
            users = j.get('users', {})
            if users: config['uuid'] = list(users.keys())[0]; config['password'] = users[config['uuid']]
        except: pass
        if not config.get('congestion_control'): config['congestion_control'] = 'bbr'
        return config

    def generate_share_link(self, conf, ip):
        remark = "Tuic-{}".format(ip)
        url = "tuic://{}:{}@{}:{}?congestion_control={}&alpn=h3&sni={}&allow_insecure=1#{}".format(
            conf['uuid'], conf['password'], ip, conf['port'], conf.get('congestion_control', 'bbr'), ip, remark)
        cfg = "UUID: {}\nPassword: {}\nPort: {}\nCongestion: {}".format(conf['uuid'], conf['password'], conf['port'], conf.get('congestion_control'))
        return {'url': url, 'config': cfg}

    def generate_clash_proxy(self, conf, ip):
        name = "{} - {}".format(self.meta['name'], conf['port'])
        return {
            "name": name, "type": "tuic", "server": ip, "port": int(conf['port']),
            "uuid": conf['uuid'], "password": conf['password'],
            "congestion-controller": conf.get('congestion_control', 'bbr'),
            "sni": ip, "alpn": ["h3"], "skip-cert-verify": True
        }

class XrayRealityProtocol(BaseProtocol):
    def _get_service_desc(self): return "Xray Reality Server"
    def _get_service_cmd(self): return "{} run -c {}".format(self.meta['bin'], self.meta['conf'])
    def _get_service_env(self): return 'Environment="XRAY_LOCATION_ASSET={}"'.format(self.ctx.get_conf_dir())
    def _get_install_type(self): return "zip"

    def get_batch_defaults(self, site_name, cert_path, key_path):
        priv_key, pub_key = self.ctx._get_xray_key_pair()
        if not priv_key: priv_key = ""; pub_key = ""
        return {
            'sni': 'www.microsoft.com', 'dest': 'www.microsoft.com:443',
            'private_key': priv_key, 'public_key': pub_key,
            'short_id': ''.join('{:02x}'.format(x) for x in bytearray(os.urandom(4)))
        }

    def _get_template(self):
        return DogeTemplates.CONF_XRAY_REALITY_DICT

    def _fill_template(self, conf, data):
        conf['log']['access'] = self.meta['log']
        conf['log']['error'] = self.meta['log']
        
        inbound = conf['inbounds'][0]
        inbound['port'] = int(self._get_val(data, 'port'))
        inbound['settings']['clients'][0]['id'] = self._get_val(data, 'uuid').strip()
        
        reality = inbound['streamSettings']['realitySettings']
        reality['dest'] = self._get_val(data, 'dest').strip()
        reality['serverNames'] = [self._get_val(data, 'sni').strip()]
        reality['privateKey'] = self._get_val(data, 'private_key').strip()
        reality['shortIds'] = [self._get_val(data, 'short_id').strip()]
        
        final_pub_key = ""
        if hasattr(data, 'public_key') and data.public_key:
            final_pub_key = data.public_key.strip()
        else:
            final_pub_key = self.ctx._get_xray_pubkey(self._get_val(data, 'private_key').strip())
            
        if not final_pub_key: raise Exception("无法生成公钥，请检查私钥格式或确保服务已安装。")
        reality['publicKey'] = final_pub_key
        
        sni = self._get_val(data, 'sni').strip()
        dest = self._get_val(data, 'dest').strip()
        if 'microsoft.com' in dest and 'microsoft.com' not in sni:
            reality['dest'] = "{}:443".format(sni)
        return conf

    def generate_default_config(self, uuid_val, port):
        priv_key, pub_key = self.ctx._get_xray_key_pair()
        if not priv_key: priv_key = ""
        short_id = ''.join('{:02x}'.format(x) for x in bytearray(os.urandom(4)))
        
        conf = copy.deepcopy(DogeTemplates.CONF_XRAY_REALITY_DICT)
        conf['log']['access'] = self.meta['log']
        conf['log']['error'] = self.meta['log']
        
        inbound = conf['inbounds'][0]
        inbound['port'] = port
        inbound['settings']['clients'][0]['id'] = uuid_val
        
        reality = inbound['streamSettings']['realitySettings']
        reality['dest'] = "www.microsoft.com:443"
        reality['serverNames'] = ["www.microsoft.com"]
        reality['privateKey'] = priv_key
        reality['publicKey'] = pub_key
        reality['shortIds'] = [short_id]
        
        self._save_json_config(conf)

    def parse_config(self):
        defaults = {'port': '8004', 'uuid': '', 'private_key': '', 'sni': '', 'dest': '', 'short_id': '', 'public_key': ''}
        j = self._load_json_conf({})
        if not j: return defaults
        config = defaults.copy()
        try:
            inbound = j.get('inbounds', [])[0]
            config['port'] = inbound.get('port', 8004)
            config['uuid'] = inbound['settings']['clients'][0].get('id', '')
            reality = inbound['streamSettings']['realitySettings']
            config['private_key'] = reality.get('privateKey', '')
            config['dest'] = reality.get('dest', '')
            config['sni'] = reality.get('serverNames', [''])[0]
            config['short_id'] = reality.get('shortIds', [''])[0]
            config['public_key'] = reality.get('publicKey', '')
            if not config['public_key'] and config['private_key']:
                config['public_key'] = self.ctx._get_xray_pubkey(config['private_key'])
        except: pass
        return config

    def generate_share_link(self, conf, ip):
        pub_key = conf.get('public_key', '')
        if not pub_key: pub_key = self.ctx._get_xray_pubkey(conf['private_key'])
        sid_param = "&sid={}".format(conf['short_id']) if conf['short_id'] else ""
        remark = "VLESS-Reality-{}".format(conf['sni'] if conf['sni'] else ip)
        url = "vless://{}@{}:{}?security=reality&encryption=none&pbk={}&headerType=none&fp=chrome&type=tcp&flow=xtls-rprx-vision&sni={}{}#{}".format(
            conf['uuid'], ip, conf['port'], pub_key, conf['sni'], sid_param, remark)
        cfg = "Protocol: VLESS-Reality\nUUID: {}\nSNI: {}\nPBK: {}\nSID: {}".format(conf['uuid'], conf['sni'], pub_key, conf['short_id'])
        return {'url': url, 'config': cfg}

    def generate_clash_proxy(self, conf, ip):
        pub_key = conf.get('public_key', '')
        if not pub_key: pub_key = self.ctx._get_xray_pubkey(conf['private_key'])
        name = "{} - {}".format(self.meta['name'], conf['port'])
        return {
            "name": name, "type": "vless", "server": ip, "port": int(conf['port']),
            "uuid": conf['uuid'], "network": "tcp", "tls": True, "udp": True,
            "flow": "xtls-rprx-vision", "servername": conf['sni'],
            "reality-opts": {"public-key": pub_key, "short-id": conf['short_id']},
            "client-fingerprint": "chrome"
        }

class XrayCDNProtocol(BaseProtocol):
    def _get_service_desc(self): return "Xray VLESS CDN Server"
    def _get_service_cmd(self): return "{} run -c {}".format(self.meta['bin'], self.meta['conf'])
    def _get_service_env(self): return 'Environment="XRAY_LOCATION_ASSET={}"'.format(self.ctx.get_conf_dir())
    def _get_install_type(self): return "zip"

    def get_batch_defaults(self, site_name, cert_path, key_path):
        return {'path': '/ws'}

    def _get_template(self):
        return DogeTemplates.CONF_XRAY_CDN_DICT

    def _fill_template(self, conf, data):
        conf['log']['access'] = self.meta['log']
        conf['log']['error'] = self.meta['log']
        
        inbound = conf['inbounds'][0]
        inbound['port'] = int(self._get_val(data, 'port'))
        inbound['settings']['clients'][0]['id'] = self._get_val(data, 'uuid')
        
        stream = inbound['streamSettings']
        stream['tlsSettings']['certificates'][0]['certificateFile'] = self._get_val(data, 'cert_path')
        stream['tlsSettings']['certificates'][0]['keyFile'] = self._get_val(data, 'key_path')
        stream['wsSettings']['path'] = self._get_val(data, 'path')
        return conf

    def generate_default_config(self, uuid_val, port):
        conf = copy.deepcopy(DogeTemplates.CONF_XRAY_CDN_DICT)
        conf['log']['access'] = self.meta['log']
        conf['log']['error'] = self.meta['log']
        
        inbound = conf['inbounds'][0]
        inbound['port'] = port
        inbound['settings']['clients'][0]['id'] = uuid_val
        inbound['streamSettings']['wsSettings']['path'] = "/ws"
        
        self._save_json_config(conf)

    def parse_config(self):
        defaults = {'port': '8005', 'uuid': '', 'path': '/ws', 'cert_path': '', 'key_path': ''}
        j = self._load_json_conf({})
        if not j: return defaults
        config = defaults.copy()
        try:
            inbound = j.get('inbounds', [])[0]
            config['port'] = inbound.get('port', 8005)
            config['uuid'] = inbound['settings']['clients'][0].get('id', '')
            tls = inbound['streamSettings']['tlsSettings']['certificates'][0]
            config['cert_path'] = tls.get('certificateFile', '')
            config['key_path'] = tls.get('keyFile', '')
            config['path'] = inbound['streamSettings']['wsSettings'].get('path', '/ws')
        except: pass
        return config

    def generate_share_link(self, conf, ip):
        sni = ip
        if conf['cert_path']:
            base = os.path.basename(conf['cert_path'])
            if '.' in base and 'fullchain' not in base: sni = base.replace('.crt', '').replace('.pem', '')
        remark = "VLESS-CDN-{}".format(sni)
        url = "vless://{}@{}:{}?security=tls&encryption=none&type=ws&host={}&path={}&sni={}#{}".format(
            conf['uuid'], sni, conf['port'], sni, conf['path'], sni, remark)
        cfg = "Protocol: VLESS+TLS+WS\nUUID: {}\nHost/SNI: {}\nPath: {}".format(conf['uuid'], sni, conf['path'])
        return {'url': url, 'config': cfg}

    def generate_clash_proxy(self, conf, ip):
        sni = ip
        if conf['cert_path']:
            base = os.path.basename(conf['cert_path'])
            if '.' in base and 'fullchain' not in base: sni = base.replace('.crt', '').replace('.pem', '')
        name = "{} - {}".format(self.meta['name'], conf['port'])
        return {
            "name": name, "type": "vless", "server": sni, "port": int(conf['port']),
            "uuid": conf['uuid'], "network": "ws", "tls": True, "udp": True,
            "servername": sni, "ws-opts": {"path": conf['path'], "headers": {"Host": sni}}
        }

class TrojanProtocol(BaseProtocol):
    def _get_service_desc(self): return "Trojan-Go Server"
    def _get_service_cmd(self): return '/bin/bash -c "{} -config {} >> {} 2>&1"'.format(self.meta['bin'], self.meta['conf'], self.meta['log'])
    def _get_install_type(self): return "zip"

    def get_batch_defaults(self, site_name, cert_path, key_path):
        return {'remote_addr': '127.0.0.1', 'remote_port': '80'}

    def _get_template(self):
        return DogeTemplates.CONF_TROJAN_DICT

    def _fill_template(self, conf, data):
        conf['local_port'] = int(self._get_val(data, 'port'))
        conf['remote_addr'] = self._get_val(data, 'remote_addr')
        conf['remote_port'] = int(self._get_val(data, 'remote_port'))
        conf['password'] = [self._get_val(data, 'password')]
        conf['ssl']['cert'] = self._get_val(data, 'cert_path')
        conf['ssl']['key'] = self._get_val(data, 'key_path')
        return conf

    def generate_default_config(self, uuid_val, port):
        conf = copy.deepcopy(DogeTemplates.CONF_TROJAN_DICT)
        conf['local_port'] = port
        conf['password'] = [uuid_val]
        self._save_json_config(conf)

    def parse_config(self):
        defaults = {'port': '8006', 'password': '', 'cert_path': '', 'key_path': '', 'remote_addr': '127.0.0.1', 'remote_port': '80'}
        j = self._load_json_conf({})
        if not j: return defaults
        config = defaults.copy()
        try:
            config['port'] = j.get('local_port', 8006)
            config['remote_addr'] = j.get('remote_addr', '127.0.0.1')
            config['remote_port'] = j.get('remote_port', 80)
            config['password'] = j.get('password', [''])[0]
            config['cert_path'] = j['ssl'].get('cert', '')
            config['key_path'] = j['ssl'].get('key', '')
        except: pass
        return config

    def generate_share_link(self, conf, ip):
        sni = ip
        if conf['cert_path']:
            base = os.path.basename(conf['cert_path'])
            if '.' in base and 'fullchain' not in base: sni = base.replace('.crt', '').replace('.pem', '')
        remark = "Trojan-{}".format(sni)
        url = "trojan://{}@{}:{}?sni={}#{}".format(conf['password'], ip, conf['port'], sni, remark)
        cfg = "Protocol: Trojan\nPassword: {}\nSNI: {}".format(conf['password'], sni)
        return {'url': url, 'config': cfg}

    def generate_clash_proxy(self, conf, ip):
        name = "{} - {}".format(self.meta['name'], conf['port'])
        return {
            "name": name, "type": "trojan", "server": ip, "port": int(conf['port']),
            "password": conf['password'], "sni": ip, "skip-cert-verify": True
        }

class JuicityProtocol(BaseProtocol):
    def can_generate_clash(self): return False # Clash 不支持 Juicity
    def _get_service_desc(self): return "Juicity Server"
    def _get_service_cmd(self): return '/bin/bash -c "{} run -c {} >> {} 2>&1"'.format(self.meta['bin'], self.meta['conf'], self.meta['log'])
    def _get_install_type(self): return "zip"

    def get_batch_defaults(self, site_name, cert_path, key_path):
        return {'congestion_control': 'bbr'}

    def _get_template(self):
        return DogeTemplates.CONF_JUICITY_DICT

    def _fill_template(self, conf, data):
        conf['listen'] = ":" + str(self._get_val(data, 'port'))
        conf['users'] = { self._get_val(data, 'uuid'): self._get_val(data, 'password') }
        conf['certificate'] = self._get_val(data, 'cert_path')
        conf['private_key'] = self._get_val(data, 'key_path')
        conf['congestion_control'] = self._get_val(data, 'congestion_control', 'bbr')
        return conf

    def generate_default_config(self, uuid_val, port):
        conf = copy.deepcopy(DogeTemplates.CONF_JUICITY_DICT)
        conf['listen'] = ":" + str(port)
        conf['users'] = {uuid_val: uuid_val}
        self._save_json_config(conf)

    def parse_config(self):
        defaults = {'port': '8007', 'uuid': '', 'password': '', 'cert_path': '', 'key_path': '', 'congestion_control': 'bbr'}
        j = self._load_json_conf({})
        if not j: return defaults
        config = defaults.copy()
        try:
            listen = j.get('listen', '')
            if ':' in listen: config['port'] = listen.split(':')[-1]
            config['cert_path'] = j.get('certificate', '')
            config['key_path'] = j.get('private_key', '')
            config['congestion_control'] = j.get('congestion_control', 'bbr')
            users = j.get('users', {})
            if users: config['uuid'] = list(users.keys())[0]; config['password'] = users[config['uuid']]
        except: pass
        return config

    def generate_share_link(self, conf, ip):
        sni = ip
        if conf['cert_path']:
            base = os.path.basename(conf['cert_path'])
            if '.' in base and 'fullchain' not in base: sni = base.replace('.crt', '').replace('.pem', '')
        remark = "Juicity-{}".format(sni)
        url = "juicity://{}:{}@{}:{}?congestion_control={}&sni={}#{}".format(
            conf['uuid'], conf['password'], ip, conf['port'], conf.get('congestion_control', 'bbr'), sni, remark)
        cfg = "Protocol: Juicity\nUUID: {}\nPassword: {}\nSNI: {}".format(conf['uuid'], conf['password'], sni)
        return {'url': url, 'config': cfg}

    def generate_clash_proxy(self, conf, ip):
        return None

class ShadowsocksProtocol(BaseProtocol):
    def _get_service_desc(self): return "Shadowsocks-Rust Server"
    def _get_service_cmd(self): return '/bin/bash -c "{} -c {} >> {} 2>&1"'.format(self.meta['bin'], self.meta['conf'], self.meta['log'])
    def _get_install_type(self): return "tar"

    def get_batch_defaults(self, site_name, cert_path, key_path):
        return {
            'method': '2022-blake3-aes-128-gcm',
            'password': base64.b64encode(os.urandom(16)).decode('utf-8')
        }

    def _get_template(self):
        return DogeTemplates.CONF_SHADOWSOCKS_DICT

    def _fill_template(self, conf, data):
        conf['server_port'] = int(self._get_val(data, 'port'))
        conf['password'] = self._get_val(data, 'password')
        conf['method'] = self._get_val(data, 'method', '2022-blake3-aes-128-gcm')
        return conf

    def generate_default_config(self, uuid_val, port):
        # SS 不使用 UUID，生成随机密钥
        default_key = base64.b64encode(os.urandom(16)).decode('utf-8')
        self._save_text_config(DogeTemplates.CONF_SHADOWSOCKS.format(password=default_key, port=port))

    def parse_config(self):
        defaults = {'port': '8008', 'password': '', 'method': '2022-blake3-aes-128-gcm'}
        j = self._load_json_conf({})
        if not j: return defaults
        config = defaults.copy()
        try:
            config['port'] = j.get('server_port', 8008)
            config['password'] = j.get('password', '')
            config['method'] = j.get('method', '2022-blake3-aes-128-gcm')
        except: pass
        if not config.get('method'): config['method'] = '2022-blake3-aes-128-gcm'
        return config

    def generate_share_link(self, conf, ip):
        user_info = "{}:{}".format(conf['method'], conf['password'])
        user_info_b64 = base64.urlsafe_b64encode(user_info.encode('utf-8')).decode('utf-8').rstrip('=')
        remark = "Shadowsocks-{}".format(ip)
        url = "ss://{}@{}:{}#{}".format(user_info_b64, ip, conf['port'], remark)
        cfg = "Protocol: Shadowsocks-2022\nMethod: {}\nPassword: {}\nPort: {}".format(conf['method'], conf['password'], conf['port'])
        return {'url': url, 'config': cfg}

    def generate_clash_proxy(self, conf, ip):
        name = "{} - {}".format(self.meta['name'], conf['port'])
        return {
            "name": name, "type": "ss", "server": ip, "port": int(conf['port']),
            "cipher": conf['method'], "password": conf['password']
        }

# ==========================================
# 主控制类 (Context)
# ==========================================

class dogecloud_main:
    __base_path = '/www/server/panel/plugin/dogecloud'
    __conf_dir = __base_path + '/conf'
    __log_dir = __base_path + '/logs'
    __install_log = '/tmp/dogecloud_install.log'
    __sub_info_file = __conf_dir + '/sub_info.json'
    __software_config_file = __conf_dir + '/software_config.json'
    
    __META = {}
    __handlers = {}

    def __init__(self):
        # 修复初始化顺序：先迁移文件，再加载配置，最后注册处理器
        self._init_structure()
        self._load_software_config()
        self._register_handlers()

    def get_conf_dir(self):
        return self.__conf_dir

    def _load_software_config(self):
        '''加载软件配置信息'''
        if os.path.exists(self.__software_config_file):
            try:
                content = public.readFile(self.__software_config_file)
                config = json.loads(content)
                for key, item in config.items():
                    self.__META[key] = {
                        'name': item['name'],
                        'conf': self.__conf_dir + '/' + item['conf_file'],
                        'log': self.__log_dir + '/' + item['log_file'],
                        'bin': '/usr/bin/' + item['bin_name'],
                        'svc': item['svc_name'],
                        'proto': item['proto'],
                        'url': item['download_url']
                    }
                self.__META['protocols'] = {'conf': self.__conf_dir + '/protocols.json'}
            except Exception as e:
                print("Error loading software config: " + str(e))

    def _init_structure(self):
        '''初始化目录结构并迁移旧文件'''
        if not os.path.exists(self.__conf_dir): os.makedirs(self.__conf_dir)
        if not os.path.exists(self.__log_dir): os.makedirs(self.__log_dir)
        static_css = self.__base_path + '/static/css'
        static_js = self.__base_path + '/static/js'
        if not os.path.exists(static_css): os.makedirs(static_css)
        if not os.path.exists(static_js): os.makedirs(static_js)
        
        files_to_move = {
            'Caddyfile': 'conf', 'config_hy2.yaml': 'conf', 'config_tuic.json': 'conf',
            'config_xray.json': 'conf', 'config_vless_cdn.json': 'conf', 
            'config_trojan.json': 'conf', 'config_juicity.json': 'conf', 'config_shadowsocks.json': 'conf',
            'protocols.json': 'conf', 'software_config.json': 'conf',
            'geoip.dat': 'conf', 'geosite.dat': 'conf',
            'caddy.log': 'logs', 'hy2.log': 'logs', 'tuic.log': 'logs',
            'xray.log': 'logs', 'vless_cdn.log': 'logs', 'trojan.log': 'logs', 'juicity.log': 'logs', 'shadowsocks.log': 'logs'
        }
        for f, d in files_to_move.items():
            old_path = os.path.join(self.__base_path, f)
            new_path = os.path.join(self.__base_path, d, f)
            if os.path.exists(old_path) and not os.path.exists(new_path):
                try: shutil.move(old_path, new_path)
                except: pass

    def _register_handlers(self):
        '''注册协议处理器'''
        # 映射表：协议类型 -> 策略类
        strategy_map = {
            'naive': NaiveProtocol,
            'hy2': Hy2Protocol,
            'tuic': TuicProtocol,
            'xray': XrayRealityProtocol,
            'vless_cdn': XrayCDNProtocol,
            'trojan': TrojanProtocol,
            'juicity': JuicityProtocol,
            'shadowsocks': ShadowsocksProtocol
        }
        
        for sType, StrategyClass in strategy_map.items():
            if sType in self.__META:
                self.__handlers[sType] = StrategyClass(self, self.__META[sType])

    def _get_handler(self, sType):
        return self.__handlers.get(sType)

    # ================= 核心功能 =================

    def get_assets(self, get):
        data = {'css': '', 'js': ''}
        try:
            css_path = self.__base_path + '/static/css/style.css'
            if os.path.exists(css_path): data['css'] = public.readFile(css_path)
            
            # 模块化加载 JS 文件，按顺序合并
            js_files = ['doge_utils.js', 'doge_dashboard.js', 'doge_service.js', 'dogecloud.js']
            js_content = ""
            for f in js_files:
                path = self.__base_path + '/static/js/' + f
                if os.path.exists(path):
                    js_content += public.readFile(path) + "\n"
            data['js'] = js_content
            
        except Exception as e:
            return public.returnMsg(False, '资源加载失败: ' + str(e))
        return public.returnMsg(True, data)

    def get_dashboard_data(self, get):
        data = {
            'subscription': '', 'sub_raw': '', 'sub_count': 0, 'sub_bind': None,
            'services': [], 'downloads': {}, 'all_installed': True
        }
        
        public_ip = self._get_public_ip()
        sub_links = self._generate_base64_sub_links(public_ip)
        
        for sType, meta in self.__META.items():
            if sType == 'protocols': continue
            
            svc_info = {
                'type': sType, 'name': meta.get('name', sType), 'installed': False,
                'status': False, 'port': '-', 'cpu': 0, 'memory': 0, 'uptime': '-'
            }
            
            if os.path.exists(meta['bin']) and os.path.getsize(meta['bin']) > 1024:
                svc_info['installed'] = True
                svc_info['status'] = self._check_service_active(meta['svc'])
                
                handler = self._get_handler(sType)
                if handler and os.path.exists(meta['conf']):
                    try:
                        conf = handler.parse_config()
                        if conf and conf.get('port'): svc_info['port'] = conf['port']
                    except: pass
                
                if svc_info['status']:
                    proc = self._get_process_status(meta['svc'])
                    svc_info.update(proc)
            else:
                data['all_installed'] = False
            
            data['services'].append(svc_info)
            
        if sub_links:
            raw_text = "\n".join(sub_links)
            data['sub_raw'] = raw_text
            data['subscription'] = base64.b64encode(raw_text.encode('utf-8')).decode('utf-8')
            data['sub_count'] = len(sub_links)
            
        self._ensure_config_exists('protocols')
        try:
            content = public.readFile(self.__META['protocols']['conf'])
            data['downloads'] = json.loads(content)
        except: pass

        if os.path.exists(self.__sub_info_file):
            try:
                info = json.loads(public.readFile(self.__sub_info_file))
                if info.get('name') and info.get('filename'):
                    base_url = "http://{}/{}".format(info['name'], info['filename'])
                    data['sub_bind'] = {
                        'site': info['name'],
                        'clash_url': base_url + '.yaml',
                        'base64_url': base_url + '.txt',
                        'clash_qr': self._get_qrcode_base64(base_url + '.yaml'),
                        'base64_qr': self._get_qrcode_base64(base_url + '.txt')
                    }
            except: pass
        
        return public.returnMsg(True, data)

    def _generate_base64_sub_links(self, public_ip=None):
        if not public_ip: public_ip = self._get_public_ip()
        sub_links = []
        for sType, handler in self.__handlers.items():
            meta = self.__META[sType]
            if os.path.exists(meta['bin']) and self._check_service_active(meta['svc']):
                try:
                    conf = handler.parse_config()
                    share = handler.generate_share_link(conf, public_ip)
                    if share.get('url'): sub_links.append(share['url'])
                except: pass
        return sub_links

    def _generate_clash_yaml_content(self):
        public_ip = self._get_public_ip()
        proxies = []
        proxy_names = []
        
        for sType, handler in self.__handlers.items():
            # 过滤不支持 Clash 的协议
            if not handler.can_generate_clash():
                continue

            meta = self.__META[sType]
            if not (os.path.exists(meta['bin']) and self._check_service_active(meta['svc'])):
                continue
            try:
                conf = handler.parse_config()
                proxy_item = handler.generate_clash_proxy(conf, public_ip)
                if proxy_item:
                    proxies.append(proxy_item)
                    proxy_names.append(proxy_item['name'])
            except: pass
        
        if not proxies: return None

        yaml_content = [
            "port: 7890", "socks-port: 7891", "allow-lan: true", "mode: rule",
            "log-level: info", "external-controller: :9090", 
            "geodata-mode: true", "geox-url:",
            "  geoip: \"https://cdn.jsdelivr.net/gh/Loyalsoldier/v2ray-rules-dat@release/geoip.dat\"",
            "  geosite: \"https://cdn.jsdelivr.net/gh/Loyalsoldier/v2ray-rules-dat@release/geosite.dat\"",
            "proxies:"
        ]
        for p in proxies:
            # 修复：添加 YAML 列表项前缀 "- "
            yaml_content.append("  - " + json.dumps(p, ensure_ascii=False))
            
        yaml_content.append("proxy-groups:")
        yaml_content.append("  - name: PROXY")
        yaml_content.append("    type: select")
        yaml_content.append("    proxies:")
        yaml_content.append("      - AUTO")
        for name in proxy_names: yaml_content.append("      - " + name)
            
        yaml_content.append("  - name: AUTO")
        yaml_content.append("    type: url-test")
        yaml_content.append("    url: http://www.gstatic.com/generate_204")
        yaml_content.append("    interval: 300")
        yaml_content.append("    tolerance: 50")
        yaml_content.append("    proxies:")
        for name in proxy_names: yaml_content.append("      - " + name)
            
        yaml_content.append("rules:")
        # 插入新的规则
        rules = [
            "  - GEOIP,LAN,DIRECT,no-resolve",
            "  - GEOIP,PRIVATE,DIRECT,no-resolve",
            "  - GEOSITE,gfw,PROXY",
            "  - GEOSITE,google,PROXY",
            "  - GEOSITE,youtube,PROXY",
            "  - GEOSITE,telegram,PROXY",
            "  - GEOSITE,netflix,PROXY",
            "  - GEOSITE,cn,DIRECT",
            "  - GEOSITE,apple-cn,DIRECT",
            "  - GEOSITE,tld-cn,DIRECT",
            "  - GEOIP,CN,DIRECT",
            "  - MATCH,PROXY"
        ]
        yaml_content.extend(rules)
        
        return "\n".join(yaml_content)

    def get_clash_config(self, get):
        yaml_text = self._generate_clash_yaml_content()
        if not yaml_text: return public.returnMsg(False, '没有正在运行的节点，无法生成配置')
        b64_text = base64.b64encode(yaml_text.encode('utf-8')).decode('utf-8')
        return public.returnMsg(True, {'yaml': yaml_text, 'base64': b64_text})

    # ================= 订阅绑定与更新 =================

    def get_site_list(self, get):
        sites = public.M('sites').field('name,path').select()
        return public.returnMsg(True, sites)

    def get_ssl_sites(self, get):
        sites = public.M('sites').field('name,path').select()
        ssl_sites = []
        for site in sites:
            cert_path = "/www/server/panel/vhost/cert/{}/fullchain.pem".format(site['name'])
            key_path = "/www/server/panel/vhost/cert/{}/privkey.pem".format(site['name'])
            if os.path.exists(cert_path) and os.path.exists(key_path):
                ssl_sites.append(site)
        return public.returnMsg(True, ssl_sites)

    def bind_sub_site(self, get):
        site_path = getattr(get, 'path', '').strip()
        site_name = getattr(get, 'site_name', '').strip()
        if not site_path or not os.path.exists(site_path): return public.returnMsg(False, '网站目录不存在')
        
        filename = 'doge_' + ''.join(random.sample('abcdefghijklmnopqrstuvwxyz0123456789', 16))
        info = {'name': site_name, 'path': site_path, 'filename': filename}
        public.writeFile(self.__sub_info_file, json.dumps(info))
        
        self._update_sub_files()
        return public.returnMsg(True, '绑定成功，订阅链接已生成')

    def unbind_sub_site(self, get):
        if os.path.exists(self.__sub_info_file):
            try:
                info = json.loads(public.readFile(self.__sub_info_file))
                p = info.get('path')
                f = info.get('filename')
                if p and f:
                    if os.path.exists(os.path.join(p, f + '.txt')): os.remove(os.path.join(p, f + '.txt'))
                    if os.path.exists(os.path.join(p, f + '.yaml')): os.remove(os.path.join(p, f + '.yaml'))
            except: pass
            os.remove(self.__sub_info_file)
        return public.returnMsg(True, '已解绑')

    def _update_sub_files(self):
        if not os.path.exists(self.__sub_info_file): return
        try:
            info = json.loads(public.readFile(self.__sub_info_file))
            site_path = info.get('path')
            filename = info.get('filename')
            if not site_path or not filename or not os.path.exists(site_path): return
            
            links = self._generate_base64_sub_links()
            b64_content = ""
            if links:
                raw = "\n".join(links)
                b64_content = base64.b64encode(raw.encode('utf-8')).decode('utf-8')
            public.writeFile(os.path.join(site_path, filename + '.txt'), b64_content)
            
            yaml_content = self._generate_clash_yaml_content()
            if not yaml_content: yaml_content = "# No active proxies"
            public.writeFile(os.path.join(site_path, filename + '.yaml'), yaml_content)
        except: pass

    # ================= 服务管理 =================

    def get_service_info(self, get):
        sType = getattr(get, 'type', 'naive')
        meta = self.__META.get(sType)
        if not meta: return public.returnMsg(False, '未知协议')

        data = {
            'status': False, 'install_status': False, 'client_config': '',
            'share_url': '', 'qrcode': '', 'process': {'cpu': 0, 'memory': 0, 'uptime': ''}, 'ps': ''
        }

        public_ip = self._get_public_ip()
        data['install_status'] = os.path.exists(meta['bin']) and os.path.getsize(meta['bin']) > 1024
        
        if data['install_status']:
            data['status'] = self._check_service_active(meta['svc'])
            if data['status']: data['process'] = self._get_process_status(meta['svc'])
            
            handler = self._get_handler(sType)
            if handler:
                conf = handler.parse_config()
                if conf:
                    share_data = handler.generate_share_link(conf, public_ip)
                    data['client_config'] = share_data.get('config', '')
                    data['share_url'] = share_data.get('url', '')
                    data['qrcode'] = self._get_qrcode_base64(data['share_url'])
        return data

    def get_subscription(self, get):
        res = self.get_dashboard_data(get)
        if res['status']:
            d = res['msg']
            if d['sub_count'] > 0:
                return public.returnMsg(True, {'count': d['sub_count'], 'subscription': d['subscription']})
        return public.returnMsg(False, '暂无可用节点')

    def get_protocol_info(self, get):
        self._ensure_config_exists('protocols')
        try:
            content = public.readFile(self.__META['protocols']['conf'])
            return public.returnMsg(True, json.loads(content))
        except:
            return public.returnMsg(False, '无法读取协议信息文件')

    def get_protocol_install_status(self, get):
        """获取所有协议的安装状态"""
        status = {}
        for sType, meta in self.__META.items():
            if sType == 'protocols': continue
            status[sType] = os.path.exists(meta['bin']) and os.path.getsize(meta['bin']) > 1024
        return public.returnMsg(True, status)

    def install_service(self, get):
        sType = getattr(get, 'type', 'naive')
        meta = self.__META.get(sType)
        handler = self._get_handler(sType)
        if not meta or not handler: return public.returnMsg(False, '未知协议')

        self._ensure_config_exists(sType)
        
        conf = handler.parse_config()
        current_port = conf.get('port') if conf else None

        script = DogeTemplates.INSTALL_HEADER.format(log_file=self.__install_log, service_type=sType)
        script += handler.get_install_script_snippet()
        script += DogeTemplates.INSTALL_FOOTER

        script_path = '/tmp/dogecloud_install.sh'
        public.writeFile(script_path, script)
        public.ExecShell('chmod +x ' + script_path)
        public.writeFile(self.__install_log, '')
        public.ExecShell("nohup bash {} > /dev/null 2>&1 &".format(script_path))
        
        if current_port:
            self._release_firewall(current_port, meta['proto'])
            if sType == 'shadowsocks': self._release_firewall(current_port, 'udp')
            
        return public.returnMsg(True, '已开始后台安装')

    def _get_site_cert_paths(self, site_name):
        """[Helper] 获取网站证书路径"""
        return {
            'cert': "/www/server/panel/vhost/cert/{}/fullchain.pem".format(site_name),
            'key': "/www/server/panel/vhost/cert/{}/privkey.pem".format(site_name)
        }

    def batch_install(self, get):
        site_name = getattr(get, 'site_name', '').strip()
        site_path = getattr(get, 'site_path', '').strip()
        protocols_json = getattr(get, 'protocols', '[]')
        
        if not site_name or not site_path: return public.returnMsg(False, '请选择一个有效的网站')
        
        try:
            selected_protocols = json.loads(protocols_json)
        except:
            return public.returnMsg(False, '协议参数格式错误')

        if not selected_protocols:
            return public.returnMsg(False, '请至少选择一个协议进行安装')

        # 统一获取证书路径
        certs = self._get_site_cert_paths(site_name)
        if not os.path.exists(certs['cert']) or not os.path.exists(certs['key']):
            return public.returnMsg(False, '该网站未配置SSL证书或证书文件不存在。')

        if not self._ensure_xray_bin_for_keys():
            return public.returnMsg(False, '无法下载 Xray 核心用于生成密钥。')

        used_ports = []
        install_script_body = ""
        
        for sType, handler in self.__handlers.items():
            # 只安装选中的协议
            if sType not in selected_protocols: continue
            
            # 再次检查是否已安装，避免重复操作
            meta = self.__META[sType]
            if os.path.exists(meta['bin']) and os.path.getsize(meta['bin']) > 1024:
                continue

            port = self._get_random_port(exclude=used_ports)
            used_ports.append(port)
            common_uuid = str(uuid.uuid4())
            
            # 构造配置数据对象
            class ConfigObj: pass
            cfg = ConfigObj()
            cfg.port = str(port)
            cfg.uuid = common_uuid
            cfg.password = common_uuid
            cfg.cert_path = certs['cert']
            cfg.key_path = certs['key']
            
            # 获取协议特定的默认参数 (多态调用)
            defaults = handler.get_batch_defaults(site_name, certs['cert'], certs['key'])
            for k, v in defaults.items():
                setattr(cfg, k, v)

            handler.save_config(cfg)
            self._release_firewall(port, meta['proto'])
            if sType == 'shadowsocks': self._release_firewall(port, 'udp')
            
            install_script_body += handler.get_install_script_snippet()

        class BindObj: pass
        bind_get = BindObj()
        bind_get.path = site_path
        bind_get.site_name = site_name
        self.bind_sub_site(bind_get)

        full_script = DogeTemplates.INSTALL_HEADER.format(log_file=self.__install_log, service_type="批量安装协议")
        full_script += install_script_body
        full_script += DogeTemplates.INSTALL_FOOTER

        script_path = '/tmp/dogecloud_install_all.sh'
        public.writeFile(script_path, full_script)
        public.ExecShell('chmod +x ' + script_path)
        public.writeFile(self.__install_log, '')
        public.ExecShell("nohup bash {} > /dev/null 2>&1 &".format(script_path))

        return public.returnMsg(True, '已配置选中协议并开始后台安装，请查看日志等待完成。')

    def _update_service_file(self, sType):
        handler = self._get_handler(sType)
        if not handler: return
        
        service_file = "/etc/systemd/system/{}.service".format(self.__META[sType]['svc'])
        content = handler.get_service_content()
        
        current_content = public.readFile(service_file)
        if current_content != content:
            public.writeFile(service_file, content)
            public.ExecShell("systemctl daemon-reload")

    def uninstall_service(self, get):
        sType = getattr(get, 'type', 'naive')
        meta = self.__META.get(sType)
        if not meta: return public.returnMsg(False, '未知服务类型')
        
        log = []
        try:
            log.append("正在卸载 {} ...".format(sType))
            log.append(">> 终止进程: pkill -9 -f {}".format(meta['svc']))
            public.ExecShell("pkill -9 -f {}".format(meta['svc']))
            
            should_delete_bin = True
            if sType in ['xray', 'vless_cdn']:
                other_svc = 'dogecloud-vless-cdn' if sType == 'xray' else 'dogecloud-xray'
                if os.path.exists("/etc/systemd/system/{}.service".format(other_svc)):
                    should_delete_bin = False
                    log.append(">> 检测到其他 Xray 服务存在，跳过删除二进制文件")
            
            if should_delete_bin and os.path.exists(meta['bin']):
                log.append(">> 删除二进制文件: rm {}".format(meta['bin']))
                os.remove(meta['bin'])
            
            public.ExecShell("systemctl stop {}".format(meta['svc']))
            public.ExecShell("systemctl disable {}".format(meta['svc']))
            
            service_file = "/etc/systemd/system/{}.service".format(meta['svc'])
            if os.path.exists(service_file): os.remove(service_file)
            
            public.ExecShell("systemctl daemon-reload")
            
            if sType == 'naive' and os.path.exists("/usr/bin/dogecloud"):
                os.remove("/usr/bin/dogecloud")
            
            if should_delete_bin and sType in ['xray', 'vless_cdn', 'trojan']:
                for f in ['geoip.dat', 'geosite.dat']:
                    p = os.path.join(self.__conf_dir, f)
                    if os.path.exists(p): os.remove(p)
                
            log.append(">> 卸载完成")
            return {"status": True, "msg": "\n".join(log)}
        except Exception as e:
            log.append("Error: " + str(e))
            return {"status": True, "msg": "\n".join(log)}

    def get_install_log(self, get):
        if not os.path.exists(self.__install_log): return public.returnMsg(True, '等待日志生成...')
        return public.returnMsg(True, public.readFile(self.__install_log))

    def service_admin(self, get):
        sType = getattr(get, 'type', 'naive')
        action = getattr(get, 'status', 'restart')
        meta = self.__META.get(sType)
        if not meta: return public.returnMsg(False, '未知服务类型')
        
        if action in ['start', 'restart']:
            self._ensure_config_exists(sType)
            self._update_service_file(sType)

        public.ExecShell("systemctl {} {}".format(action, meta['svc']))
        is_active = self._check_service_active(meta['svc'])
        self._update_sub_files()
        
        if action == 'start' and not is_active: return public.returnMsg(False, '启动失败，请查看日志')
        return public.returnMsg(True, '操作成功')

    def clear_service_log(self, get):
        sType = getattr(get, 'type', 'naive')
        meta = self.__META.get(sType)
        if meta and os.path.exists(meta['log']):
            public.writeFile(meta['log'], "")
            return public.returnMsg(True, '日志已清空')
        return public.returnMsg(False, '未知服务类型或日志不存在')

    def get_form_config(self, get):
        sType = getattr(get, 'type', 'naive')
        self._ensure_config_exists(sType)
        handler = self._get_handler(sType)
        return handler.parse_config() if handler else {}

    def set_form_config(self, get):
        sType = getattr(get, 'type', 'naive')
        meta = self.__META.get(sType)
        handler = self._get_handler(sType)
        try:
            if handler:
                handler.save_config(get)
                self._release_firewall(get.port, meta['proto'])
                if sType == 'shadowsocks': self._release_firewall(get.port, 'udp')
                self._update_sub_files()
                return public.returnMsg(True, '配置已保存，请重启服务生效')
            return public.returnMsg(False, '保存方法未定义')
        except Exception as e:
            return public.returnMsg(False, '保存失败: ' + str(e))

    def generate_reality_keys(self, get):
        priv, pub_or_err = self._get_xray_key_pair()
        if not priv: return public.returnMsg(False, '密钥生成失败：' + str(pub_or_err))
        return public.returnMsg(True, {'private_key': priv, 'public_key': pub_or_err})

    def generate_ss_key(self, get):
        method = getattr(get, 'method', '2022-blake3-aes-128-gcm')
        length = 16
        if '256' in method or 'chacha20' in method: length = 32
        try:
            key = base64.b64encode(os.urandom(length)).decode('utf-8')
            return public.returnMsg(True, {'key': key})
        except Exception as e:
            return public.returnMsg(False, '生成失败: ' + str(e))

    # ================= 辅助方法 =================

    def _ensure_config_exists(self, sType):
        if not os.path.exists(self.__conf_dir): os.makedirs(self.__conf_dir)
        meta = self.__META.get(sType)
        if not meta: return
        path = meta['conf']
        if os.path.exists(path) and os.path.getsize(path) > 0: return

        common_uuid = str(uuid.uuid4())
        random_port = self._get_random_port()
        
        handler = self._get_handler(sType)
        if handler:
            handler.generate_default_config(common_uuid, random_port)
        elif sType == 'protocols':
            public.writeFile(path, "{}")

    def _get_random_port(self, exclude=None):
        if exclude is None: exclude = []
        for _ in range(50):
            port = random.randint(10000, 65000)
            if port in exclude: continue
            if self._is_port_used(port): continue
            return port
        return random.randint(9000, 9999)

    def _is_port_used(self, port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                return s.connect_ex(('127.0.0.1', port)) == 0
        except: return False

    def _release_firewall(self, port, protocol):
        try:
            if os.path.exists('/usr/bin/firewall-cmd'):
                public.ExecShell('firewall-cmd --zone=public --add-port={}/{} --permanent'.format(port, protocol))
                public.ExecShell('firewall-cmd --reload')
            if os.path.exists('/usr/sbin/ufw'):
                public.ExecShell('ufw allow {}/{}'.format(port, protocol))
        except: pass

    def _check_service_active(self, name):
        res = public.ExecShell("systemctl is-active {}".format(name))[0].strip()
        return res == 'active'

    def _get_process_status(self, service_name):
        try:
            pid_out = public.ExecShell("systemctl show --property MainPID --value {}".format(service_name))[0].strip()
            if not pid_out or pid_out == '0': return {'cpu': 0, 'memory': 0, 'uptime': '未运行'}
            pid = int(pid_out)
            p = psutil.Process(pid)
            cpu = p.cpu_percent(interval=0.1)
            mem = p.memory_info().rss / 1024 / 1024
            create_time = p.create_time()
            uptime_seconds = time.time() - create_time
            m, s = divmod(uptime_seconds, 60)
            h, m = divmod(m, 60)
            d, h = divmod(h, 24)
            uptime = "%d天%d小时%d分" % (d, h, m)
            return {'cpu': round(cpu, 1), 'memory': round(mem, 1), 'uptime': uptime}
        except: return {'cpu': 0, 'memory': 0, 'uptime': '获取失败'}

    def _get_public_ip(self):
        return public.GetLocalIp()

    def _get_qrcode_base64(self, url):
        try:
            import qrcode
            img = qrcode.make(url)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('utf-8')
        except: return ""

    def _ensure_xray_bin_for_keys(self):
        bin_path = '/usr/bin/dogecloud-xray'
        if os.path.exists(bin_path): return True
        url = self.__META['xray']['url']
        tmp_zip = '/tmp/xray_temp.zip'
        try:
            public.ExecShell('wget -O {} {} -t 3 -T 20'.format(tmp_zip, url))
            if os.path.exists(tmp_zip) and os.path.getsize(tmp_zip) > 1024:
                public.ExecShell('unzip -o {} -d /tmp/xray_temp_dist'.format(tmp_zip))
                if os.path.exists('/tmp/xray_temp_dist/xray'):
                    public.ExecShell('mv /tmp/xray_temp_dist/xray {}'.format(bin_path))
                    public.ExecShell('chmod +x {}'.format(bin_path))
                    public.ExecShell('rm -rf /tmp/xray_temp_dist {}'.format(tmp_zip))
                    return True
        except: pass
        return False

    def _get_xray_key_pair(self):
        bin_path = '/usr/bin/dogecloud-xray'
        if not os.path.exists(bin_path): return None, "未找到 Xray 核心程序 ({})，请先安装服务。".format(bin_path)
        try:
            cmd = bin_path + " x25519"
            res = public.ExecShell(cmd)
            out = res[0]
            if out:
                priv = re.search(r'Private\s+Key:\s*(\S+)', out, re.IGNORECASE)
                pub = re.search(r'Public\s+Key:\s*(\S+)', out, re.IGNORECASE)
                if priv and pub: return priv.group(1).strip(), pub.group(1).strip()
            return None, "无法解析输出: " + str(out)
        except Exception as e: return None, "系统错误: " + str(e)

    def _get_xray_pubkey(self, private_key):
        bin_path = '/usr/bin/dogecloud-xray'
        if not private_key or not os.path.exists(bin_path): return ""
        tmp_key_file = '/tmp/xray_priv_key.tmp'
        try:
            public.writeFile(tmp_key_file, private_key.strip())
            cmd = "{} x25519 -i < {}".format(bin_path, tmp_key_file)
            out = public.ExecShell(cmd)[0]
            pub = re.search(r'Public\s+Key:\s*(\S+)', out, re.IGNORECASE)
            if pub: return pub.group(1).strip()
            out_clean = out.strip()
            if len(out_clean) == 43 and '=' not in out_clean: return out_clean
            return ""
        except: return ""
        finally:
            if os.path.exists(tmp_key_file): os.remove(tmp_key_file)
