# Mihomo AdBlock Rules (每日自动合并与优化)

[![Build and Release AdBlock Rules](https://github.com/USERNAME/REPO/actions/workflows/build.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/build.yml)
[![Release](https://img.shields.io/github/v/release/USERNAME/REPO?color=blue&label=Release)](https://github.com/USERNAME/REPO/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

专为 **Mihomo (Clash.Meta)** 打造的高性能广告拦截与追踪防御规则集。本项目参照 [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat) 自动化工程架构，利用 GitHub Actions **每日定时拉取上游权威规则库，经倒序字典树（Trie）智能剪除冗余子域后编译输出**。

---

## 规则分类与定位

| 规则名称 | 定位场景 | 涵盖上游数据源 | 规则体量 (去冗余后) | 格式支持 |
| :--- | :--- | :--- | :--- | :--- |
| **`reject-server`**<br>(全量极致防御) | **软路由 / 网关 / VPS 服务器**<br>硬件算力充裕，追求极致拦截率与全方位防追踪。 | • **Loyalsoldier**: `reject.txt`<br>• **Sukka**: `reject.txt` (Base)<br>• **Sukka**: `reject_extra.txt` (Extra) | **~233,000 条** | `.mrs` / `.yaml` / `.list` / `.txt` |
| **`reject-client`**<br>(极轻特化防御) | **手机 / 平板 / 移动轻薄本**<br>兼顾极低内存占用与高频国内移动 App 开屏、SDK 广告拦截。 | • **MetaCubeX**: `category-ads-all`<br>• **Sukka**: `reject.txt` (Non-IP)<br>• **Sukka**: `reject-no-drop.txt`<br>• **217heidai**: `adblockmihomolite`<br>• **秋风**: `AWAvenue-Ads-Rule` | **~9,000 条** | `.mrs` / `.yaml` / `.list` / `.txt` |

---

## 核心优化机制

1. **子域名冗余消除 (Trie Pruning)**：
   若规则库已包含祖先泛域名 `+.example.com`，则所有形如 `+.sub.example.com`、`ad.example.com` 的重复子域均会被自动剪枝剔除。去除无意义规则，使体积压缩 15%~25%，显著加快客户端启动建树速度并节省 RAM。
2. **多格式原生编译**：
   除标准的 YAML 与文本格式外，每日自动调用原生内核编译为 Mihomo **`.mrs` 高性能二进制规则集**，规则体积缩小近 70%，实现毫秒级加载与单次字典树查询。

---

## 订阅链接速查

> [!TIP]
> 请将链接中的 `USERNAME/REPO` 替换为你自己的 GitHub 用户名及仓库名。推荐优先使用 jsDelivr CDN 加速。

### 1. 服务器版 (`reject-server`)
* **MRS 二进制 (强烈推荐，速度与内存最优)**:
  * jsDelivr: `https://cdn.jsdelivr.net/gh/USERNAME/REPO@release/reject-server.mrs`
  * GitHub: `https://raw.githubusercontent.com/USERNAME/REPO/release/reject-server.mrs`
* **YAML 格式 (`behavior: domain`)**:
  * jsDelivr: `https://cdn.jsdelivr.net/gh/USERNAME/REPO@release/reject-server.yaml`
  * GitHub: `https://raw.githubusercontent.com/USERNAME/REPO/release/reject-server.yaml`
* **纯文本格式 (`.list` / `.txt`)**:
  * jsDelivr: `https://cdn.jsdelivr.net/gh/USERNAME/REPO@release/reject-server.list`

### 2. 客户端版 (`reject-client`)
* **MRS 二进制 (强烈推荐)**:
  * jsDelivr: `https://cdn.jsdelivr.net/gh/USERNAME/REPO@release/reject-client.mrs`
  * GitHub: `https://raw.githubusercontent.com/USERNAME/REPO/release/reject-client.mrs`
* **YAML 格式 (`behavior: domain`)**:
  * jsDelivr: `https://cdn.jsdelivr.net/gh/USERNAME/REPO@release/reject-client.yaml`
  * GitHub: `https://raw.githubusercontent.com/USERNAME/REPO/release/reject-client.yaml`
* **纯文本格式 (`.list` / `.txt`)**:
  * jsDelivr: `https://cdn.jsdelivr.net/gh/USERNAME/REPO@release/reject-client.list`

---

## Mihomo 配置使用范例

### 方式 A：使用 `.mrs` 规则集（推荐，最高效）

```yaml
rule-providers:
  # 客户端移动端使用：
  adblock-client:
    type: http
    behavior: domain
    format: mrs
    path: ./ruleset/reject-client.mrs
    url: "https://cdn.jsdelivr.net/gh/USERNAME/REPO@release/reject-client.mrs"
    interval: 86400

  # 服务器 / 软路由使用：
  adblock-server:
    type: http
    behavior: domain
    format: mrs
    path: ./ruleset/reject-server.mrs
    url: "https://cdn.jsdelivr.net/gh/USERNAME/REPO@release/reject-server.mrs"
    interval: 86400

rules:
  # 在 rules 数组顶端放置一条拦截规则即可
  - RULE-SET,adblock-client,REJECT
  # - RULE-SET,adblock-server,REJECT
  - ...后续正常分流规则...
```

### 方式 B：使用标准 `.yaml` 规则集

```yaml
rule-providers:
  adblock:
    type: http
    behavior: domain
    format: yaml
    path: ./ruleset/reject-client.yaml
    url: "https://cdn.jsdelivr.net/gh/USERNAME/REPO@release/reject-client.yaml"
    interval: 86400

rules:
  - RULE-SET,adblock,REJECT
  - ...后续正常分流规则...
```

---

## 本地手动构建

如需在本地调试或测试构建：

```bash
# 1. 确保安装了 Python 3.9+ 和 Go 1.21+
python --version
go version

# 2. 运行构建脚本 (自动完成下载、解析、剪枝去冗余并编译 mrs)
python scripts/build.py --profile all --output publish
```

---

## 致谢上游项目

本项目的规则源自以下优秀的开源维护者，感谢他们的无私贡献：
* [Loyalsoldier/clash-rules](https://github.com/Loyalsoldier/clash-rules)
* [SukkaW/Surge (ruleset.skk.moe)](https://ruleset.skk.moe)
* [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat)
* [217heidai/adblockfilters](https://github.com/217heidai/adblockfilters)
* [TG-Twilight/AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule)
