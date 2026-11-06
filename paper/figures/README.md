# paper/figures README（由 analysis/fig_w72.py 生成，勿手改）

- 重出命令：`.venv/Scripts/python.exe analysis/fig_w72.py`（一条命令重出全部图与表）
- 生成环境：Python 3.13.14，matplotlib 3.11.2，pymupdf 2.1:
- 文件为稳定名（fig1_frontier / fig2_geometry / fig3_lmin），版本演进看本文件与 git 历史。
- 口径：残熵/H 取 w11spike_frontier.csv 的 C-B** 行（C031–C036，M1 臂；controls.csv 无 C-B** 行，
  已记 DEVIATION_LEDGER）；误拦取 w11spike_grid.csv（真实负载 holdout 68）；24 bit 为运行判据。

## 输入（sha256 前 16 位）
- analysis/w11spike_grid.csv: 6970afeb7e5974b9
- analysis/w11spike_frontier.csv: 4c8b5347e7ed9bf8
- analysis/w11geom_curve.csv: 856caff6b4c36cbb
- analysis/w11spike_controls.csv: e32cab7f6449b069

## 输出（sha256 前 16 位）
- paper\figures\fig1_frontier.pdf: a19cc55c737cdf8b
- paper\figures\fig1_frontier.svg: 2c2ba7ed9b43227c
- paper\figures\fig2_geometry.pdf: 9580369dd20f70c3
- paper\figures\fig2_geometry.svg: 876c920240d8cde1
- paper\figures\fig3_lmin.pdf: e1ad5ac3688c631b
- paper\figures\fig3_lmin.svg: 8309e4fc063756a9
- paper\tables\tab1a_main.tex: d4fc53d59a175dff
- paper\tables\tab1b_cost.tex: 7be2a8304b16257b
- paper\tables\tab2_counters.tex: 2f0febf5ecbff523
