#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error

# ============ 配置区（改成你自己的） ============
TOKEN = ""  # 把抓包得到的 authorization 值粘贴到这里（青龙面板请用环境变量 WUMU_TOKEN）
APP_ID = "97c0bf46-d8c1-4b4f-93ab-526971f1bf47"  # 通常固定不变
# ===============================================

BASE_URL = "https://api3.umu168.com"

HEADERS = {
    "authorization": "",
    "app": APP_ID,
    "teenager": "no",
    "content-type": "application/json",
    "User-Agent": "okhttp/4.9.1",
    "Accept-Encoding": "gzip",
    "Connection": "Keep-Alive",
}

# 青龙面板通知模块（存在则自动启用）
try:
    from notify import send as ql_send
    HAS_QL_NOTIFY = True
except ImportError:
    ql_send = None
    HAS_QL_NOTIFY = False


def http_request(path, method="GET", body=None, token=None, timeout=15):
    """发送请求并返回解析后的 JSON"""
    url = BASE_URL + path
    headers = dict(HEADERS)
    headers["authorization"] = token

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            try:
                return json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                import gzip
                return json.loads(gzip.decompress(raw).decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", "ignore")
        print(f"[错误] HTTP {e.code} {e.reason}")
        if err_body:
            print(f"       {err_body[:500]}")
        return None
    except urllib.error.URLError as e:
        print(f"[错误] 网络异常: {e.reason}")
        return None


def decode_token(token):
    """解码 token，展示里面对应的用户信息（仅提示用途）。"""
    try:
        raw = base64.b64decode(token + "=" * (-len(token) % 4)).decode("utf-8")
        return raw
    except Exception:
        return "(无法解码)"


def get_sign_days(token):
    """查询本周签到情况。"""
    return http_request("/sign/getSignDays", "GET", token=token)


def get_user_info(token):
    """查询用户信息。"""
    return http_request("/user/info", "GET", token=token)


def do_sign(token, is_double=0):
    """执行签到。is_double: 0=普通签到，1=双倍签到。"""
    return http_request("/sign/sign", "POST", body={"isDouble": is_double}, token=token)


def run(token, is_double=0):
    """执行完整签到流程，返回 (成功与否, 日志文本列表)。"""
    logs = []
    success = True

    logs.append(f"Token 解码信息: {decode_token(token)}")

    # 1. 查询签到状态
    logs.append("[1/3] 查询签到状态 ...")
    sign_info = get_sign_days(token)
    signed = False
    if sign_info and sign_info.get("code") == 0:
        data = sign_info.get("data", {})
        signed = data.get("isSign", False)
        sign_count = data.get("signCount", 0)
        logs.append(f"      今日已签到: {'是' if signed else '否'}")
        logs.append(f"      连续签到天数: {sign_count}")
        if signed:
            logs.append("      今日已经签到过了，无需重复签到。")
        for d in data.get("signDay", []):
            r = d.get("reward", {})
            mark = "[已签]" if d.get("isSign") else "[未签]"
            logs.append(f"      {d.get('date','?')} {mark} 奖励: {r.get('reward')} {r.get('rewardName','')}")
    else:
        success = False
        logs.append("      查询失败: " + json.dumps(sign_info, ensure_ascii=False))

    # 2. 如果今天还没签到，执行签到
    logs.append("[2/3] 执行签到 ...")
    if signed:
        logs.append("      已签到，跳过签到请求。")
    else:
        result = do_sign(token, is_double)
        if result and result.get("code") == 0:
            reward = result.get("data", {})
            logs.append(f"      签到成功！获得奖励: {reward.get('reward')} {reward.get('rewardName','')} (type={reward.get('rewardType')})")
        elif result is not None:
            success = False
            logs.append("      签到失败: " + json.dumps(result, ensure_ascii=False))
        else:
            success = False
            logs.append("      签到请求未得到有效响应。")

    # 3. 查询用户资产
    logs.append("[3/3] 查询用户资产 ...")
    info = get_user_info(token)
    if info and info.get("code") == 0:
        d = info.get("data", {})
        assets = d.get("assets", {})
        grade = d.get("grade", {})
        logs.append(f"      昵称: {d.get('alias')}")
        logs.append(f"      等级: {grade.get('level_name','?')} (Lv.{grade.get('level_value','?')})")
        logs.append(f"      积分: {assets.get('integral')}")
        logs.append(f"      唔姆币: {assets.get('wumucoin')}")
        logs.append(f"      VIP时长: {assets.get('vip_time')}")
    else:
        success = False
        logs.append("      查询失败: " + json.dumps(info, ensure_ascii=False))

    logs.append("完成。")
    return success, logs


def notify_qinglong(success, logs):
    """调用青龙面板 notify 发送通知。"""
    if not HAS_QL_NOTIFY:
        return
    text = "\n".join(logs)
    title = "唔姆签到成功 ✅" if success else "唔姆签到失败 ❌"
    try:
        ql_send(title, text)
        print("[通知] 已通过青龙 notify 发送通知。")
    except Exception as e:
        print(f"[通知] 发送失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="唔姆 App 自动签到脚本")
    parser.add_argument("--token", "-t", default=None, help="authorization token")
    parser.add_argument("--double", action="store_true", help="使用双倍签到 isDouble=1")
    args = parser.parse_args()

    # token 优先级：命令行参数 > 环境变量 WUMU_TOKEN > 脚本内 TOKEN 常量
    token = (args.token or os.environ.get("WUMU_TOKEN") or TOKEN or "").strip()
    if not token:
        print("未提供 token！")
        print("  - 命令行: python3 wumu_sign.py --token \"你的token\"")
        print("  - 环境变量(青龙面板推荐): WUMU_TOKEN=你的token")
        print("  - 或直接编辑脚本顶部 TOKEN 变量。")
        sys.exit(1)

    # 双倍签到：命令行 --double > 环境变量 WUMU_DOUBLE
    double_env = os.environ.get("WUMU_DOUBLE", "").strip().lower()
    is_double = 1 if (args.double or double_env in ("1", "true", "yes", "on")) else 0

    print("=" * 50)
    success, logs = run(token, is_double)
    for line in logs:
        print(line)
    print("=" * 50)

    # 青龙面板环境自动发通知
    notify_qinglong(success, logs)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()