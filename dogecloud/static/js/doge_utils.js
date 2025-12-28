// dogecloud/static/js/doge_utils.js
var doge_utils = {
    // 复制文本到剪贴板
    copyText: function(text) {
        var textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand("copy");
            layer.msg('复制成功', {icon: 1});
        } catch (e) {
            layer.msg('复制失败，请手动复制', {icon: 2});
        }
        document.body.removeChild(textarea);
    },

    // 安全获取值
    safeValue: function(val, items, defaultVal) {
        if (!val || val === 'undefined') return defaultVal;
        for (var i = 0; i < items.length; i++) {
            if (items[i].value === val) return val;
        }
        return defaultVal;
    }
};