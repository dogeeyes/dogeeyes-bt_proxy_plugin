// dogecloud/static/js/dogecloud.js
var dogecloud = {
    currentType: 'dashboard',
    
    init: function () {
      var _that = this;
      $(".bt-w-menu p").click(function(){
        $(this).addClass("bgw").siblings().removeClass("bgw");
        _that.currentType = $(this).data('type');
        _that.render_main();
      });
      _that.render_main();
    },

    render_main: function () {
      var _that = this;
      
      // 如果是控制台，直接渲染全屏内容，不显示子Tab
      if (_that.currentType == 'dashboard') {
          doge_dashboard.render(_that);
          return;
      }

      $('#webEdit-con').html('<div class="tab-body">\
          <div class="tab-nav ml0 mb15">\
            <span class="on">服务状态</span>\
            <span>参数配置</span>\
            <span>配置文件</span>\
            <span>运行日志</span>\
          </div>\
          <div class="tab-con" style="padding: 0;">\
            <div class="tab-block on"></div>\
            <div class="tab-block"></div>\
            <div class="tab-block"></div>\
            <div class="tab-block"></div>\
          </div>\
        </div>');
      
      $('#webEdit-con .tab-nav span').click(function () {
        var index = $(this).index();
        $(this).addClass('on').siblings().removeClass('on');
        $('#webEdit-con .tab-con .tab-block').eq(index).addClass('on').siblings().removeClass('on');
        
        switch (index) {
          case 0: doge_service.render_status(_that.currentType); break;
          case 1: doge_service.render_form(_that.currentType); break;
          case 2: doge_service.render_file(_that.currentType); break;
          case 3: doge_service.render_logs(_that.currentType); break;
        }
      });
      doge_service.render_status(_that.currentType);
    }
};
dogecloud.init();