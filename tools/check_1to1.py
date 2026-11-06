# 零位 5 组：两条独立路（吊舱 / 双目）各算 dx,dy，看 mm 是否 1:1 对齐
import io, json, os
D = r"C:\Users\QI\Desktop\calib_zero_20261106"
m = json.load(io.open(os.path.join(D, "manifest.json"), encoding="utf-8"))
c = m["标定结果"]
RP, RS = c["零位中心_吊舱"], c["零位中心_双目"]
KP, KS = c["k_pod_mm_per_px"], c["k_st_mm_per_px"]
print("REF pod", RP, " stereo", RS, "| k", KP, KS)
n = 0
dxd, dyd = [], []
for it in m["组"]:
    pd, sd = it["pod"]["detect"], it["stereo"]["detect"]
    if not (pd["ok"] and sd["ok"]):
        continue
    pc, sc = pd["center"], sd["center"]
    dxp, dyp = (RP[0] - pc[0]) * KP, (RP[1] - pc[1]) * KP
    dxs, dys = (RS[0] - sc[0]) * KS, (RS[1] - sc[1]) * KS
    dxd.append(dxs - dxp)
    dyd.append(dys - dyp)
    n += 1
    print("%s  pod %+6.2f/%+6.2f   stereo %+6.2f/%+6.2f   差 %+5.2f/%+5.2f mm | 预测双目中心(%+6.1f,%+6.1f) 实测(%6.1f,%6.1f)" % (
        it["stem"][-2:], dxp, dyp, dxs, dys, dxs - dxp, dys - dyp,
        RS[0] - dxp / KS, RS[1] - dyp / KS, sc[0], sc[1]))
mu = lambda a: sum(a) / len(a)
sd = lambda a: (sum((x - mu(a)) ** 2 for x in a) / (len(a) - 1)) ** 0.5
print("\n组数 %d | 两路差 dx %+0.2f±%0.2f mm  dy %+0.2f±%0.2f mm | 最差 %.2fmm" % (
    n, mu(dxd), sd(dxd), mu(dyd), sd(dyd), max(abs(x) for x in dxd + dyd)))
print("中心预测残差 px: 见上两列对比（实测 vs 预测）")
