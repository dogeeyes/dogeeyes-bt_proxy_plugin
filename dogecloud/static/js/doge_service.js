// dogecloud/static/js/doge_service.js
var doge_service = {
    render_status: function (currentType) {
      var _that = this;
      bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=get_service_info', data: {type: currentType}}, function (rdata) {
        var ctrlBtns = '', infoBtn = '';
        var btn = [{title:'启动', value: 'start'},{title:'停止', value: 'stop'},{title:'重启', value: 'restart'}];
        
        for (var j = 0; j < btn.length; j++) {
          if(rdata.status === true && btn[j].value == 'start') continue;
          if(rdata.status === false && btn[j].value == 'stop') continue;
          ctrlBtns += '<button class="btn btn-default btn-sm mr16" data-action="'+btn[j].value+'">'+btn[j].title+'</button>';
        }
        
        if(rdata.install_status) {
            ctrlBtns += '<button class="btn btn-danger btn-sm mr16" data-action="uninstall">卸载</button>';
        }
        
        infoBtn = '<button class="btn btn-info btn-sm mr16 show-proto-info">协议介绍</button>';
        
        var content = '';
        if(!rdata.install_status) {
            content = '<div class="soft-man-con"><div class="alert alert-warning">当前协议服务未安装，<a href="javascript:;" class="btlink install_btn">点击安装</a></div></div>';
            content += '<div class="mt10">' + infoBtn + '</div>'; 
        } else {
            var statusHtml = '<div class="soft-man-con" style="padding-top: 10px;">\
                <div style="display:flex; justify-content:space-between; align-items:center;">\
                    <p class="status">运行状态: <span>'+ (rdata.status ? '运行中' : '已停止') +'</span>\
                    <span style="color: '+(rdata.status ? '#20a53a' : 'red' ) + '; margin-left: 3px;" class="glyphicon glyphicon '+ (rdata.status ? 'glyphicon-play' : 'glyphicon-pause') +'"></span></p>\
                    <div class="text-right" style="color:#888; font-size:12px;">运行时长: ' + (rdata.process.uptime || '0') + '</div>\
                </div>';
            
            statusHtml += '<div class="mt10">' + ctrlBtns + infoBtn + '</div>';
            
            statusHtml += '<div class="mt20"><strong>当前节点配置:</strong><div class="client-config-box"><pre id="client-code">' + rdata.client_config + '</pre></div>\
                <button class="btn btn-xs btn-success mt10 copy-config">复制配置</button>\
                <button class="btn btn-xs btn-info mt10 show-qrcode" style="margin-left:5px">二维码</button>\
                </div>\
                <div class="mt20"><strong>当前节点链接:</strong><div class="client-config-box"><pre id="client-code">' + rdata.share_url + '</pre></div>\
            </div></div>';
            
            content = statusHtml;
        }

        $('#webEdit-con .tab-con .tab-block.on').html(content);
        
        $('.show-proto-info').unbind('click').click(function(){
            var loadT = layer.msg('正在获取信息...', {icon: 16, time: 0, shade: 0.3});
            bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=get_protocol_info'}, function(res){
                layer.close(loadT);
                if(res.status) {
                    var info = res.msg[currentType];
                    if(!info) {
                        layer.msg('暂无该协议信息', {icon: 2});
                        return;
                    }
                    
                    var content = '<div style="padding: 20px;">\
                        <h3 style="margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px;">' + info.name + ' <a href="' + info.github + '" target="_blank" style="font-size: 12px; float: right; margin-top: 5px;" class="btlink">GitHub 项目主页 <span class="glyphicon glyphicon-new-window"></span></a></h3>\
                        <div style="margin-bottom: 15px; color: #666; line-height: 1.6;">' + info.description + '</div>\
                        <table class="proto-info-table" style="width: 100%; margin-bottom: 20px;">\
                            <tr><td class="proto-label">安全性</td><td>' + info.security + '</td></tr>\
                            <tr><td class="proto-label">速度</td><td>' + info.speed + '</td></tr>\
                        </table>\
                    </div>';
                    
                    layer.open({
                        type: 1,
                        title: '协议详情 - ' + info.name,
                        area: ['500px', '350px'],
                        shadeClose: true,
                        content: content,
                        btn: ['关闭']
                    });
                } else {
                    layer.msg(res.msg, {icon: 2});
                }
            });
        });
        
        $('.install_btn').unbind('click').click(function(){
            // 增加风险提示弹窗
            layer.confirm('⚠️ 警告：该工具千万不要在腾讯云、阿里云、天翼云、百度云等中国的云主机使用，有可能导致很严重的后果（封号、警告等）！<br><br>确定要继续安装吗？', {
                title: '风险提示',
                icon: 0, // 警告图标
                btn: ['继续安装', '取消'],
                btn2: function(index){
                    layer.close(index);
                }
            }, function(index){
                layer.close(index);
                // 用户确认后，执行安装逻辑
                bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=install_service', data: {type: currentType}}, function(res){
                    if(res.status) {
                        var logLayer = layer.open({
                            type: 1,
                            title: '正在安装 ' + currentType + ' 服务',
                            area: ['600px', '450px'],
                            closeBtn: 0, 
                            content: '<div class="pd15"><pre id="install-log" style="background:#333;color:#fff;padding:10px;height:320px;overflow:auto;font-family:Consolas;font-size:12px;border-radius:4px;">正在启动安装任务...</pre></div>',
                            btn: ['后台运行'], 
                            yes: function(idx){
                                layer.close(idx);
                                layer.msg('安装将在后台继续，请稍后刷新状态');
                                if(timer) clearInterval(timer);
                            }
                        });
                        
                        var timer = setInterval(function(){
                            bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=get_install_log'}, function(logs){
                                var logContent = logs.msg || logs;
                                $('#install-log').text(logContent);
                                var elem = document.getElementById('install-log');
                                if(elem) elem.scrollTop = elem.scrollHeight;
                                
                                if(logContent.indexOf('安装完成|Success') > -1) {
                                    clearInterval(timer);
                                    layer.close(logLayer);
                                    layer.msg('安装成功', {icon: 1});
                                    _that.render_status(currentType);
                                } else if(logContent.indexOf('安装失败|Failed') > -1) {
                                    clearInterval(timer);
                                    layer.msg('安装失败，请检查日志', {icon: 2});
                                    $('.layui-layer-btn0').text('关闭');
                                }
                            }, {verify:false, load_T:false});
                        }, 1500);
                    } else {
                        bt_tools.msg(res);
                    }
                });
            });
        });

        $('.copy-config').unbind('click').click(function(){ doge_utils.copyText($('#client-code').text()); });

        $('.show-qrcode').unbind('click').click(function(){
            if(!rdata.qrcode) {
                layer.msg('二维码生成失败或库未安装', {icon: 2});
                return;
            }
            layer.open({
                type: 1,
                title: false,
                closeBtn: 0,
                area: ['300px', '300px'],
                shadeClose: true,
                content: '<div style="text-align:center;padding:20px;"><img src="'+rdata.qrcode+'" style="width:250px;height:250px;"/></div>'
            });
        });

        $('button[data-action]').unbind('click').click(function(){
            var act = $(this).data('action');
            if(act == 'uninstall') {
                bt.confirm({title: '卸载确认', msg: '确定要卸载 ' + currentType + ' 服务吗？这将删除相关二进制文件和服务配置。'}, function(){
                    var loadT = layer.msg('正在卸载中...', {icon: 16, time: 0, shade: 0.3});
                    bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=uninstall_service', data: {type: currentType}}, function(res){
                        layer.close(loadT);
                        layer.open({
                            type: 1,
                            title: '卸载结果',
                            area: ['500px', '300px'],
                            content: '<div class="pd15"><pre style="background:#f5f5f5;padding:10px;height:180px;overflow:auto;font-size:12px;">' + res.msg + '</pre></div>',
                            btn: ['确定'],
                            yes: function(index){
                                layer.close(index);
                                _that.render_status(currentType);
                            }
                        });
                    });
                });
                return;
            }
            bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=service_admin', data: {type: currentType, status: act}}, function(res){
                bt_tools.msg(res);
                _that.render_status(currentType);
            });
        });
      });
    },

    render_form: function (currentType) {
      var _that = this;
      bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=get_form_config', data: {type: currentType}}, function (res) {
        var formItems = [];
        var inputWidth = '320px'; 
        
        var certGroup = [
            { label: '证书公钥', group: [{ type: 'text', name: 'cert_path', width: '350px', value: res.cert_path, icon: { type: 'glyphicon-folder-open' }, placeholder: '例如: /www/server/panel/vhost/cert/你的域名/fullchain.pem' }] },
            { label: '证书私钥', group: [{ type: 'text', name: 'key_path', width: '350px', value: res.key_path, icon: { type: 'glyphicon-folder-open' }, placeholder: '例如: /www/server/panel/vhost/cert/你的域名/privkey.pem' }] }
        ];

        if (currentType == 'naive') {
            formItems = [
                { label: '监听端口', group: [{ type: 'number', name: 'port', width: inputWidth, value: res.port }] },
                { label: '内部HTTP端口', group: [{ type: 'number', name: 'http_port', width: inputWidth, value: res.http_port, placeholder: '33372' }] },
                { label: '绑定域名', group: [{ type: 'text', name: 'domain', width: inputWidth, value: res.domain, placeholder: '可选，留空则使用公网IP' }] },
                { label: '用户名', group: [{ type: 'text', name: 'user', width: inputWidth, value: res.user }] },
                { label: '密码', group: [{ type: 'text', name: 'password', width: inputWidth, value: res.password }] },
                { label: '伪装网站', group: [{ type: 'text', name: 'proxy_site', width: inputWidth, value: res.proxy_site }] }
            ].concat(certGroup);
        } else if (currentType == 'hy2') {
            formItems = [
                { label: '监听端口', group: [{ type: 'number', name: 'port', width: inputWidth, value: res.port }] },
                { label: '验证密码', group: [{ type: 'text', name: 'password', width: inputWidth, value: res.password }] },
                { label: '上行带宽', group: [{ type: 'number', name: 'up_mbps', width: inputWidth, value: res.up_mbps, unit: 'Mbps' }] },
                { label: '下行带宽', group: [{ type: 'number', name: 'down_mbps', width: inputWidth, value: res.down_mbps, unit: 'Mbps' }] },
                { label: '伪装网址', group: [{ type: 'text', name: 'masquerade_url', width: inputWidth, value: res.masquerade_url }] }
            ].concat(certGroup);
        } else if (currentType == 'tuic') {
            var tuic_cc = res.congestion_control || 'bbr';
            formItems = [
                { label: '监听端口', group: [{ type: 'number', name: 'port', width: inputWidth, value: res.port }] },
                { label: 'UUID', group: [{ type: 'text', name: 'uuid', width: inputWidth, value: res.uuid }] },
                { label: '密码', group: [{ type: 'text', name: 'password', width: inputWidth, value: res.password }] },
                { label: '拥塞控制', group: [{ type: 'text', name: 'congestion_control', width: inputWidth, value: tuic_cc, placeholder: 'bbr, cubic, new_reno' }] }
            ].concat(certGroup);
        } else if (currentType == 'xray') {
            formItems = [
                { label: '监听端口', group: [{ type: 'number', name: 'port', width: inputWidth, value: res.port }] },
                { label: 'UUID', group: [{ type: 'text', name: 'uuid', width: inputWidth, value: res.uuid }] },
                { label: '私钥', group: [{ type: 'text', name: 'private_key', width: '240px', value: res.private_key, placeholder: 'X25519 私钥' }] },
                { label: '公钥', group: [{ type: 'text', name: 'public_key', width: inputWidth, value: res.public_key, readonly: true, placeholder: '自动计算，只读', style: 'background-color: #eee;' }] },
                { label: 'SNI 域名', group: [{ type: 'text', name: 'sni', width: inputWidth, value: res.sni, placeholder: '例如: www.microsoft.com' }] },
                { label: '回落目标', group: [{ type: 'text', name: 'dest', width: inputWidth, value: res.dest, placeholder: '例如: www.microsoft.com:443' }] },
                { label: 'Short ID', group: [{ type: 'text', name: 'short_id', width: inputWidth, value: res.short_id, placeholder: '可选，16进制字符串' }] }
            ];
        } else if (currentType == 'vless_cdn') {
            formItems = [
                { label: '监听端口', group: [{ type: 'number', name: 'port', width: inputWidth, value: res.port }] },
                { label: 'UUID', group: [{ type: 'text', name: 'uuid', width: inputWidth, value: res.uuid }] },
                { label: 'WS Path', group: [{ type: 'text', name: 'path', width: inputWidth, value: res.path, placeholder: '/ws' }] }
            ].concat(certGroup);
        } else if (currentType == 'trojan') {
            formItems = [
                { label: '监听端口', group: [{ type: 'number', name: 'port', width: inputWidth, value: res.port }] },
                { label: '密码', group: [{ type: 'text', name: 'password', width: inputWidth, value: res.password }] },
                { label: '回落地址', group: [{ type: 'text', name: 'remote_addr', width: inputWidth, value: res.remote_addr, placeholder: '127.0.0.1' }] },
                { label: '回落端口', group: [{ type: 'number', name: 'remote_port', width: '100px', value: res.remote_port, placeholder: '80' }] }
            ].concat(certGroup);
        } else if (currentType == 'juicity') {
            var juicity_cc = res.congestion_control || 'bbr';
            formItems = [
                { label: '监听端口', group: [{ type: 'number', name: 'port', width: inputWidth, value: res.port }] },
                { label: 'UUID', group: [{ type: 'text', name: 'uuid', width: inputWidth, value: res.uuid }] },
                { label: '密码', group: [{ type: 'text', name: 'password', width: inputWidth, value: res.password }] },
                { label: '拥塞控制', group: [{ type: 'text', name: 'congestion_control', width: inputWidth, value: juicity_cc, placeholder: 'bbr, cubic, new_reno' }] }
            ].concat(certGroup);
        } else if (currentType == 'shadowsocks') {
            var ss_method = res.method || '2022-blake3-aes-128-gcm';
            formItems = [
                { label: '监听端口', group: [{ type: 'number', name: 'port', width: inputWidth, value: res.port }] },
                { label: '加密方式', group: [{ type: 'text', name: 'method', width: inputWidth, value: ss_method, placeholder: '2022-blake3-aes-128-gcm' }] },
                { label: '密钥', group: [{ type: 'text', name: 'password', width: '240px', value: res.password, placeholder: 'Base64 编码的密钥' }] }
            ];
        }

        formItems.push({ label: '', group: [{ type: 'button', title: '保存配置', name: 'save-btn' }] });

        $('#webEdit-con .tab-con .tab-block.on').html('<div class="server-config" style="height: 510px;overflow: auto;"></div>');
        var configForm = bt_tools.form({ el: '.server-config', data: res, form: formItems });

        // Xray 密钥生成按钮逻辑
        if (currentType == 'xray') {
            var $pkInput = $('.server-config [name="private_key"]');
            if ($pkInput.length > 0) {
                $pkInput.after('<button class="btn btn-default btn-sm ml5 generate-key" type="button">生成密钥</button>');
                $('.generate-key').click(function(){
                    var loadT = layer.msg('正在生成密钥...', {icon: 16, time: 0, shade: 0.3});
                    bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=generate_reality_keys'}, function(res){
                        layer.close(loadT);
                        if(res.status) {
                            $pkInput.val(res.msg.private_key);
                            $('.server-config [name="public_key"]').val(res.msg.public_key);
                            layer.msg('密钥生成成功', {icon: 1});
                        } else {
                            layer.msg(res.msg, {icon: 2});
                        }
                    });
                });
            }
        }
        
        // Shadowsocks 密钥生成按钮逻辑
        if (currentType == 'shadowsocks') {
            var $pwdInput = $('.server-config [name="password"]');
            if ($pwdInput.length > 0) {
                $pwdInput.after('<button class="btn btn-default btn-sm ml5 generate-ss-key" type="button">生成密钥</button>');
                $('.generate-ss-key').click(function(){
                    var method = $('.server-config input[name="method"]').val();
                    var loadT = layer.msg('正在生成密钥...', {icon: 16, time: 0, shade: 0.3});
                    bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=generate_ss_key', data: {method: method}}, function(res){
                        layer.close(loadT);
                        if(res.status) {
                            $pwdInput.val(res.msg.key);
                            layer.msg('密钥生成成功', {icon: 1});
                        } else {
                            layer.msg(res.msg, {icon: 2});
                        }
                    });
                });
            }
        }

        setTimeout(function(){
            $('.server-config input[name="cert_path"], .server-config input[name="key_path"]').each(function(){
                var $input = $(this);
                var $icon = $input.next('.input-group-addon');
                $icon.css({'cursor':'pointer', 'pointer-events':'auto'}).attr('title','选择文件');
                $icon.off('click').on('click', function(){
                    bt.select_path($input.attr('name'), true, function(path){
                        $input.val(path);
                    }, '请选择证书文件');
                });
            });
        }, 500);

        $('.server-config button[name="save-btn"]').unbind('click').click(function () {
            var formData = configForm.$get_form_value();
            formData.type = currentType;
            bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=set_form_config', data: formData}, function (rdata) {
                bt_tools.msg(rdata);
            });
        });
      });
    },

    render_file: function (currentType) {
      var pathMap = {
          'naive': '/www/server/panel/plugin/dogecloud/conf/Caddyfile',
          'hy2': '/www/server/panel/plugin/dogecloud/conf/config_hy2.yaml',
          'tuic': '/www/server/panel/plugin/dogecloud/conf/config_tuic.json',
          'xray': '/www/server/panel/plugin/dogecloud/conf/config_xray.json',
          'vless_cdn': '/www/server/panel/plugin/dogecloud/conf/config_vless_cdn.json',
          'trojan': '/www/server/panel/plugin/dogecloud/conf/config_trojan.json',
          'juicity': '/www/server/panel/plugin/dogecloud/conf/config_juicity.json',
          'shadowsocks': '/www/server/panel/plugin/dogecloud/conf/config_shadowsocks.json'
      };
      var configPath = pathMap[currentType];

      $('#webEdit-con .tab-con .tab-block.on').html(
          '<p style="color: #666; margin-bottom: 7px">提示：Ctrl+S 保存</p>\
           <div class="bt-input-text ace_config_editor_scroll" style="height: 400px; line-height:18px;" id="configFile"></div>\
           <button class="OnlineEditFileBtn btn btn-success btn-sm" style="margin-top:10px;">保存</button>'
      );

      bt_tools.send({url: '/files?action=GetFileBody', data: {path: configPath}}, function(res) {
        var config = bt.aceEditor({ el: 'configFile', content: res.status ? res.data : '', readOnly: false });
        var saveFunc = function() {
            config.path = configPath;
            bt.saveEditor(config);
        };
        config.ACE.commands.addCommand({ name: '保存', bindKey: { win: 'Ctrl-S', mac: 'Command-S' }, exec: saveFunc });
        $('.OnlineEditFileBtn').unbind('click').click(saveFunc);
      });
    },

    render_logs: function (currentType) {
      var pathMap = {
          'naive': '/www/server/panel/plugin/dogecloud/logs/caddy.log',
          'hy2': '/www/server/panel/plugin/dogecloud/logs/hy2.log',
          'tuic': '/www/server/panel/plugin/dogecloud/logs/tuic.log',
          'xray': '/www/server/panel/plugin/dogecloud/logs/xray.log',
          'vless_cdn': '/www/server/panel/plugin/dogecloud/logs/vless_cdn.log',
          'trojan': '/www/server/panel/plugin/dogecloud/logs/trojan.log',
          'juicity': '/www/server/panel/plugin/dogecloud/logs/juicity.log',
          'shadowsocks': '/www/server/panel/plugin/dogecloud/logs/shadowsocks.log'
      };
      var logPath = pathMap[currentType];

      $('#webEdit-con .tab-con .tab-block.on').html(
          '<div class="logs-box"><div class="mb10 flex"><button class="btn btn-success btn-sm refresh mr16">刷新</button><button class="btn btn-danger btn-sm clear-log">清空</button></div>\
           <div class="logs-content"><div class="bt-form" id="serviceLogs" style="height: 410px;"></div></div></div>'
      );

      var get_logs = function() {
          bt_tools.send({url: '/files?action=GetFileBody', data: {path: logPath}}, function(res) {
              var content = res.status ? res.data : '暂无日志或读取失败';
              var aEditor = bt.aceEditor({ el: 'serviceLogs', mode:'text', content: content, readOnly: true, theme:'ace/theme/monokai' });
              setTimeout(function(){ aEditor.ACE.getSession().setScrollTop(aEditor.ACE.renderer.scrollBar.scrollHeight); }, 50);
          });
      };
      
      get_logs();
      $('.refresh').unbind('click').click(get_logs);
      
      $('.clear-log').unbind('click').click(function(){
          bt.confirm({title:'清空日志', msg:'确定要清空当前服务的运行日志吗？此操作不可恢复。'}, function(){
              bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=clear_service_log', data: {type: currentType}}, function(res){
                  bt_tools.msg(res);
                  get_logs();
              });
          });
      });
    }
};