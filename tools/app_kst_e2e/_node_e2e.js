// 在 Node 里真实执行 App 的 JS（提取 gimbal_compare.html 的主 <script>），
// 用归档真图的真实尺寸 + 标定用的真实孔位坐标走「点四个圆 → dx/dy → 双目换算」链路。
const fs = require('fs'), vm = require('vm'), path = require('path');
const DIR = 'C:\\Users\\QI\\gimbal-compare\\app\\src\\main\\assets';
const DATA = 'C:\\Users\\QI\\Desktop\\calib_zero_20261106';

// ---------- 1. 提取主脚本 ----------
const html = fs.readFileSync(path.join(DIR, 'gimbal_compare.html'), 'utf8');
const blocks = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
blocks.sort((a, b) => b.length - a.length);
const code = blocks[0];
console.log('主脚本 %d 行 / %d 字节', code.split('\n').length, code.length);

// ---------- 2. DOM 桩 ----------
const els = {};
function strip(h) { return String(h).replace(/<[^>]*>/g, ''); }
function ctxStub() {
  const t = { measureText: () => ({ width: 8 }) };
  return new Proxy(t, {
    get(o, k) { if (k in o) return o[k]; if (k === 'getImageData') return () => ({ data: new Uint8ClampedArray(4), width: 1, height: 1 }); if (k === 'createLinearGradient' || k === 'createPattern') return () => ({ addColorStop() {} }); return () => {}; },
    set(o, k, v) { o[k] = v; return true; }
  });
}
function El(id, tag) {
  const h = {}; let _html = '', _text = '';
  const e = {
    id, tagName: (tag || 'div').toUpperCase(), style: {}, dataset: {}, children: [], value: '', checked: false,
    width: 0, height: 0, clientWidth: 900, clientHeight: 600, scrollTop: 0, files: [], textContent: '',
    addEventListener(t, fn) { (h[t] = h[t] || []).push(fn); }, removeEventListener() {},
    dispatch(t, ev) { (h[t] || []).forEach(fn => fn(ev || {})); },
    appendChild(c) { e.children.push(c); return c }, removeChild(c) { return c }, remove() {},
    querySelector() { return El(id + '_q'); }, querySelectorAll() { return []; },
    closest() { return null; }, setAttribute() {}, getAttribute() { return null; }, focus() {}, blur() {}, click() {},
    getBoundingClientRect: () => ({ left: 0, top: 0, width: e.clientWidth, height: e.clientHeight, right: e.clientWidth, bottom: e.clientHeight }),
    getContext: () => ctxStub(), toDataURL: () => 'data:image/png;base64,',
    classList: { add() {}, remove() {}, toggle() {}, contains: () => false }
  };
  Object.defineProperty(e, 'innerHTML', { get: () => _html, set: v => { _html = String(v); _text = strip(v); e.textContent = _text; } });
  Object.defineProperty(e, 'textContent', { get: () => _text, set: v => { _text = String(v); } });
  els[id] = e; return e;
}
const $ = id => els[id] || El(id);
// JPEG/PNG 尺寸解析：喂真图的真实字节
function dims(buf) {
  if (buf[0] === 0x89 && buf[1] === 0x50) return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
  for (let i = 2; i + 9 < buf.length; i++) {
    if (buf[i] !== 0xFF) continue;
    const mk = buf[i + 1];
    if (mk >= 0xC0 && mk <= 0xCF && mk !== 0xC4 && mk !== 0xC8 && mk !== 0xCC)
      return { height: buf.readUInt16BE(i + 5), width: buf.readUInt16BE(i + 7) };
    const len = buf.readUInt16BE(i + 2); if (len < 2) break; i += 1 + len;
  }
  return { width: 0, height: 0 };
}
class FakeImage {
  constructor() { this._s = ''; this.width = 0; this.height = 0; this.onload = null; this.onerror = null; this.complete = false; this.naturalWidth = 0; this.naturalHeight = 0; }
  get src() { return this._s; }
  set src(v) {
    this._s = v; const self = this;
    setTimeout(() => {
      let buf = null;
      try { if (v.startsWith('data:')) buf = Buffer.from(v.slice(v.indexOf(',') + 1), 'base64'); } catch (e) { }
      if (buf) { const d = dims(buf); self.width = d.width; self.height = d.height; self.naturalWidth = d.width; self.naturalHeight = d.height; self.complete = true; }
      if (self.complete && self.onload) self.onload(); else if (self.onerror) self.onerror();
    }, 0);
  }
}
const store = {};
const sandbox = {
  console, setTimeout, clearTimeout, setInterval, clearInterval, Math, JSON, Date, Number, String, Array, Object,
  document: {
    getElementById: $, createElement: (t) => El('new_' + t + '_' + Math.random().toString(36).slice(2, 6), t),
    addEventListener() {}, removeEventListener() {}, body: El('body'), head: El('head'),
    documentElement: El('html'), querySelector: () => null, querySelectorAll: () => [],
    readyState: 'complete', createTextNode: (s) => ({ textContent: s }), hidden: false
  },
  Image: FakeImage, localStorage: {
    getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); },
    removeItem: k => { delete store[k]; }, clear: () => { for (const k in store) delete store[k]; }
  },
  ResizeObserver: class { observe() {} unobserve() {} disconnect() {} },
  MutationObserver: class { observe() {} disconnect() {} },
  IntersectionObserver: class { observe() {} disconnect() {} },
  WebSocket: class { constructor() { this.readyState = 0; } close() {} send() {} },
  fetch: () => Promise.reject(new Error('no-net')),
  requestAnimationFrame: cb => { setTimeout(() => cb(Date.now()), 0); return 1; },
  matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
  navigator: { clipboard: { writeText: () => Promise.resolve() }, userAgent: 'node' },
  alert() { }, confirm: () => false, prompt: () => null, devicePixelRatio: 1,
  __fire: (id, type, ev) => { const e = els[id]; if (!e) throw new Error('no element ' + id); e.dispatch(type, ev); },
  __el: id => els[id] || null
};
sandbox.window = sandbox; sandbox.globalThis = sandbox; sandbox.self = sandbox;
sandbox.G20 = { isApp: () => false, grabFrame: () => { }, saveConfig: () => false };

