# 把零位同帧标定写进 App：吊舱/双目双常量 + 1:1 mm 换算（幂等，旧串必须唯一命中）
import io, os

P = r"C:\Users\QI\gimbal-compare\app\src\main\assets\gimbal_compare.html"
s = io.open(P, encoding="utf-8").read()
E = []

# E1 设置页：改掉过期的 0.680，加双目参考点与换算依据说明
E.append(('''      <div class="tr"><span style="color:var(--muted)">双目 scale：<b id="stereoScaleVal">0.680</b> mm/px（= z/fx，按 z≈736mm、fx≈1081.76 计算，随深度变）</span></div>
      <div class="tr"><span id="setRef">—</span><button class="bt" id="setResetRef">复位参考点</button></div>''',
'''      <div class="tr"><span style="color:var(--muted)">双目 scale：<b id="stereoScaleVal">0.830</b> mm/px（1536×1280；零位同帧标定 2026-11-06：深度图 900.7mm÷fx1081.76=0.8326 与板尺互验 0.8235，差 1.1%。旧 0.680 作废）</span></div>
      <div class="tr"><span id="setRef">—</span><button class="bt" id="setResetRef">复位参考点</button></div>
      <div class="tr"><span id="stRef">—</span></div>
      <div class="tr" style="font-size:11px;color:var(--muted);line-height:1.6">换算依据：吊舱与双目在零位同帧实测，<b>毫米层面 1:1 相等</b>（归零后双目 0.0±0.6mm、吊舱 0.0±1.9mm）⇒ 吊舱的 dx/dy 就是双目的 dx/dy。双目 scale 只用来反推「板心应出现在双目画面哪个像素」便于比对。两套常量各按各的帧分辨率标定，<b>不可共用</b>；点「校准」在现场零位重采会覆盖当前帧来源那套的默认值。</div>'''))

# E2 面板：加双目换算显示
E.append(('''      <div class="cell"><div class="lbl">dx</div><div class="val" id="vgdx">—<small>mm</small></div></div>
      <div class="cell"><div class="lbl">dy</div><div class="val" id="vgdy">—<small>mm</small></div></div>
    </div>''',
'''      <div class="cell"><div class="lbl">dx</div><div class="val" id="vgdx">—<small>mm</small></div></div>
      <div class="cell"><div class="lbl">dy</div><div class="val" id="vgdy">—<small>mm</small></div></div>
    </div>
    <div style="font-size:11px;color:var(--muted);margin-top:4px" id="curCam">当前帧：吊舱 1280×720</div>
    <div class="cmp" style="margin-top:6px">
      <div class="cell"><div class="lbl">双目 dx</div><div class="val" id="vsdx">—<small>mm</small></div></div>
      <div class="cell"><div class="lbl">双目 dy</div><div class="val" id="vsdy">—<small>mm</small></div></div>
    </div>
    <div style="font-size:11px;color:var(--muted);margin-top:4px">双目板心预测 <b id="vscenter">—</b>（mm 与吊舱 1:1 相等；此像素按双目常量反算，供到双目画面里核对）</div>'''))

# E3 常量：两套独立基准（吊舱 1280×720 / 双目 1536×1280）
E.append(('''let REF_X = 653, REF_Y = 358, SCALE = 1.19, calibrated = false, calibState = 0;''',
'''// 零位同帧标定 2026-11-06（板上连抓 8 组、5 组两路全检出，均值±SD）
// 吊舱与双目各一套常量，基准点/scale 都按各自帧分辨率标定，绝不能共用
let REF_X = 642.8, REF_Y = 361.4, SCALE = 1.19, calibrated = false, calibState = 0;        // 吊舱 1280×720  SD(0.5,1.6)px
let ST_REF_X = 784.4, ST_REF_Y = 559.1, ST_SCALE = 0.830, stCalibrated = false;            // 双目 1536×1280 SD(0.7,0.5)px
let frameSrc = 'pod';   // 当前标注帧来源：'pod' 吊舱 / 'stereo' 双目 -> 决定用哪套常量'''))

