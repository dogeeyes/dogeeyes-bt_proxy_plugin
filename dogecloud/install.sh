# dogecloud/install.sh
#!/bin/bash
PATH=/www/server/panel/pyenv/bin:/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

PLUGIN_PATH="/www/server/panel/plugin/dogecloud"

Install_dogecloud()
{
    # 1. 创建基础目录结构 (对应 Python 中的 __conf_dir 和 __log_dir)
    mkdir -p ${PLUGIN_PATH}/conf
    mkdir -p ${PLUGIN_PATH}/logs
    chmod 755 ${PLUGIN_PATH}
    chmod 755 ${PLUGIN_PATH}/conf
    chmod 755 ${PLUGIN_PATH}/logs
    
    # 注意：配置文件生成已移交由 Python 后端 (dogecloud_main.py) 统一处理。
    # 当用户首次打开插件或请求数据时，后端会自动检测并生成所有协议(Naive/Hy2/Tuic/Xray/SS等)的默认配置。
    # 这样可以避免 Shell 脚本和 Python 代码逻辑不一致的问题。

    echo '安装完成'
}

Uninstall_dogecloud()
{
    # 1. 强制清理所有相关进程
    echo "正在终止进程..."
    pkill -9 -f dogecloud-naive
    pkill -9 -f dogecloud-hy2
    pkill -9 -f dogecloud-tuic
    pkill -9 -f dogecloud-juicity
    pkill -9 -f dogecloud-xray
    pkill -9 -f dogecloud-vless-cdn
    pkill -9 -f dogecloud-trojan
    pkill -9 -f dogecloud-ssserver
    pkill -9 -f dogecloud-shadowsocks
    
    # 2. 删除所有二进制文件
    echo "正在删除二进制文件..."
    rm -f /usr/bin/dogecloud
    rm -f /usr/bin/dogecloud-naive
    rm -f /usr/bin/dogecloud-hy2
    rm -f /usr/bin/dogecloud-tuic
    rm -f /usr/bin/dogecloud-juicity
    rm -f /usr/bin/dogecloud-xray
    rm -f /usr/bin/dogecloud-trojan
    rm -f /usr/bin/dogecloud-ssserver

    # 3. 清理 Systemd 服务
    echo "正在清理服务..."
    services=(
        "dogecloud-naive" 
        "dogecloud-hy2" 
        "dogecloud-tuic" 
        "dogecloud-juicity" 
        "dogecloud-xray" 
        "dogecloud-vless-cdn" 
        "dogecloud-trojan" 
        "dogecloud-shadowsocks"
    )
    
    for svc in "${services[@]}"; do
        if [ -f "/etc/systemd/system/${svc}.service" ]; then
            systemctl stop ${svc}
            systemctl disable ${svc}
            rm -f /etc/systemd/system/${svc}.service
        fi
    done
    
    # 兼容旧版服务名清理
    if [ -f "/etc/systemd/system/dogecloud.service" ]; then
         systemctl stop dogecloud
         systemctl disable dogecloud
         rm -f /etc/systemd/system/dogecloud.service
    fi
    
    systemctl daemon-reload
    
    # 4. 删除插件目录
    rm -rf ${PLUGIN_PATH}
    echo "卸载成功"
}

action=$1
if [ "${1}" == 'install' ];then
    Install_dogecloud
else
    Uninstall_dogecloud
fi