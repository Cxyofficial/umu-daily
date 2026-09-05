# 唔姆 App 自动签到脚本

自动完成「唔姆」（`com.umu168.wumu`）App 的每日签到，纯 Python 标准库实现，无需额外依赖。

支持：本地命令行运行、**青龙面板**、**GitHub Actions** 定时运行。

## 功能

- 查询本周签到状态（`/sign/getSignDays`）
- 执行每日签到（`/sign/sign`），已签到则自动跳过，避免重复
- 查询用户资产（`/user/info`）
- 青龙面板环境自动调用 `notify` 发送通知

## 原理

签到接口：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/sign/getSignDays` | GET | 查询本周签到状态 |
| `/sign/sign` | POST | 执行签到，请求体 `{"isDouble":0}` |
| `/user/info` | GET | 查询用户资产 |

鉴权只需要三个请求头：

```
authorization : <用户 token>   # Base64(毫秒时间戳_用户ID)
app           : 97c0bf46-d8c1-4b4f-93ab-526971f1bf47
teenager      : no
```

## 使用方法

### 1. 获取 token

通过抓包工具（如 Reqable / Charles / mitmproxy）抓取 App 的任意一个 `api3.umu168.com` 请求，
复制请求头中 `authorization` 的值。

### 2. 填写 token

编辑 `wumu_sign.py` 顶部的 `TOKEN` 变量：

```python
TOKEN = "你的 token"
```

或在运行时通过参数传入：

```bash
python3 wumu_sign.py --token "你的 token"
```

### 3. 运行

```bash
python3 wumu_sign.py
```

### 4. 定时运行（可选）

使用 crontab / Termux 定时任务，每天执行一次：

```bash
0 7 * * * python3 /path/to/wumu_sign.py
```

## 青龙面板部署

### 1. 新建脚本

在青龙面板「脚本管理」中新建脚本，命名为 `wumu_sign.py`，将脚本内容粘贴进去。

### 2. 添加环境变量

在「环境变量」中添加：

| 名称 | 值 | 是否必填 |
|------|-----|---------|
| `WUMU_TOKEN` | 你的 authorization token | 必填 |
| `WUMU_DOUBLE` | `true` / `false`（是否双倍签到） | 选填，默认 `false` |

### 3. 新建任务

| 字段 | 值 |
|------|-----|
| 任务名称 | 唔姆签到 |
| 命令 | `task wumu_sign.py` |
| 定时规则 | `0 9 * * *`（每天 9 点，可自行调整） |

> 说明：青龙面板运行时会自动注入 `notify` 模块，脚本检测到后会调用它发送「签到成功/失败」通知，无需额外配置通知方式。

## GitHub Actions 部署

### 1. 配置 Secrets

在仓库「Settings → Secrets and variables → Actions → New repository secret」中添加：

| 名称 | 值 | 是否必填 |
|------|-----|---------|
| `WUMU_TOKEN` | 你的 authorization token | 必填 |
| `WUMU_DOUBLE` | `true` / `false` | 选填，默认 `false` |

### 2. 触发方式

- **定时触发**：每天 00:30 UTC（北京时间 08:30）自动运行，可在 `.github/workflows/sign.yml` 中调整 `cron`。
- **手动触发**：在 Actions 页面选中「唔姆签到」workflow → Run workflow。
- **推送触发**：向 `main` / `master` 分支推送代码时自动运行（可用于首次部署验证）。

### 3. 注意事项

- GitHub Actions 的定时任务在仓库 60 天无活动时会被暂停，偶尔手动触发一次即可保持活跃。
- GitHub 免费版的 Actions 有额度限制，但每天一次的签到完全够用。
- 若需要失败通知，可取消 `.github/workflows/sign.yml` 中 Telegram 通知部分的注释，并配置对应 Secrets。

## 参数说明

| 参数 | 说明 |
|------|------|
| `--token, -t` | 指定 authorization token |
| `--double` | 使用双倍签到（`isDouble=1`） |
| `--no-double` | 普通签到（默认，`isDouble=0`） |

## 注意事项

- token 由服务端下发，**过期后需重新在 App 中抓包获取**，脚本无法自动续期。
- 本脚本仅供学习交流，请勿用于非法用途或高频请求。
- 请勿将包含个人 token、手机号等敏感信息上传到公开仓库。