# E4 计算：按来源选常量 + 双目换算
E.append(('''  if(marks.length<4){$('vgdx').innerHTML='—<small>mm</small>';$('vgdy').innerHTML='—<small>mm</small>';
    inlierIdx=[];lastDx=lastDy=null;draw();return}''',
'''  if(marks.length<4){$('vgdx').innerHTML='—<small>mm</small>';$('vgdy').innerHTML='—<small>mm</small>';
    $('vsdx').innerHTML='—<small>mm</small>';$('vsdy').innerHTML='—<small>mm</small>';$('vscenter').textContent='—';
    inlierIdx=[];lastDx=lastDy=null;draw();return}'''))
E.append(('''  const dx=(REF_X-r.cx)*SCALE, dy=(REF_Y-r.cy)*SCALE;   // 简化：参考点 + 比例
  lastDx=dx; lastDy=dy;
  $('vgdx').innerHTML=fmt(dx,0)+'<small>mm</small>';$('vgdy').innerHTML=fmt(dy,0)+'<small>mm</small>';''',
'''  // 按当前帧来源选常量；毫米层面两路 1:1，所以双目的 dx/dy 等于吊舱的 dx/dy
  const RX = frameSrc==='stereo'?ST_REF_X:REF_X, RY = frameSrc==='stereo'?ST_REF_Y:REF_Y,
        SC = frameSrc==='stereo'?ST_SCALE:SCALE;
  const dx=(RX-r.cx)*SC, dy=(RY-r.cy)*SC;   // 简化：参考点 + 比例
  lastDx=dx; lastDy=dy;
  $('vgdx').innerHTML=fmt(dx,0)+'<small>mm</small>';$('vgdy').innerHTML=fmt(dy,0)+'<small>mm</small>';
  $('vsdx').innerHTML=fmt(dx,1)+'<small>mm</small>';$('vsdy').innerHTML=fmt(dy,1)+'<small>mm</small>';
  $('vscenter').textContent='('+(ST_REF_X-dx/ST_SCALE).toFixed(1)+', '+(ST_REF_Y-dy/ST_SCALE).toFixed(1)+') px';'''))

# E5 帧来源标记 + 分辨率自检
E.append(("""function fetchFrame(){
  // App 内：原生 libVLC 抓 RTSP 帧""",
"""function fetchFrame(){
  frameSrc='pod';
  // App 内：原生 libVLC 抓 RTSP 帧"""))
E.append(('''        const url = img.startsWith('data:') ? img : 'data:image/jpeg;base64,' + img;
        loadCompareFrame(url);''',
'''        const url = img.startsWith('data:') ? img : 'data:image/jpeg;base64,' + img;
        frameSrc = 'stereo';
        loadCompareFrame(url);'''))

# E6 onload：显示当前相机 + 帧尺寸与常量口径不符时告警
E.append(("""img.onload=()=>{spinner(false);off.width=img.width;off.height=img.height;octx.drawImage(img,0,0);marks=[];selected=-1;inlierIdx=[];fit();setStat('已标 0/4 孔','ok');document.getElementById('hint').textContent='已取帧，点「检测圆」或手动点孔标注';recompute()};""",
"""img.onload=()=>{spinner(false);off.width=img.width;off.height=img.height;octx.drawImage(img,0,0);marks=[];selected=-1;inlierIdx=[];fit();setStat('已标 0/4 孔','ok');
  const nm=frameSrc==='stereo'?'双目':'吊舱', want=frameSrc==='stereo'?[1536,1280]:[1280,720];
  const cc=$('curCam'); if(cc) cc.textContent='当前帧：'+nm+' 标定口径 '+want[0]+'×'+want[1]+'，实际 '+img.width+'×'+img.height;
  let h='已取帧（'+nm+'），点「检测圆」或手动点孔标注；dx/dy 用'+nm+'那套常量，两路 mm 1:1';
  if(img.width!==want[0]||img.height!==want[1]) h+=' ⚠️ 帧尺寸与常量口径不符，scale/参考点需按 '+img.width+'×'+img.height+' 重标';
  document.getElementById('hint').textContent=h;
  recompute()};"""))

