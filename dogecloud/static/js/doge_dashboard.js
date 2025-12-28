// dogecloud/static/js/doge_dashboard.js
var doge_dashboard = {
    render: function(main_obj) {
        var _that = this;
        var loadT = layer.msg('正在加载控制台数据...', {icon: 16, time: 0, shade: 0.3});
        
        bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=get_dashboard_data'}, function(res){
            layer.close(loadT);
            if(!res.status) {
                $('#webEdit-con').html('<div class="alert alert-danger">数据加载失败: ' + res.msg + '</div>');
                return;
            }
            
            var data = res.msg;
            var html = '<div style="padding: 10px;">';
            
            // 1. 聚合订阅卡片
            html += '<div class="sub-card" style="margin-top:0;">\
                <div style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">\
                    <strong style="color:#2e7d32; font-size:16px;"><span class="glyphicon glyphicon-link"></span> 聚合订阅中心</strong>';
            
            // 只有当不是所有协议都安装时，才显示一键安装按钮
            if (!data.all_installed) {
                html += '<button class="btn btn-primary btn-sm install-all-btn"><span class="glyphicon glyphicon-flash"></span> 一键安装所有协议</button>';
            }
            
            html += '</div>\
                <div style="color:#666; font-size:12px; margin-bottom: 15px;">当前已聚合 <b>' + data.sub_count + '</b> 个可用节点，支持一键导入所有配置。</div>';
            
            if (data.sub_bind) {
                // 已绑定网站 - 显示 URL 二维码
                html += '<div style="display:flex; gap: 10px; flex-wrap: wrap;">\
                        <button class="btn btn-success btn-sm copy-link" data-link="' + data.sub_bind.base64_url + '">Base</button>\
                        <button class="btn btn-default btn-sm show-qr" data-qr="' + data.sub_bind.base64_qr + '">订阅二维码</button>\
                        <button class="btn btn-info btn-sm copy-link" data-link="' + data.sub_bind.clash_url + '">Clash配置</button>\
                        <button class="btn btn-default btn-sm copy-raw-links" data-link="' + encodeURIComponent(data.sub_raw) + '">所有链接</button>\
                        <button class="btn btn-danger btn-sm unbind-site" style="margin-left:auto;">解绑订阅网站</button>\
                    </div>';
            } else {
                // 未绑定 - 移除二维码按钮，引导绑定
                html += '<div style="display:flex; gap: 10px; flex-wrap: wrap;">\
                        <button class="btn btn-success btn-sm copy-dash-sub" data-link="' + data.subscription + '">Base64</button>\
                        <!-- 未绑定网站时不显示二维码，因为内容太长无法生成链接二维码 -->\
                        <button class="btn btn-default btn-sm get-clash-conf">Clash配置</button>\
                        <button class="btn btn-info btn-sm copy-raw-links" data-link="' + encodeURIComponent(data.sub_raw) + '">所有链接</button>\
                        <button class="btn btn-primary btn-sm bind-site-btn" style="margin-left:auto;">配置订阅网站</button>\
                    </div>';
            }
            
            html += '<div style="margin-top:10px; font-size:12px; color:#888; border-top: 1px solid #c8e6c9; padding-top: 8px;">\
                    <span class="glyphicon glyphicon-info-sign"></span> 提示：如需使用<b>订阅二维码</b>或<b>HTTP订阅链接</b>，请点击右侧"配置自动订阅"绑定一个网站。\
                </div>\
            </div>';
            
            // 2. 服务监控列表
            html += '<div class="dash-section-title">服务监控</div>';
            html += '<table class="table table-hover table-bordered dashboard-table" style="background:#fff;">\
                <thead><tr><th>协议名称</th><th>状态</th><th>端口</th><th>CPU</th><th>内存</th><th>运行时长</th><th>操作</th></tr></thead>\
                <tbody>';
            
            for(var i=0; i<data.services.length; i++) {
                var svc = data.services[i];
                var statusClass = svc.status ? 'on' : 'off';
                var statusText = svc.status ? '运行中' : (svc.installed ? '已停止' : '未安装');
                
                html += '<tr>\
                    <td>' + svc.name + '</td>\
                    <td><span class="status-dot ' + statusClass + '"></span>' + statusText + '</td>\
                    <td>' + svc.port + '</td>\
                    <td>' + (svc.status ? svc.cpu + '%' : '-') + '</td>\
                    <td>' + (svc.status ? svc.memory + ' MB' : '-') + '</td>\
                    <td>' + svc.uptime + '</td>\
                    <td>';
                
                if(svc.installed) {
                    if(svc.status) {
                        html += '<button class="btn btn-default btn-xs svc-action" data-type="'+svc.type+'" data-act="restart">重启</button> ';
                        html += '<button class="btn btn-default btn-xs svc-action" data-type="'+svc.type+'" data-act="stop">停止</button>';
                    } else {
                        html += '<button class="btn btn-success btn-xs svc-action" data-type="'+svc.type+'" data-act="start">启动</button>';
                    }
                } else {
                    html += '<span class="text-muted">未安装</span>';
                }
                
                html += '</td></tr>';
            }
            html += '</tbody></table>';
            
            // 3. 全平台客户端下载推荐
            html += '<div class="dash-section-title">全平台客户端推荐</div>';
            html += '<table class="table table-bordered table-hover dashboard-table" style="background:#fff;">\
                <thead><tr><th width="100">平台</th><th>推荐客户端</th><th>说明</th><th>下载</th></tr></thead>\
                <tbody>';
            
            var recs = data.downloads.global_recommendations || {};
            var keys = Object.keys(recs);
            
            var getIcon = function(key) {
                key = key.toLowerCase();
                if(key.indexOf('ios') > -1) return 'apple';
                if(key.indexOf('android') > -1) return 'phone';
                if(key.indexOf('win') > -1 || key.indexOf('desktop') > -1) return 'modal-window';
                if(key.indexOf('mac') > -1) return 'console';
                return 'download-alt';
            };

            for(var i=0; i<keys.length; i++) {
                var key = keys[i];
                var items = recs[key] || [];
                var icon = getIcon(key);
                var displayName = key.charAt(0).toUpperCase() + key.slice(1);
                
                if(items.length > 0) {
                    html += '<tr>';
                    html += '<td rowspan="' + items.length + '" style="vertical-align:middle;text-align:center;background:#f9f9f9;"><span class="glyphicon glyphicon-'+icon+'" style="font-size:20px;display:block;margin-bottom:5px;"></span> '+displayName+'</td>';
                    
                    for(var j=0; j<items.length; j++) {
                        var item = items[j];
                        if(j > 0) html += '<tr>';
                        html += '<td><strong>'+item.name+'</strong></td>\
                                <td style="color:#666; font-size:12px;">'+item.desc+'</td>\
                                <td><a href="'+item.url+'" target="_blank" class="btn btn-success btn-xs">下载</a></td>\
                            </tr>';
                    }
                }
            }
            html += '</tbody></table>';
            
            html += '</div>';
            $('#webEdit-con').html(html);
            
            // 绑定事件
            $('.copy-link').click(function(){
                var link = $(this).data('link');
                doge_utils.copyText(link);
            });

            $('.copy-raw-links').click(function(){
                var raw = decodeURIComponent($(this).data('link'));
                if(!raw) { layer.msg('暂无可用节点', {icon: 2}); return; }
                doge_utils.copyText(raw);
            });
            
            $('.show-qr').click(function(){
                var qr = $(this).data('qr');
                if(!qr) { layer.msg('二维码生成失败', {icon: 2}); return; }
                layer.open({
                    type: 1,
                    title: '订阅二维码',
                    area: ['300px', '340px'],
                    shadeClose: true,
                    content: '<div style="margin:20px auto;text-align:center;"><img src="'+qr+'" style="width:200px;height:200px;"/></div><div style="text-align:center;color:#666;">请使用客户端扫描</div>'
                });
            });

            // 一键安装所有协议
            $('.install-all-btn').click(function(){
                // 1. 获取网站列表
                bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=get_ssl_sites'}, function(res){
                    if(res.status) {
                        var sites = res.msg;
                        if(sites.length == 0) {
                            layer.alert('当前面板没有已配置SSL证书的网站，无法进行一键配置。<br>请先在"网站"管理中添加一个网站，并申请SSL证书。', {icon: 2, title: '前置条件不足'});
                            return;
                        }
                        
                        // 2. 获取协议安装状态
                        bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=get_protocol_install_status'}, function(statusRes){
                            var installStatus = statusRes.msg || {};
                            
                            var options = '';
                            for(var i=0; i<sites.length; i++) {
                                options += '<option value="'+sites[i].path+'" data-name="'+sites[i].name+'">'+sites[i].name+'</option>';
                            }
                            
                            // 协议列表映射
                            var protocols = [
                                {id: 'naive', name: 'NaiveProxy'},
                                {id: 'hy2', name: 'Hysteria2'},
                                {id: 'tuic', name: 'Tuic V5'},
                                {id: 'xray', name: 'VLESS-Reality'},
                                {id: 'vless_cdn', name: 'VLESS+CDN'},
                                {id: 'trojan', name: 'Trojan-Go'},
                                {id: 'juicity', name: 'Juicity'},
                                {id: 'shadowsocks', name: 'Shadowsocks'}
                            ];
                            
                            // 修改：使用 Flex 布局实现一行两个
                            var checkboxes = '<div class="protocol-list" style="margin-top:10px; border:1px solid #eee; padding:10px; border-radius:4px; max-height:150px; overflow-y:auto; display:flex; flex-wrap:wrap;">';
                            for(var j=0; j<protocols.length; j++) {
                                var p = protocols[j];
                                var isInstalled = installStatus[p.id];
                                var disabledAttr = isInstalled ? 'disabled' : 'checked';
                                var labelClass = isInstalled ? 'disabled-protocol-label' : '';
                                var title = isInstalled ? ' (已安装)' : '';
                                
                                // 修改：设置宽度为 50%
                                checkboxes += '<div class="checkbox" style="width:50%; margin:5px 0; padding-right:10px; box-sizing:border-box;">\
                                    <label class="'+labelClass+'" style="width:100%; cursor:'+(isInstalled?'not-allowed':'pointer')+'">\
                                        <input type="checkbox" name="protocols" value="'+p.id+'" '+disabledAttr+'> '+p.name + title + '\
                                    </label>\
                                </div>';
                            }
                            checkboxes += '</div>';
                            
                            layer.open({
                                type: 1,
                                title: '一键安装协议',
                                area: ['500px', '500px'],
                                content: '<div class="pd15">\
                                    <div class="alert alert-danger" style="font-weight:bold; color:#a94442; margin-bottom:10px;">\
                                        ⚠️ 警告：该工具千万不要在腾讯云、阿里云、天翼云、百度云等中国的云主机使用，有可能导致很严重的后果（封号、警告等）！\
                                    </div>\
                                    <div class="alert alert-warning" style="margin-bottom:10px;font-size:12px;">\
                                        此操作将为选中协议生成随机端口和密钥，并使用选定网站的 SSL 证书配置 TLS。\
                                    </div>\
                                    <div class="form-group">\
                                        <label>选择绑定网站 (需有SSL)</label>\
                                        <select class="bt-input-text mr5" id="install-site-select" style="width:100%">'+options+'</select>\
                                    </div>\
                                    <div class="form-group">\
                                        <label>选择要安装的协议</label>\
                                        '+checkboxes+'\
                                    </div>\
                                    <div class="mt10 text-right"><button class="btn btn-primary btn-sm" id="confirm-install-all">开始安装</button></div>\
                                </div>',
                                success: function(layero, index){
                                    $('#confirm-install-all').click(function(){
                                        var $sel = $('#install-site-select option:selected');
                                        var path = $sel.val();
                                        var name = $sel.data('name');
                                        
                                        // 收集选中的协议
                                        var selectedProtocols = [];
                                        $('input[name="protocols"]:checked').each(function(){
                                            selectedProtocols.push($(this).val());
                                        });
                                        
                                        if(selectedProtocols.length === 0) {
                                            layer.msg('请至少选择一个协议', {icon: 2});
                                            return;
                                        }
                                        
                                        layer.close(index);
                                        var loadT = layer.msg('正在生成配置并启动安装任务...', {icon: 16, time: 0, shade: 0.3});
                                        
                                        // 调用 batch_install，传递协议列表
                                        bt_tools.send({
                                            url: '/plugin?action=a&name=dogecloud&s=batch_install', 
                                            data: {
                                                site_path: path, 
                                                site_name: name,
                                                protocols: JSON.stringify(selectedProtocols)
                                            }
                                        }, function(r){
                                            layer.close(loadT);
                                            if(r.status) {
                                                // 显示日志窗口
                                                var logLayer = layer.open({
                                                    type: 1,
                                                    title: '批量安装进度',
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
                                                            layer.msg('所有服务安装完成', {icon: 1});
                                                            _that.render(main_obj);
                                                        } else if(logContent.indexOf('安装失败|Failed') > -1) {
                                                            clearInterval(timer);
                                                            layer.msg('部分服务安装失败，请检查日志', {icon: 2});
                                                            $('.layui-layer-btn0').text('关闭');
                                                        }
                                                    }, {verify:false, load_T:false});
                                                }, 1500);
                                            } else {
                                                layer.alert(r.msg, {icon: 2});
                                            }
                                        });
                                    });
                                }
                            });
                        });
                    }
                });
            });

            $('.bind-site-btn').click(function(){
                bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=get_site_list'}, function(res){
                    if(res.status) {
                        var sites = res.msg;
                        if(sites.length == 0) {
                            layer.msg('当前面板没有添加网站，请先添加一个网站用于存放订阅文件。', {icon: 2});
                            return;
                        }
                        
                        var options = '';
                        for(var i=0; i<sites.length; i++) {
                            options += '<option value="'+sites[i].path+'" data-name="'+sites[i].name+'">'+sites[i].name+' ('+sites[i].path+')</option>';
                        }
                        
                        layer.open({
                            type: 1,
                            title: '选择绑定网站',
                            area: ['400px', '250px'],
                            content: '<div class="pd15">\
                                <div class="alert alert-info" style="margin-bottom:10px;">插件将在选定网站根目录下生成随机文件名的订阅文件，以便您通过 HTTP 链接访问。</div>\
                                <div class="form-group">\
                                    <label>选择网站</label>\
                                    <select class="bt-input-text mr5" id="site-select" style="width:100%">'+options+'</select>\
                                </div>\
                                <div class="mt10 text-right"><button class="btn btn-success btn-sm" id="confirm-bind">确定绑定</button></div>\
                            </div>',
                            success: function(layero, index){
                                $('#confirm-bind').click(function(){
                                    var $sel = $('#site-select option:selected');
                                    var path = $sel.val();
                                    var name = $sel.data('name');
                                    bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=bind_sub_site', data: {path: path, site_name: name}}, function(r){
                                        layer.close(index);
                                        bt_tools.msg(r);
                                        _that.render(main_obj);
                                    });
                                });
                            }
                        });
                    }
                });
            });

            $('.unbind-site').click(function(){
                bt.confirm({title:'解绑确认', msg:'确定要解绑订阅网站吗？这将删除网站目录下的订阅文件，导致现有订阅链接失效。'}, function(){
                    bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=unbind_sub_site'}, function(res){
                        bt_tools.msg(res);
                        _that.render(main_obj);
                    });
                });
            });

            $('.copy-dash-sub').click(function(){
                var link = $(this).data('link');
                if(!link) { layer.msg('暂无可用节点', {icon: 2}); return; }
                
                layer.open({
                    type: 1,
                    title: '复制通用订阅内容',
                    area: ['500px', '300px'],
                    content: '<div class="pd15">\
                        <div class="alert alert-danger"><b>注意：</b>这是 Base64 编码的节点列表内容，<b>不是 URL 链接</b>！<br>请在客户端选择 <b>"从剪贴板导入"</b>，切勿填入订阅/URL输入框。</div>\
                        <textarea class="bt-input-text" style="width:100%;height:100px;" id="sub-content" readonly>'+link+'</textarea>\
                        <div class="mt10 text-right"><button class="btn btn-success btn-sm" id="do-copy-sub">复制内容</button></div>\
                    </div>',
                    success: function(layero, index){
                        $('#do-copy-sub').click(function(){
                            doge_utils.copyText(link);
                            layer.close(index);
                        });
                    }
                });
            });

            $('.get-clash-conf').click(function(){
                var loadT = layer.msg('正在生成配置...', {icon: 16, time: 0, shade: 0.3});
                bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=get_clash_config'}, function(res){
                    layer.close(loadT);
                    if(res.status) {
                        var yaml = res.msg.yaml;
                        var b64 = res.msg.base64;
                        
                        var content = '<div class="pd15">\
                            <div class="alert alert-danger"><b>注意：</b>这是配置文件的具体内容，<b>不是订阅链接</b>！<br>请在客户端使用 <b>"导入配置"</b> 功能，切勿填入 URL 订阅框。</div>\
                            <textarea class="bt-input-text" style="width:100%;height:200px;margin-bottom:10px;" id="clash-yaml" readonly>' + yaml + '</textarea>\
                            <div style="display:flex; gap:10px;">\
                                <button class="btn btn-success" style="flex:1;" id="copy-clash-yaml">复制 YAML 内容</button>\
                                <button class="btn btn-info" style="flex:1;" id="copy-clash-b64">复制 Base64 (修复导入报错)</button>\
                            </div>\
                        </div>';
                        
                        layer.open({
                            type: 1,
                            title: 'Clash Meta (Mihomo) 配置内容',
                            area: ['600px', '500px'],
                            shadeClose: true,
                            content: content,
                            success: function(){
                                $('#copy-clash-yaml').click(function(){
                                    doge_utils.copyText(yaml);
                                });
                                $('#copy-clash-b64').click(function(){
                                    doge_utils.copyText(b64);
                                });
                            }
                        });
                    } else {
                        layer.msg(res.msg, {icon: 2});
                    }
                });
            });
            
            $('.svc-action').click(function(){
                var type = $(this).data('type');
                var act = $(this).data('act');
                bt_tools.send({url: '/plugin?action=a&name=dogecloud&s=service_admin', data: {type: type, status: act}}, function(res){
                    bt_tools.msg(res);
                    _that.render(main_obj);
                });
            });
        });
    }
};