// ---------- 3. 追加取数出口（与 App 同一词法作用域） ----------
const epilogue = `
;globalThis.__T = {
  set src(v) { frameSrc = v }, get src() { return frameSrc },
  load(u) { loadCompareFrame(u) },
  click(u, v) { const r = cv.getBoundingClientRect();
    __fire('cv', 'pointerdown', { clientX: r.left + bx() + u * ds(), clientY: r.top + by() + v * ds(), preventDefault() { } }); },
  get n() { return marks.length },
  get center() { if (!marks.length) return null; return [marks.reduce((s, m) => s + m.cx, 0) / marks.length,
      marks.reduce((s, m) => s + m.cy, 0) / marks.length]; },
  shift(dx, dy) { marks.forEach(m => { m.cx += dx; m.cy += dy }); },
  get vals() { const t = id => { const e = __el(id); return e ? e.textContent : 'MISSING'; };
    return { dx: t('vgdx'), dy: t('vgdy'), sdx: t('vsdx'), sdy: t('vsdy'), sc: t('vscenter'), cam: t('curCam'), hint: t('hint') }; },
  get k() { return { ref: [REF_X, REF_Y, SCALE], stref: [ST_REF_X, ST_REF_Y, ST_SCALE], src: frameSrc, dims: [img.width, img.height] }; },
  calibrate() { calibrate(); }, resetRef() { resetRefPoint(); }, apply() { applyConfig(); },
  poke(k, x, y) { if (k === 'pod') { REF_X = x; REF_Y = y; } else { ST_REF_X = x; ST_REF_Y = y; } },
  selfTest() { return runSelfTest(); },
  get calibrated() { return { pod: calibrated, st: stCalibrated }; },
  forceCalib() { calibrated = true; }
};`;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(DIR, 'config.js'), 'utf8'), sandbox, { filename: 'config.js' });
console.log('config.js 载入:', JSON.stringify({ podRef: [sandbox.GIMBAL_CONFIG.gimbalRefX, sandbox.GIMBAL_CONFIG.gimbalRefY], podK: sandbox.GIMBAL_CONFIG.scale, stRef: [sandbox.GIMBAL_CONFIG.stereoRefX, sandbox.GIMBAL_CONFIG.stereoRefY], stK: sandbox.GIMBAL_CONFIG.stereoScale }));
vm.runInContext(code + epilogue, sandbox, { filename: 'gimbal_compare.main.js' });
// 截 MQTT 发布：函数声明挂在 global 上，可直接换掉，内部调用点会走新绑定
sandbox.__PUB = [];
sandbox.mqttPublish = (t, p) => { sandbox.__PUB.push([String(t), String(p)]); };

// ---------- 4. 真图 + 真孔位 ----------
const b64 = f => 'data:image/jpeg;base64,' + fs.readFileSync(path.join(DATA, f)).toString('base64');
const man = JSON.parse(fs.readFileSync(path.join(DATA, 'manifest.json'), 'utf8'));
const g4 = man['组'].find(x => x.stem.endsWith('_04'));
const g2 = man['组'].find(x => x.stem.endsWith('_02'));
const REF = man['标定结果']['零位中心_吊舱'], STREF = man['标定结果']['零位中心_双目'];
const KP = man['标定结果']['k_pod_mm_per_px'], KS = man['标定结果']['k_st_mm_per_px'];
const wait = ms => new Promise(r => setTimeout(r, ms));

function exp(c, ref, k) { return [(ref[0] - c[0]) * k, (ref[1] - c[1]) * k]; }
function mean(pts) { return [pts.reduce((s, p) => s + p[0], 0) / pts.length, pts.reduce((s, p) => s + p[1], 0) / pts.length]; }