# E7 校准：只覆盖当前帧来源那套常量，分开存 localStorage
E.append(("""  REF_X = cx; REF_Y = cy;
  calibrated = true;
  try{ localStorage.setItem('gimbal_ref', JSON.stringify({x:cx, y:cy})); }catch(e){}""",
"""  // 校准写的是「当前帧来源」那套常量（吊舱帧→吊舱基准，双目帧→双目基准），分开存
  if(frameSrc==='stereo'){ ST_REF_X=cx; ST_REF_Y=cy; stCalibrated=true;
    try{ localStorage.setItem('stereo_ref', JSON.stringify({x:cx, y:cy})); }catch(e){} }
  else { REF_X=cx; REF_Y=cy; calibrated=true;
    try{ localStorage.setItem('gimbal_ref', JSON.stringify({x:cx, y:cy})); }catch(e){} }"""))

# E8 applyConfig：双目常量可被 config.js / /sdcard/gimbal_config.json 覆盖，恢复两套校准值
E.append(("""  if(CFG.scale!=null)SCALE=CFG.scale;
  // 恢复已保存的校准参考点
  try{
    const s=localStorage.getItem('gimbal_ref');
    if(s){const o=JSON.parse(s);if(o.x!=null&&o.y!=null){REF_X=o.x;REF_Y=o.y;calibrated=true;}}
  }catch(e){}""",
"""  if(CFG.scale!=null)SCALE=CFG.scale;
  if(CFG.stereoRefX!=null)ST_REF_X=CFG.stereoRefX;
  if(CFG.stereoRefY!=null)ST_REF_Y=CFG.stereoRefY;
  if(CFG.stereoScale!=null)ST_SCALE=CFG.stereoScale;
  // 恢复已保存的校准参考点（吊舱 / 双目 分开）
  try{
    const s=localStorage.getItem('gimbal_ref');
    if(s){const o=JSON.parse(s);if(o.x!=null&&o.y!=null){REF_X=o.x;REF_Y=o.y;calibrated=true;}}
    const t=localStorage.getItem('stereo_ref');
    if(t){const o=JSON.parse(t);if(o.x!=null&&o.y!=null){ST_REF_X=o.x;ST_REF_Y=o.y;stCalibrated=true;}}
  }catch(e){}"""))

# E9 设置页文本：两套常量各自显示
E.append(("""  if(ref) ref.textContent='参考点 X='+Number(REF_X).toFixed(1)+'  Y='+Number(REF_Y).toFixed(1)+(calibrated?'（已校准）':'（默认）');
  try{ refreshLiveConn(); }catch(e){}""",
"""  if(ref) ref.textContent='吊舱参考点 ('+Number(REF_X).toFixed(1)+', '+Number(REF_Y).toFixed(1)+')'+(calibrated?'（已校准）':'（默认）')+' · scale '+Number(SCALE).toFixed(3)+' mm/px';
  const sr=document.getElementById('stRef');
  if(sr) sr.textContent='双目参考点 ('+Number(ST_REF_X).toFixed(1)+', '+Number(ST_REF_Y).toFixed(1)+')'+(stCalibrated?'（已校准）':'（默认）')+' · scale '+Number(ST_SCALE).toFixed(3)+' mm/px';
  const ps=document.getElementById('podScaleVal'); if(ps) ps.textContent=Number(SCALE).toFixed(3);
  const sv=document.getElementById('stereoScaleVal'); if(sv) sv.textContent=Number(ST_SCALE).toFixed(3);
  try{ refreshLiveConn(); }catch(e){}"""))

