// 校验 App「校准」按钮行为：门槛 3 孔、双目/吊舱都只发 aruco/stop {"cmd":"calibrate"}、绝不改本地基准
const fs = require('fs'), vm = require('vm'), path = require('path');
const HTML = path.join(__dirname, '..', 'app', 'src', 'main', 'assets', 'gimbal_compare.html');
const src = fs.readFileSync(HTML, 'utf8');

// 抠出 calibrate 函数
const i0 = src.indexOf('function calibrate(){');
if (i0 < 0) { console.error('FAIL: 找不到 calibrate'); process.exit(1); }
let depth = 0, i1 = -1;
for (let i = src.indexOf('{', i0); i < src.length; i++) {
  if (src[i] === '{') depth++;
  else if (src[i] === '}') { depth--; if (depth === 0) { i1 = i + 1; break; } }
}
const body = src.slice(i0, i1);
console.log('抽取 calibrate 长度', body.length, '字节');

// 期望常量（config.js 与 html 必须一致）
const cfg = fs.readFileSync(path.join(__dirname, '..', 'app', 'src', 'main', 'assets', 'config.js'), 'utf8');
const gv = k => Number((cfg.match(new RegExp(k + '\\s*:\\s*([0-9.]+)')) || [])[1]);
console.log('config.js  stereoRef', gv('stereoRefX'), gv('stereoRefY'), 'scale', gv('stereoScale'));
const htmlConst = (src.match(/let ST_REF_X = ([0-9.]+), ST_REF_Y = ([0-9.]+), ST_SCALE = ([0-9.]+)/) || []).slice(1).map(Number);
console.log('html 常量     ', htmlConst.join(' '));

function run({ nHoles, stereo = true, manual = null, calibState = 0 }) {
  const sent = [], hint = { textContent: '' }, btn = { textContent: '🎯 校准', disabled: false };
  const el = id => id === 'hint' ? hint : (id === 'calibrate' ? btn : { textContent: '' });
  const ctx = {
    console,
    ST_REF_X: htmlConst[0], ST_REF_Y: htmlConst[1], ST_SCALE: htmlConst[2],
    REF_X: 642.8, REF_Y: 361.4, SCALE: 1.19, calibrated: false, stCalibrated: false,
    frameSrc: stereo ? 'stereo' : 'pod',
    calibState, manualPending: manual,
    inlierIdx: Array.from({ length: nHoles }, (_, i) => i),
    marks: Array.from({ length: nHoles }, (_, i) => ({ cx: 700 + i * 50, cy: 500 + i * 40, r: 76 })),
    img: { width: 1280, height: 1066 },
    window: { GIMBAL_CONFIG: { mqtt: { calibCmd: 'aruco/stop', manualResp: 'aruco/manual' } } },
    document: { getElementById: el },
    mqttPublish: (t, p) => sent.push([t, p]),
    updateCalibButton: st => { btn.textContent = 'state' + st; },
    lockUIFor: () => { ctx.__locked = true; },
    setStat: () => {},
    recompute: () => {},
    POD_MM: false,
  };
  ctx.window.document = ctx.document;
  vm.createContext(ctx);
  vm.runInContext(body + '\ncalibrate();', ctx);
  return { sent, hint: hint.textContent, ref: [ctx.ST_REF_X, ctx.ST_REF_Y], locked: !!ctx.__locked };
}

let bad = 0;
const chk = (name, ok, extra) => { console.log((ok ? '✅ ' : '❌ ') + name + (extra ? ' | ' + extra : '')); if (!ok) bad++; };

let r = run({ nHoles: 4 });
chk('4 孔双目→发 aruco/stop calibrate', r.sent.length === 1 && r.sent[0][0] === 'aruco/stop' && JSON.parse(r.sent[0][1]).cmd === 'calibrate', JSON.stringify(r.sent));
chk('4 孔双目→不写本地基准', r.ref[0] === htmlConst[0] && r.ref[1] === htmlConst[1], r.ref.join(','));
chk('4 孔双目→锁 UI', r.locked, r.hint.slice(0, 40));

r = run({ nHoles: 3 });
chk('3 孔双目→放行(门槛 3)', r.sent.length === 1, JSON.stringify(r.sent));
chk('3 孔双目→不写本地基准', r.ref[0] === htmlConst[0] && r.ref[1] === htmlConst[1]);

r = run({ nHoles: 3, stereo: false });
chk('3 孔吊舱→也发 aruco/stop', r.sent.length === 1 && r.sent[0][0] === 'aruco/stop', JSON.stringify(r.sent));

r = run({ nHoles: 2 });
chk('2 孔→不发命令+提示', r.sent.length === 0 && r.hint.includes('未标满 3'), r.hint);

r = run({ nHoles: 0 });
chk('0 孔→不发命令', r.sent.length === 0);

r = run({ nHoles: 4, manual: { image_id: 'X' } });
chk('人工补标模式→发 aruco/manual 不发 stop', r.sent.length === 1 && r.sent[0][0] === 'aruco/manual' && r.sent[0][1].includes('image_id'), JSON.stringify(r.sent));
chk('人工补标→坐标还原到 1536 口径', JSON.parse(r.sent[0][1]).points[0].x === Math.round(700 * 1536 / 1280 * 10) / 10, JSON.parse(r.sent[0][1]).points[0].x);

r = run({ nHoles: 4, calibState: 1 });
chk('校准中→重复点击拦截', r.sent.length === 0, r.hint);

chk('config.js 与 html 常量一致',
  gv('stereoRefX') === htmlConst[0] && gv('stereoRefY') === htmlConst[1] && gv('stereoScale') === htmlConst[2],
  [gv('stereoRefX'), gv('stereoRefY'), gv('stereoScale')].join(',') + ' vs ' + htmlConst.join(','));

console.log(bad ? ('\nFAIL ' + bad + ' 项') : '\nALL PASS');
process.exit(bad ? 1 : 0);
