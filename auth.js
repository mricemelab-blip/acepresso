// ACEpresso Authentication System
// Generated: 2026-10-19 | 60 whitelisted students
// Salt: acepresso_3hfit_2026

(function() {
  'use strict';

  var VALID_HASHES = [
    '50dec4e6f9ef62b33ea9f9a51236f771b379b0515a11a8f667286646916f8c54',
    '63caf470c1fe9f763a84a91f082baf16c3e41400e94c2fcadd3d180d788dfc05',
    '38e136e76537f3d7af0d5af0873221b57d8f89a67721156e143ca0b4eed3bd25',
    'dce06c9e523a1e042591006242459ca40ee89dd4c94c14a73725a38b1aff04c6',
    '3563a294d9339213b1f575ec904de130ea3bc3705b0da9f462e27037b660f645',
    'ba170a2df448a40ff06ee4acd422eb58272e79e6e720b1cb4d0a62ffe27453ac',
    'd2d545f7db0600f37ad304acddc97c237c1e9a72250703896dff8389bd89406f',
    '40da251daf13e4f9bbb8febc15827c062189ab936d8323ebd9f3664d7c436444',
    '58d1020bab6a33cc202acd6c5d3a64095e1633f27e295b1319a29793c90ebe87',
    '72ab557674c114e90ea44b7a5cc460b7acfea4b8363bd1134afc23c82ff89a81',
    '426e423f25ad647c2698e3e53925774b393fe4221e16020d41e3bef4cffb307b',
    '029ccf8dbf14bd227c430a778523a45bf124a25ae918f927680eff89ef247627',
    '6b7294b48f4997a36d1bed1fba58cf7a73409b7c1fe5b3be690247631e4298e3',
    'fdc949a2913ed557f32281de159cdd2eb80506966ef2c4fbffc7b971dca91444',
    '386da3bc2b8895f1024ccc985493763786a2acead52f8a35ccd794e5cfb59006',
    '1cee0c370357b1b39b292dfb32d969ed68ab2586c60f11d8e0559226fc4eef2e',
    '9b51d3f25396ae4aa11b9588472a73055ac022f8545707a86b5a0e409dcc7baf',
    '02e1a8298c8ed960eb89e91ebed36625b053f5c5eb2ecc22a17a1ad193fe4aa4',
    '2f2cb4e654718998908b4239dcd3c1d547f73dac8e48881d7b84622d5112e959',
    '72ff3e80c7ea3ab2d95d2353a97f6be3e0d5f6b4e57fce34041650f740397a7a',
    '1a3d33ca3c94dace2b52bea459731820fda956ee96b390653aa5556af0885b23',
    '5b5265125080a3f0ac391ae8fb216873a813cf2cd4220a2954f3cefa34c71295',
    '52103b7dd458e803011fe25555e5e2754a6a4a11ac66c101ac25ebd40a0b5472',
    '8c4518ddcda802d31c726bb4036156cf9e757dd744c33ff79a17afcadd746b6f',
    'e39b4e6d1191553a99c7e8c64819cfb9d530e448f47a0e188cc99a15e2e41058',
    '4885da4a7d2e00e9f83b7ccb5401108a2b4b5991fd792461358851bf3fb25801',
    '642dfdf75ded14488ec9ef35df120d2a9da26e735e7318194cc7c90431e4f154',
    'afde7e405e0af48fd2a193da146b9c6680234eb173a348803ff44fd78eb89024',
    '2e09acb19194aa16cd94ed7713f80aa5aa9bc97496784493d5bbb588be18d503',
    'e3302f4ecb9bc7556df2f04663ca17f6106fe1898513459af9f63b98ec839bbf',
    'f341e7243e668419cf2f1ab79b0332ee20f80a96140f8f9884ce1696978d397c',
    'e5659a55f8083fafd183b73d7aff1f06860e762cd75b6d554a55a96696a2743e',
    'e127e28f798369fc12ef2fa07fb4ff79b973ac6bc1a811f7093a0647d1bfa443',
    'd944f573d8e5243b0e936ef87ec9c25efa7de7cc0332ed3ef8912950a50f6927',
    '117e86963419d368770faf792cb59fe4f3577497f5d99392312a63b33fabf32e',
    '18b551e6a126d8fce3e0a2b98fb1ad958111575e5db73f201489c4d022961118',
    '36d7e47091c9938d779734cd7c1cd8fb0ba94c1cc60185e2bec8c4d68dfd4f9c',
    'ffd68cae18307529e2d8f2811050246c41be8f4ee83744a3143167499614d2fd',
    'bcd61935a66d635488880fab5797693bc7db25a237cfb352880b22151ee4705a',
    'fc81516012a9ba6ed597d2278bd66fe05188e988aa114cc792ccfdb620799338',
    'b34d19421ed74e8065a8efe64845c0b621ffa4c703d1b95e4ec5173fbbf944db',
    'dace7b008ac2c25c4e7a036745d4bbe2bc87b0e74be67eb99adcdb5c3b9b518d',
    '8b036c7992d132cb7ca70937ff5860a5187c854d05b3fe27e7a58933a759ba3d',
    '78719822a48c4e4057fb5c3433bcb896d3aaa03dc061cac504b662c8711c4f6e',
    'ea8ea285a835a3993f0db0e940a27b8ef26dd152d01ac1b82d02cf57abde21f8',
    'befda9297c980dd64f7ae149a4c298e7f3b77f749e2b9de18bd51bd8c45e3689',
    '6424206885192ab79ff6195e9d9126248b0f38d7a3437227a3e3fd50f288924d',
    '91b6f9921c131854cb2b5b9ced7d20dee1e7d5a70d66b66f55a388905029782d',
    '93259d9c19bb042408c4b396d526d70419e06f9358a25507e7e43af6876c564c',
    '869fb325f33634b4bebbb357a62cf62d9dbc39f800488e6ab6b24787ea08f5f5',
    '495c81f31ce8eee546385415e6ad1a12b489826165732188a09ff2b8d0f50e5d',
    '347638d8544c689c8c198f33ec73d35ec0638d4ac8ce3c948cee8a3686117a2f',
    '8d5f6cd8b3f217205bb844e915ec6d439351c9cdb6e84827c24b4714cdeacd77',
    'ac93af4e3e14b4f581905729fd8f89b0e9a7d38c0c7281181e36a438be8f90f4',
    'a13d5a0d9693300e69cbc3bbdf7616d90b8fce6889222582262a2638e402b1da',
    '324d98599f7732adb5cf5c16cc89fcd8b48699b9e9fb8b354831f8ce4259890d',
    'c3830b04520cbd3624c4bcc6514344803f100c388dd8b19d711fb63f7bf73e5f',
    '4d3d4e90081f1ad382e3a4eecf893655e9412f7b3fe342f8af08dcb482e60060',
    'dd5e821c35f0488edf7013ef5257c25a0958d1403927d9f3d8d47cfd30f7d666',
    'd6983a034f86dbcebb60a11fdfba46cb446e69237200163f1e3cee003bcaa0d3'
  ];

  var SALT = 'acepresso_3hfit_2026';
  var TTL_DAYS = 30;
  var STORAGE_KEY = 'acepresso_auth';
  var STORAGE_TIME_KEY = 'acepresso_auth_time';
  var STORAGE_NAME_KEY = 'acepresso_name';

  async function sha256(message) {
    var msgBuffer = new TextEncoder().encode(message);
    var hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    var hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(function(b) { return b.toString(16).padStart(2, '0'); }).join('');
  }

  async function verifyCode(code, name) {
    var hash = await sha256(SALT + code);
    var isValid = VALID_HASHES.indexOf(hash) !== -1;
    if (isValid) {
      var now = Date.now();
      localStorage.setItem(STORAGE_KEY, hash);
      localStorage.setItem(STORAGE_TIME_KEY, now.toString());
      localStorage.setItem(STORAGE_NAME_KEY, name || '学员');
    }
    return isValid;
  }

  function isLoggedIn() {
    var hash = localStorage.getItem(STORAGE_KEY);
    var time = localStorage.getItem(STORAGE_TIME_KEY);
    if (!hash || !time) return false;
    var elapsed = Date.now() - parseInt(time);
    var expired = elapsed > TTL_DAYS * 24 * 60 * 60 * 1000;
    if (expired) {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(STORAGE_TIME_KEY);
      localStorage.removeItem(STORAGE_NAME_KEY);
      return false;
    }
    return VALID_HASHES.indexOf(hash) !== -1;
  }

  function getUserName() {
    return localStorage.getItem(STORAGE_NAME_KEY) || '学员';
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
    verifyCode: verifyCode,
    isLoggedIn: isLoggedIn,
    getUserName: getUserName,
    injectWatermark: injectWatermark,
    guard: guard
  };

})();
