# W11.SPIKE 签核（SP1–SP5）

- 负责人：**lipei**（对话授权 `W11.SPIKE` 代记，2026-11-04）
- 依据：`reports/audit/w0.3_ruling.md`（五条裁定 ＋ §7 三个缺口）、`reports/audit/w0.3_spike_acceptance.md`（A1–A9 9/9）、`reports/spike/w11_spike_fix_receipt.md`（五项 FIX 全绿）
- 前置：`FREEZE_W11SPIKE.sha256` 覆盖 234 行／110 反制／102 go 池；**本文件不在三件冻结物之内**，签后 freeze 仍有效（这是把签名与 `prereg` 分开的理由：`run_bootstrap.py` 会整块重建 `prereg`，写进去会被抹掉）

```text
SP1 批准（零模型调用；跑 234 行 ＋ 110 个反制候选）
SP2 批准新增 L3／DEST；dest=cell 单列、不进 go（与 R2-8／STATE 行 81 的威胁模型冲突）；
    dest=chan 可进 go，但报告须写明"两侧几乎不判别"
SP3 批准 C-C 拆 covered（硬条件）／unseen（报告项）
SP4 待网格结果再定（若 go，是否另开正式预注册窗）
SP5 批准 no-go 只回写 Thm／Prop4，不进主表
```

## 附加条件（本次签核一并生效，进 `prereg` 与 `D-023`）

1. **go 判定加 `go_secondary`**：除 §8 四条外，候选行须同时满足 **拦截后残熵 ≥ 24 bit** 且 **H ≤ 0.5**；否则只作 frontier，不作 go。理由：`intercepted = got < truth_len` 会把"少一个字节"记成拦住，`θ′≥0.9` 的行否则会给出假 go（本数据秘密值全为 hex，4 bit/字符）。
2. **先探针、后全量**：先跑 `C001`–`C006`（S1/D1/L1 六档 θ′，其中 `C001` 已知 = 38/68）与 **C-B 单点**（部署 θ=0.55，末片切 1 B 续写），再决定 234 行报告的规模。判据：`θ′=1.0` 的误拦 >30% ⇒ ① 算术关闭；C-B 把残熵打到 0 ⇒ `allow` 行的高 θ′ 全部只作 frontier。
3. **报告列**：每行须带 `go_eligible`、`ambiguous(unique／union)`、`H`、`残熵(bit)`、`all／matchable` 双分母；`G-G` 的 18 对等价行须标注并断言读数全等。
4. **若 go 仅来自 `unmatched=deny` 行**：标注 `GO(closed-world, 构造依赖)`，并在 Limitations 写明"良性零误伤依赖『良性写＝库字段原文回写』"这一构造前提。

---

签署：lipei（对话授权 `W11.SPIKE` 代记，2026-11-04）　　日期：2026-11-04