(async () => {
  await wait(300);
  const rows = [];
  for (const [which, holes, ref, k, file, other] of [
    ['pod', g4.pod.detect.holes, REF, KP, 'pod_1718662503_04.jpg', ['stereo', STREF, KS]],
    ['stereo', g4.stereo.detect.holes, STREF, KS, '_st.jpg', ['pod', REF, KP]],
    ['pod', g2.pod.detect.holes, REF, KP, 'pod_1718662500_02.jpg', ['stereo', STREF, KS]],
    ['stereo', g2.stereo.detect.holes, STREF, KS, '_st02.jpg', ['pod', REF, KP]],
  ]) {
    sandbox.__T.src = which;
    sandbox.__T.load(b64(file));
    await wait(60);
    holes.forEach(p => sandbox.__T.click(p[0], p[1]));
    await wait(60);
    const c = mean(holes), e = exp(c, ref, k); // c=[x,y]
    const predicted = [STREF[0] - e[0] / KS, STREF[1] - e[1] / KS];
    rows.push({ which, file, nmarks: sandbox.__T.n, fitted: sandbox.__T.center.map(x => +x.toFixed(1)), k: sandbox.__T.k, app: sandbox.__T.vals, expDx: +e[0].toFixed(2), expDy: +e[1].toFixed(2), expCenter: predicted.map(x => +x.toFixed(1)) });
  }
  // 5) 合成大偏移：吊舱孔位整体 +40,-25 px -> 换算应给出对应 mm 与双目像素预测
  sandbox.__T.src = 'pod'; sandbox.__T.load(b64('pod_1718662503_04.jpg'));
  await wait(60);
  g4.pod.detect.holes.map(p => [p[0] + 40, p[1] - 25]).forEach(p => sandbox.__T.click(p[0], p[1]));
  await wait(60);
  const c5 = sandbox.__T.center, e5 = exp(c5, REF, KP);
  rows.push({ which: 'pod+合成偏移(+40,-25px)', fitted: c5.map(x => +x.toFixed(1)), app: sandbox.__T.vals,
    expDx: +e5[0].toFixed(2), expDy: +e5[1].toFixed(2),
    expCenter: [+(STREF[0] - e5[0] / KS).toFixed(1), +(STREF[1] - e5[1] / KS).toFixed(1)] });
  // 6) 校准按钮：应只覆盖「当前帧来源」那套常量，另一套不动；并检查写盘 key
  sandbox.__T.src = 'stereo'; sandbox.__T.load(b64('_st.jpg'));
  await wait(60);
  g4.stereo.detect.holes.forEach(p => sandbox.__T.click(p[0], p[1]));
  await wait(40);
  sandbox.__T.calibrate(); await wait(30);
  const calibOnStereo = { k: sandbox.__T.k, stMean: mean(g4.stereo.detect.holes).map(x => +x.toFixed(1)), pubAfter: sandbox.__PUB.slice() };
  // 6b) 吊舱帧点校准：应发 aruco/stop{cmd:calibrate}，且 calibrated 后每次重算自动发 gimbal/result{dx,dy}
  sandbox.__PUB.length = 0;
  sandbox.__T.src = 'pod'; sandbox.__T.load(b64('pod_1718662503_04.jpg'));
  await wait(60);
  g4.pod.detect.holes.forEach(p => sandbox.__T.click(p[0], p[1]));
  await wait(40);
  sandbox.__T.calibrate(); await wait(40);
  const calibOnPod = { k: sandbox.__T.k, calibrated: sandbox.__T.calibrated, pub: sandbox.__PUB.slice() };
  // 9) 自测项（含新加的双相机常量 / 100mm 换算）
  await sandbox.__T.selfTest(); await wait(200);
  const selfTest = (els['stOut'] ? els['stOut'].textContent : 'MISSING stOut');
  // 7) 重新 applyConfig：两套都应从盘上恢复（双目=刚校准值，吊舱=之前存的组4均值）
  sandbox.__T.poke('pod', 0, 0); sandbox.__T.poke('stereo', 0, 0);
  sandbox.__T.apply(); await wait(20);
  const restored = sandbox.__T.k;
  const persisted = Object.keys(store);
  // 8) 出厂复位：两套都回 config.js
  sandbox.__T.resetRef(); await wait(20);
  const afterReset = sandbox.__T.k;

  console.log(JSON.stringify(rows, null, 1));
  console.log('双目帧点校准 ->', JSON.stringify(calibOnStereo));
  console.log('吊舱帧点校准 ->', JSON.stringify(calibOnPod));
  console.log('自测输出 ->\n' + selfTest);
  console.log('写盘 key ->', JSON.stringify(persisted), JSON.stringify(store));
  console.log('重新 applyConfig ->', JSON.stringify(restored));
  console.log('复位后常量', JSON.stringify(afterReset));
  console.log('CFG 读到的', JSON.stringify({ g: sandbox.window.GIMBAL_CONFIG.gimbalRefX, s: sandbox.window.GIMBAL_CONFIG.stereoScale }));
  fs.writeFileSync(path.join(DATA, 'app_node_e2e.json'),
    JSON.stringify({ rows, calibOnStereo, persisted, store, restored, afterReset }, null, 1));
})().catch(e => { console.log('FAILED', e && e.stack || e); process.exit(1); });
