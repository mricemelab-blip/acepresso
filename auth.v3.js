// ACEpresso Authentication - Whitelist Mode
// No invitation code needed. Name whitelist only.

(function() {
  'use strict';

  var WHITELIST = ["Jojo", "黄义睿", "Vicky", "龚艺莉", "林颖虹", "李普润", "蒋诗梦", "徐欢", "徐雯伶", "刘强", "赵赵赵", "李昕", "苏姝", "李平平", "孙玥", "李", "沈佳", "唐和佩", "刘将", "小水", "高骏成", "Rebirth", "金丰", "龚媛", "何宗颖", "高俊铭", "丁文鑫", "蔡晓东", "白叶", "任雅楠", "李瑞红", "兰清", "李秋婷", "陈稳举", "郝好", "瞿俊亮", "亚斯", "胡国弘", "李远哲", "李幸", "朱勤", "庄文康", "蓝麟", "李琦琦", "谢颖", "刘佳", "黄丽萍", "刘军利", "叶亚婷", "袁磊", "陈威志", "冯娜", "郭凯宁", "李玉", "郑庆", "龚帅", "吴轩乔", "谢雅云", "宋善哲", "谭圳桦"];

  var TTL_DAYS = 30;
  var STORAGE_KEY = 'acepresso_auth';
  var STORAGE_TIME_KEY = 'acepresso_auth_time';
  var STORAGE_NAME_KEY = 'acepresso_name';
  var STORAGE_WL_KEY = 'acepresso_auth_whitelist';

  function normalizeName(n) {
    return n.replace(/\s+/g, '').toLowerCase();
  }

  function isWhitelisted(name) {
    var norm = normalizeName(name);
    for (var i = 0; i < WHITELIST.length; i++) {
      if (normalizeName(WHITELIST[i]) === norm) return WHITELIST[i];
    }
    return null;
  }

  async function verifyName(name) {
    var matched = isWhitelisted(name);
    if (matched) {
      var now = Date.now();
      localStorage.setItem(STORAGE_KEY, 'whitelist_' + matched);
      localStorage.setItem(STORAGE_TIME_KEY, now.toString());
      localStorage.setItem(STORAGE_NAME_KEY, matched);
      localStorage.setItem(STORAGE_WL_KEY, matched);
    }
    return matched !== null;
  }

  function isLoggedIn() {
    var name = localStorage.getItem(STORAGE_NAME_KEY);
    var time = localStorage.getItem(STORAGE_TIME_KEY);
    var wlName = localStorage.getItem(STORAGE_WL_KEY);
    if (!name && !wlName) return false;
    var actualName = name || wlName;
    if (time) {
      var elapsed = Date.now() - parseInt(time);
      if (elapsed > TTL_DAYS * 24 * 60 * 60 * 1000) {
        logout();
        return false;
      }
    }
    return isWhitelisted(actualName) !== null;
  }

  function getUserName() {
    return localStorage.getItem(STORAGE_NAME_KEY) || localStorage.getItem(STORAGE_WL_KEY) || '学员';
  }

  function logout() {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(STORAGE_TIME_KEY);
    localStorage.removeItem(STORAGE_NAME_KEY);
    localStorage.removeItem(STORAGE_WL_KEY);
  }

  function injectWatermark() {
    if (!isLoggedIn()) return;
    var name = getUserName();
    var canvas = document.createElement('canvas');
    canvas.width = 300;
    canvas.height = 200;
    var ctx = canvas.getContext('2d');
    ctx.rotate(-22 * Math.PI / 180);
    ctx.font = '16px sans-serif';
    ctx.fillStyle = 'rgba(0,0,0,0.06)';
    ctx.fillText(name, 20, 80);
    ctx.fillText(name, 170, 80);
    ctx.fillText(name, 20, 160);
    ctx.fillText(name, 170, 160);
    var dataURL = canvas.toDataURL('image/png');
    var overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9999;opacity:1;overflow:hidden;';
    overlay.style.backgroundImage = 'url(' + dataURL + ')';
    overlay.style.backgroundRepeat = 'repeat';
    overlay.style.backgroundSize = '300px 200px';
    document.body.appendChild(overlay);
    var observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(m) {
        m.removedNodes.forEach(function(node) {
          if (node === overlay) document.body.appendChild(overlay);
        });
      });
    });
    observer.observe(document.body, { childList: true });
  }

  function guard() {
    if (!isLoggedIn()) {
      window.location.href = 'index.html';
    }
  }

  window.ACEpressoAuth = {
    WHITELIST: WHITELIST,
    verifyName: verifyName,
    isLoggedIn: isLoggedIn,
    getUserName: getUserName,
    logout: logout,
    injectWatermark: injectWatermark,
    guard: guard
  };

})();
