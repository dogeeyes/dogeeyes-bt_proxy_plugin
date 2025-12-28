# dogecloud/dogecloud_templates.py
# coding: utf-8

class DogeTemplates:
    # ================= 安装脚本模板 =================
    
    # 基础安装脚本头部
    INSTALL_HEADER = """#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
LOG_FILE='{log_file}'

# 输出重定向到日志文件
exec > >(tee -a $LOG_FILE) 2>&1

echo "==========================================="
echo "正在开始安装 {service_type} 服务..."
echo "时间: $(date "+%Y-%m-%d %H:%M:%S")"
echo "==========================================="

download_bin() {{
    url=$1
    path=$2
    echo ">> 步骤 1/3: 下载二进制文件"
    echo "   目标路径: $path"
    echo "   下载地址: $url"
    
    rm -f $path
    wget -O $path $url -t 3 -T 20 --no-check-certificate --progress=bar:force
    
    if [ ! -s $path ] || [ $(stat -c%s "$path") -lt 1024 ]; then
        echo "   [错误] 下载失败，文件为空或无效！"
        rm -f $path
        exit 1
    fi
    
    chmod +x $path
    echo "   [成功] 文件下载完成，大小: $(du -h $path | awk '{{print $1}}')"
}}

install_unzip() {{
    if ! command -v unzip &> /dev/null; then
        if [ -f /usr/bin/yum ]; then yum install -y unzip; fi
        if [ -f /usr/bin/apt ]; then apt-get install -y unzip; fi
    fi
}}

install_tar() {{
    if ! command -v tar &> /dev/null; then
        if [ -f /usr/bin/yum ]; then yum install -y tar; fi
        if [ -f /usr/bin/apt ]; then apt-get install -y tar; fi
    fi
    if ! command -v xz &> /dev/null; then
        if [ -f /usr/bin/yum ]; then yum install -y xz; fi
        if [ -f /usr/bin/apt ]; then apt-get install -y xz-utils; fi
    fi
}}
"""

    # 基础安装脚本尾部
    INSTALL_FOOTER = """
if [ $? -eq 0 ]; then
    echo "==========================================="
    echo "安装完成|Success"
else
    echo "==========================================="
    echo "安装失败|Failed"
fi
"""

    # Systemd 服务文件模板
    SERVICE_FILE = """[Unit]
Description={desc}
After=network.target
[Service]
User=root
WorkingDirectory={work_dir}
{env_vars}
ExecStart={exec_start}
{exec_reload}
Restart=on-failure
RestartSec=5
LimitNOFILE=65535
[Install]
WantedBy=multi-user.target
"""

    # Naive 专用安装步骤 (需要软链接)
    INSTALL_STEP_NAIVE = """
download_bin "{url}" "{bin_path}"
rm -f /usr/bin/dogecloud
ln -s {bin_path} /usr/bin/dogecloud

echo ">> 步骤 2/3: 配置 Systemd 服务"
cat > /etc/systemd/system/{service_name}.service <<EOF
{service_content}
EOF
echo "   服务文件已创建: /etc/systemd/system/{service_name}.service"

echo ">> 步骤 3/3: 启动服务"
systemctl daemon-reload
systemctl enable {service_name}
systemctl restart {service_name}
"""

    # 单文件直接运行模式 (Hysteria2, Tuic, Juicity)
    INSTALL_STEP_SINGLE_BIN = """
download_bin "{url}" "{bin_path}"

echo ">> 步骤 2/3: 配置 Systemd 服务"
cat > /etc/systemd/system/{service_name}.service <<EOF
{service_content}
EOF
echo "   服务文件已创建: /etc/systemd/system/{service_name}.service"

echo ">> 步骤 3/3: 启动服务"
systemctl daemon-reload
systemctl enable {service_name}
systemctl restart {service_name}
"""

    # 解压模式 (Xray, Trojan) - ZIP
    INSTALL_STEP_UNZIP = """
install_unzip
echo ">> 步骤 1/3: 下载并解压 {name}"
ZIP_PATH="/tmp/{name}.zip"
rm -f $ZIP_PATH
wget -O $ZIP_PATH "{url}" -t 3 -T 20 --no-check-certificate --progress=bar:force

if [ ! -s $ZIP_PATH ]; then
    echo "   [错误] 下载失败！"
    exit 1
fi

unzip -o $ZIP_PATH -d /tmp/{name}_dist
if [ ! -f /tmp/{name}_dist/{bin_name} ]; then
    echo "   [错误] 解压失败，未找到二进制文件"
    exit 1
fi

mv -f /tmp/{name}_dist/{bin_name} {bin_path}
chmod +x {bin_path}
# 移动资源文件
if [ -f /tmp/{name}_dist/geoip.dat ]; then mv -f /tmp/{name}_dist/geoip.dat {asset_path}/; fi
if [ -f /tmp/{name}_dist/geosite.dat ]; then mv -f /tmp/{name}_dist/geosite.dat {asset_path}/; fi
rm -rf /tmp/{name}_dist $ZIP_PATH

echo "   [成功] {name} 安装完成"

echo ">> 步骤 2/3: 配置 Systemd 服务"
cat > /etc/systemd/system/{service_name}.service <<EOF
{service_content}
EOF
echo "   服务文件已创建: /etc/systemd/system/{service_name}.service"

echo ">> 步骤 3/3: 启动服务"
systemctl daemon-reload
systemctl enable {service_name}
systemctl restart {service_name}
"""

    # 解压模式 (Shadowsocks-Rust) - TAR.XZ
    INSTALL_STEP_TAR_XZ = """
install_tar
echo ">> 步骤 1/3: 下载并解压 {name}"
TAR_PATH="/tmp/{name}.tar.xz"
rm -f $TAR_PATH
wget -O $TAR_PATH "{url}" -t 3 -T 20 --no-check-certificate --progress=bar:force

if [ ! -s $TAR_PATH ]; then
    echo "   [错误] 下载失败！"
    exit 1
fi

mkdir -p /tmp/{name}_dist
tar -xf $TAR_PATH -C /tmp/{name}_dist
if [ ! -f /tmp/{name}_dist/{bin_name} ]; then
    echo "   [错误] 解压失败，未找到二进制文件"
    exit 1
fi

mv -f /tmp/{name}_dist/{bin_name} {bin_path}
chmod +x {bin_path}
rm -rf /tmp/{name}_dist $TAR_PATH

echo "   [成功] {name} 安装完成"

echo ">> 步骤 2/3: 配置 Systemd 服务"
cat > /etc/systemd/system/{service_name}.service <<EOF
{service_content}
EOF
echo "   服务文件已创建: /etc/systemd/system/{service_name}.service"

echo ">> 步骤 3/3: 启动服务"
systemctl daemon-reload
systemctl enable {service_name}
systemctl restart {service_name}
"""

    # ================= 配置文件模板 (Text) =================

    # NaiveProxy 默认配置 (用于初始化)
    CONF_NAIVE = """{{
    http_port 33372
    # domain: 
    admin off
    log {{
        output file {log_path}
        level INFO
    }}
}}
:{port}, 127.0.0.1:{port} {{
    tls admin@example.com
    route {{
        forward_proxy {{
            basic_auth dogecloud {uuid}
            hide_ip
            hide_via
            probe_resistance
        }}
        reverse_proxy https://maimai.sega.jp {{
            header_up Host {{upstream_hostport}}
            header_up X-Forwarded-Host {{host}}
        }}
    }}
}}"""

    # NaiveProxy 完整配置 (用于保存设置)
    CONF_NAIVE_FULL = """{{
    http_port {http_port}
    # domain: {domain}
    admin off
    log {{
        output file {log}
        level INFO
    }}
}}
{listen} {{
    {tls}
    route {{
        forward_proxy {{
            basic_auth {user} {password}
            hide_ip
            hide_via
            probe_resistance
        }}
        reverse_proxy https://{site} {{
            header_up Host {{upstream_hostport}}
            header_up X-Forwarded-Host {{host}}
        }}
    }}
}}"""

    # Hysteria2 默认配置 (用于初始化)
    CONF_HY2 = """listen: :{port}
bandwidth:
  up: 100 mbps
  down: 100 mbps
auth:
  type: password
  password: {uuid}
tls:
  cert: {plugin_path}/fullchain.pem
  key: {plugin_path}/privkey.pem
masquerade:
  type: proxy
  proxy:
    url: https://www.bing.com/
    rewriteHost: true
"""

    # Hysteria2 完整配置 (用于保存设置)
    CONF_HY2_FULL = """listen: :{port}
bandwidth:
  up: {up_mbps} mbps
  down: {down_mbps} mbps
tls:
  cert: {cert_path}
  key: {key_path}
auth:
  type: password
  password: {password}
masquerade:
  type: proxy
  proxy:
    url: {masquerade_url}
    rewriteHost: true
"""

    # Shadowsocks 默认配置 (Text format for init)
    CONF_SHADOWSOCKS = """{{
    "server": "::",
    "server_port": {port},
    "password": "{password}",
    "method": "2022-blake3-aes-128-gcm",
    "timeout": 300
}}"""

    # ================= 配置文件模板 (Dict/JSON) =================
    
    # Tuic V5 字典模板
    CONF_TUIC_DICT = {
        "server": "0.0.0.0:0",
        "users": {},
        "certificate": "",
        "private_key": "",
        "congestion_control": "bbr",
        "alpn": ["h3", "spdy/3.1"],
        "max_idle_time": "15s",
        "log_level": "info"
    }

    # Xray Reality 字典模板
    CONF_XRAY_REALITY_DICT = {
        "log": {"loglevel": "info", "access": "", "error": ""},
        "inbounds": [{
            "port": 0,
            "protocol": "vless",
            "settings": {
                "clients": [{"id": "", "flow": "xtls-rprx-vision"}],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "show": False,
                    "dest": "",
                    "serverNames": [],
                    "privateKey": "",
                    "publicKey": "",
                    "shortIds": []
                }
            }
        }],
        "outbounds": [{"protocol": "freedom"}]
    }

    # Xray CDN 字典模板
    CONF_XRAY_CDN_DICT = {
        "log": {"loglevel": "info", "access": "", "error": ""},
        "inbounds": [{
            "port": 0,
            "protocol": "vless",
            "settings": {
                "clients": [{"id": "", "level": 0}],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "ws",
                "security": "tls",
                "tlsSettings": {
                    "certificates": [{"certificateFile": "", "keyFile": ""}]
                },
                "wsSettings": {"path": ""}
            }
        }],
        "outbounds": [{"protocol": "freedom"}]
    }

    # Trojan-Go 字典模板
    CONF_TROJAN_DICT = {
        "run_type": "server",
        "local_addr": "0.0.0.0",
        "local_port": 0,
        "remote_addr": "127.0.0.1",
        "remote_port": 80,
        "password": [],
        "ssl": {"cert": "", "key": "", "sni": ""}
    }

    # Juicity 字典模板
    CONF_JUICITY_DICT = {
        "listen": ":0",
        "users": {},
        "certificate": "",
        "private_key": "",
        "congestion_control": "bbr",
        "log_level": "info"
    }

    # Shadowsocks 字典模板
    CONF_SHADOWSOCKS_DICT = {
        "server": "::",
        "server_port": 0,
        "password": "",
        "method": "2022-blake3-aes-128-gcm",
        "timeout": 300
    }