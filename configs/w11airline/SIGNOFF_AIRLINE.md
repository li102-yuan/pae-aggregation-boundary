# W11.2 签核（SP1–SP5）— airline 预注册

- 负责人：**lipei**
- 代记：`W0.5`（**本会话对话授权**，授权原话："我授权你帮我签了"，2026-11-05 09:57）
- 日期：2026-11-05
- 依据：`configs/w11airline/PREREG_AIRLINE.json`（sha256 `5540158c61b51e5c7f7c2ffb4a49c503c8e2789569c9a7460a5b97566a0c8b28`）、`FREEZE_AIRLINE.sha256`（四件 OK）、`D-024` §二、`D-025`、`D-026`
- **本文件不在冻结物之内**：`FREEZE_AIRLINE.sha256` 只覆盖 `PREREG_AIRLINE.json` ＋ `data/{airline_tasks.json, airline_db.json, LICENSE}`；签核不改变任何 sha256。
  ⇒ 预注册内 `signoff.status = "PENDING"` 是**冻结时的快照**，生效状态以本文件为准（处理方式同 `configs/w11spike/SIGNOFF.md`）。
- **入口约定**：`W11.2` 的 `check_signoff()` 必须显式传 `path=configs/w11airline/SIGNOFF_AIRLINE.md`（默认值指向 `configs/w11spike/SIGNOFF.md`，不传会误判）。

```text
SP1 批准（预注册 40 行判定子集／判定池 32／零模型调用；sha256 5540158c… 冻结有效）
SP2 批准 L≥12 硬约束与逐 L 报（L=12、θ′=0.55 时残熵恰 24 bit、H=0.500 卡线；L=11→20 bit 直接不过 ⑤）
SP3 批准"无 holdout"，并接受 second-load, no holdout, underpowered, descriptive only 的全套标注
SP4 批准分支 A／B／C 的判定条件与"中间区间交签核"的处置；但按 D-026：airline 的 branch_verdict 记
    UNDECIDABLE (power)，不判 PASS／FAIL、不作 GO 证据、不进 C1 的跨负载论证
SP5 批准执行范围＝D-026 §二：只跑 6 行（θ′∈{0.55,0.8,1.0} × {M2+deny, M2-short+deny}，S1/D1/L3）、
    只报 F7、F1 明写"不可估"；40 行子集保留备用，但不得据其判 branch
```

## 签核时逐条断言（实测，2026-11-05）

| # | 断言 | 实测 | 结论 |
|---|---|---|---|
| A1 | `set(判定池) − set(反制池) == ∅` | 判定池 32 行（B16＋C16）＝反制池 32 行，差集空 | **PASS** |
| A2 | 冻结有效且早于第一个候选 | `sha256sum -c FREEZE_AIRLINE.sha256` **4/4 OK**；尚无任何候选运行（无 `runs/w11airline-*`） | **PASS** |
| A3 | `configs/sanity/` 零改动 | `git status --porcelain configs/sanity` 空 | **PASS** |
| A4 | 披露项已知悉 | n=15 主分母（26 仅敏感性）；`F1` 13 对／2 个任务 cluster ⇒ 不可估；无 holdout；⑤ 只在偶数 `L≤20` 且 θ′=0.55 可满足；L≥21 与奇数 L 全 θ′ 不可满足 | **已签收** |

## 附加条件（随签核生效，`W11.2` 回执须逐条回应）

1. **不得翻案**：6 行结果只作描述性附表；`branch_verdict` 恒为 `UNDECIDABLE (power)`（`D-026` §一），**不得**因某行"看起来过了五条"改判 `GO`。
2. **三读数并列**：误拦（Wilson，n=15）／`partial-leakage fraction`／**标称剩余不确定性（`C-B**` 口径）**；只报 `structural interception rate` 视为不完整。
3. **两口径**：`unique`／`union` 都报，逐行给 ambiguous 计数。
4. **不得与 retail 并列排名**，不得写"复现 55.9%"；措辞上限按 `D-025` §三（禁用「防御有效」「可部署」「族级不可能（无条件时）」）。
5. **预注册不改**：任何为跑通而需要的口径变更，一律记 `DEVIATION_LEDGER` 并在回执 §5 披露，不改 `PREREG_AIRLINE.json`。

---

签署：lipei（对话授权 `W0.5` 代记）　　日期：2026-11-05