# E10 复位参考点：两套一起回到 config.js 默认
E.append(("""function resetRefPoint(){
  try{ localStorage.removeItem('gimbal_ref'); }catch(e){}
  calibrated=false;
  REF_X=(window.GIMBAL_CONFIG||{}).gimbalRefX||REF_X;
  REF_Y=(window.GIMBAL_CONFIG||{}).gimbalRefY||REF_Y;
  recompute();
  const ref=document.getElementById('setRef');
  if(ref) ref.textContent='参考点 X='+Number(REF_X).toFixed(1)+'  Y='+Number(REF_Y).toFixed(1)+'（默认）';
}""",
"""function resetRefPoint(){
  try{ localStorage.removeItem('gimbal_ref'); localStorage.removeItem('stereo_ref'); }catch(e){}
  calibrated=false; stCalibrated=false;
  const CFG=(window.GIMBAL_CONFIG||{});
  if(CFG.gimbalRefX!=null)REF_X=CFG.gimbalRefX;
  if(CFG.gimbalRefY!=null)REF_Y=CFG.gimbalRefY;
  if(CFG.stereoRefX!=null)ST_REF_X=CFG.stereoRefX;
  if(CFG.stereoRefY!=null)ST_REF_Y=CFG.stereoRefY;
  recompute(); openSettings();
}"""))

for i, (old, new) in enumerate(E):
    n = s.count(old)
    assert n == 1, "E%d 命中 %d 次（必须恰好 1）" % (i + 1, n)
    s = s.replace(old, new)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("gimbal_compare.html 10 处改动完成")

# E11 config.js：现场可调的两套常量
Q = r"C:\Users\QI\gimbal-compare\app\src\main\assets\config.js"
c = io.open(Q, encoding="utf-8").read()
old = """  // 简化算法：参考点 + 比例（不用 H 矩阵）
  // 参考点 = 吊舱相机向下对正时，画面里四圆孔中心（实测 653,358；帧中心是 640,360，差 +13/-2 px）
  gimbalRefX: 653,   // 吊舱参考中心 X
  gimbalRefY: 358,   // 吊舱参考中心 Y
  // scale 实测标定（720p 帧）：宽 250mm/209px=1.1962，长 440mm/370px=1.1892，两向差 0.58% -> 取 1.19
  // 视野覆盖 152.5cm x 85.8cm；平台走 100mm 图上应移 83.9px
  scale: 1.19,       // mm/px（现场标定：Z / f_吊舱）"""
new = """  // ===== 简化算法：参考点 + 比例（不用 H 矩阵）。吊舱 / 双目 各一套，绝不能共用 =====
  // 零位同帧标定 2026-11-06：板上连抓 8 组（同一时刻吊舱 RTSP + 双目 RGB-D），
  // 5 组两路全检出；把两组均值当参考点重算各组 dx/dy -> 双目 0.0±0.6mm、吊舱 0.0±1.9mm，
  // 证明两路毫米层面 1:1 相等，所以吊舱的 dx/dy 就是双目的 dx/dy（无需乘系数）。

  // 吊舱（RTSP 1280×720）：零位四孔中心均值，SD (0.5, 1.6)px
  // 旧值 653/358 作废（那是按板孔位反推的，不是零位实测）
  gimbalRefX: 642.8,
  gimbalRefY: 361.4,
  // scale 用板子内间距量出（440×250 是孔的【内间距/边到边】，不是中心距；孔径约124mm
  // ⇒ 中心距 564×373mm）：横向 440/370=1.1892、纵向 250/209=1.1962，两向差 0.58% -> 取 1.19
  scale: 1.19,       // mm/px（吊舱）；平台走 100mm 图上应移 84.0px

  // 双目（1536×1280）：零位四孔中心均值，SD (0.7, 0.5)px
  stereoRefX: 784.4,
  stereoRefY: 559.1,
  // k_st 两条独立路径互验：深度图孔位中位 900.7±1.0mm ÷ fx 1081.76 = 0.8326；
  // 同帧板尺比（吊舱/双目像素比 1.4383）⇒ 1.19/1.4383 = 0.8235；两法差 1.1% -> 取 0.830
  // 旧 0.680/0.68536 作废（那版把 440mm 当中心距、642px 口径对不上任何量法）
  stereoScale: 0.830, // mm/px（双目，等效 z≈900.7mm）；平台走 100mm 图上应移 120.6px"""
assert c.count(old) == 1
c = c.replace(old, new)
io.open(Q, "w", encoding="utf-8", newline="\n").write(c)
print("config.js 常量块更新")
