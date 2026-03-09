import json
from curl_cffi import requests

# ==========================================
# ⚠️ 注意: 请把下面这段替换为你真实的完整 JSON 数据
AUTH_DATA_JSON = """
{
  "WARNING_BANNER": "!!!!!!!!!!!!!!!!!!!! DO NOT SHARE ANY PART OF THE INFORMATION YOU SEE HERE. THIS INFORMATION IS SENSITIVE AND CAN GRANT ACCESS TO YOUR ACCOUNT. SHARING THIS INFORMATION IS LIKE SHARING YOUR PASSWORD. !!!!!!!!!!!!!!!!!!!!",
  "user": {
    "id": "user-2GTmOjN7UeXyT9dfiRo1W2ad",
    "email": "x3i15ssao8pk@198994216.xyz",
    "idp": "auth0",
    "iat": 1773037915,
    "mfa": true
  },
  "expires": "2026-06-07T06:50:51.923Z",
  "account": {
    "id": "4fa10d1f-bde0-4a0d-872b-043cf253ac7d",
    "planType": "free",
    "structure": "personal",
    "isConversationClassifierEnabledForWorkspace": true,
    "isFinservEnabledWorkspace": false,
    "isFedrampCompliantWorkspace": false,
    "isDelinquent": false,
    "residencyRegion": "no_constraint",
    "computeResidency": "no_constraint"
  },
  "accessToken": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE5MzQ0ZTY1LWJiYzktNDRkMS1hOWQwLWY5NTdiMDc5YmQwZSIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS92MSJdLCJjbGllbnRfaWQiOiJhcHBfWDh6WTZ2VzJwUTl0UjNkRTduSzFqTDVnSCIsImV4cCI6MTc3MzkwMTkxNSwiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS9hdXRoIjp7ImNoYXRncHRfYWNjb3VudF9pZCI6IjRmYTEwZDFmLWJkZTAtNGEwZC04NzJiLTA0M2NmMjUzYWM3ZCIsImNoYXRncHRfYWNjb3VudF91c2VyX2lkIjoidXNlci0yR1RtT2pON1VlWHlUOWRmaVJvMVcyYWRfXzRmYTEwZDFmLWJkZTAtNGEwZC04NzJiLTA0M2NmMjUzYWM3ZCIsImNoYXRncHRfY29tcHV0ZV9yZXNpZGVuY3kiOiJub19jb25zdHJhaW50IiwiY2hhdGdwdF9wbGFuX3R5cGUiOiJmcmVlIiwiY2hhdGdwdF91c2VyX2lkIjoidXNlci0yR1RtT2pON1VlWHlUOWRmaVJvMVcyYWQiLCJ1c2VyX2lkIjoidXNlci0yR1RtT2pON1VlWHlUOWRmaVJvMVcyYWQifSwiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS9tZmEiOnsicmVxdWlyZWQiOiJ5ZXMifSwiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS9wcm9maWxlIjp7ImVtYWlsIjoieDNpMTVzc2FvOHBrQDE5ODk5NDIxNi54eXoiLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZX0sImlhdCI6MTc3MzAzNzkxNSwiaXNzIjoiaHR0cHM6Ly9hdXRoLm9wZW5haS5jb20iLCJqdGkiOiI3YWI3MTkyNS0wZjZiLTQ3M2EtOWU4Yy0xZTRjYTgwMjUzODIiLCJuYmYiOjE3NzMwMzc5MTUsInB3ZF9hdXRoX3RpbWUiOjE3NzMwMzc5MTM5OTksInNjcCI6WyJvcGVuaWQiLCJlbWFpbCIsInByb2ZpbGUiLCJvZmZsaW5lX2FjY2VzcyIsIm1vZGVsLnJlcXVlc3QiLCJtb2RlbC5yZWFkIiwib3JnYW5pemF0aW9uLnJlYWQiLCJvcmdhbml6YXRpb24ud3JpdGUiXSwic2Vzc2lvbl9pZCI6ImF1dGhzZXNzX3YzOUdZT0toOWNGUUtHSFhYN2FmMmxnQiIsInNsIjp0cnVlLCJzdWIiOiJhdXRoMHxoVDlhRXc4d3hmRjJldzgybmtmTkdBQlAifQ.A6aJ9OXrv6ThO3sQ9pPXAAiIXi3FcgW2i3jC8q752h8OWDyMhPbX4OOwAQDzd7ky9iTyZ3lAVuY8gRqL0mpo3e6phriCEIj9JNsYkTda3gMzjqBQFfsvFDHmj9shwoLWfx30aCskw2sqfxUsW37batx-zT5CbI4iJxDP9xm7lUh6MXSXnUHfrYHJnXKtzAnIPtQJtuiTJc_4KKQ4t3abOqTDUBBpdvUTJ4Tj96n98qlWgJMr200bdsTSI2mWkMnqRuso59dP1tB4QnN-Tee-yT7kiMqvdoPKzCs5GLsBj04Yh2i-yZHHHwxtKzmi2q7hf1jKCa0uPylHvYCn7GLefnmcNb7Ewjoty8wCd8C34cUkCYRBvV-qQVOoyaQl2D5eQYyfZiCC8Yoke1vbPfJTi43qZHOrEr6avaHCteRl-yttpvckN0sbKzvPBnGKV5QBHNsLTSzabZKpXFQIjL2K2QVTr4VYogAAp-kv96ngjrSW-XIC1w1OfMo7YFXzT7a7CzMb1QIad4QOXZlPZ8RqOvnT9CcBK9krbwKj7OF7XT6hJvVftEdiR9pijOU2mNfS5yNU4TYFQaeKVTn3Woih4QBSLwvJVxMZk65LDYE7crVjDvmXpdE1c8lwZeKnhRsfIgoTHxb0v8UVYd9PRnMY0oELQ9v4sHQRB9M_Q-BQvPQ",
  "authProvider": "openai",
  "sessionToken": "eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..YT2q2mBwVnHUbbwL.n7syzVCx3XktZgZ8Ne-yBrc_ifuzTHj8C6Vw1IEAugeRza-udsIeeS8fsUVAvXFL-mV-n52_1lX5DfEC3AUcGdJ_B6X1_TZGG2i-rK9A9rhPO7Dubf5XogarGzUw46P_6B64jKm1chkedmQ6U0fvJpKPJ75zzjU8nE0DnIAeC6fEnXSO7c2eE9XFG53zQn8uTvIm2-j9IJdNSlGFq49WAjb06O0_WEhdy0g_pi4KdXM6LUkm-5mWAWMkcO1xlXDDWU9Wz1JudQqruwY93pk0i0kGisMVtqtk1Oq7tLdDywLPx4sH1KT1VKClJhxj0uOi9AMNhBSHn0fmldoa2VKxxf-NEAy9s634RSZq8BIZf8zfoAhBJJmFVoLOCuPJDRKUNqf11vrr04CVx8tPqJF1KhGEH_RXOiOcbCtgykDR-D2hNEzDtGYIIA9Il1sWGPKFP0QZiaHmwVM-YUCays7ELRXDs3pc6_iG2RWP-by4waEnKW-LHzQdQBfOXz7lQwgAo4TXGTwsrgiBD_hsUHO-Rbb5BOLLqtQNKvrimG0DUCnk4b8b4LipJE3JFdy_c57vCV7_dwZkFOT3nLPIfWv7br3zXGUA6h4BlYYOtIkveFWGwM2eatgi8cKbgZW1aTpvsKklpJ4tU-VMMyvXa8dYBV55eAS8idT-aRc8iyuYRCGreZyC3ualUf7fpDGQV-8KUiMfjdW1PMOA1Od9OZBXxA-GvvZkZHpqNqx28-X335jZJf41OWUkre1jGPu_XlsGr3i5IjD0v6VHvgwRp9wvwr5XQONmrYSHvKNY1w2o6Rp7mD7w1vlu_mkJ_MdcTrhNFtwH7C4zwAy87xBfBvrfVo_OnuizKr2joE7GjBWOoTLldEuleoTsETgThrUmgHZXee4zn1wziG0Lp6V1a2yUVZyIJP9Du_tEX0er_p4sFH4jynINBgUwIiS6hSweoL3af_Th6SW-kz_yeB2L3dipT70eHHAY8T-4EZNcjDYhrIzI6U4vQYEED2YtHo4u5WMBgxNoCybUivKvl_qOZO-TX_oU_ss287PTDfk9buLzv-OKDpbqkh5mEvEpCIhiIQit3sujV-jnzhlMU3SRnRFM97g08UVQc3LUS8pZVjeBbCGBMDiQOWCLI2snsstq2Yw8w2iBqbhNqZAecKh8oIe8mDLsQTelH3rtMPGWYxndY0MyMvPtgPD1Ee--VJy3T21xLwPLZMMRTu4dCkSXsjEIB6rOg-OftKBPxuXB3Sq2hcBzxWux_BjHHhkQ6qtNH0XuYhj3qtS45WCpSObuPIuy-KX4dTQj3KWaKdfVftjfKBWOaZfqkJqCZTYIWojVY5n1s1AxG3XM9b8Q2_ZWXnSPCAtsvsNQYxfSYdOZHKto655QN8sGxneLwOTKmKEZpk0PU1yVSXNd_fFwO5QNKtlCQRTBx-kZyWA2O582NU8WylWEOJTq0EFDPcer0cetftB0l5MIMksKZSEVRV0j-l_-bHqug7KwyQnTN5LVXp2vUJ_hgC048TCnm0zODOZMIRCjF0WCyNHSdvD8XEf3CajouScffEEoyDsen6LbMfroInIx8Q4EC_4eVOadhl_onW17c5yJiolXDjaXtFYRChupNiwMkqzNzb2bvnGY8fvxIu1i7zteSa5JA7nvgBYCZbK9rbufUcepWIFAoSmKpO3bveakfCSmNucVmBBq3muESYwtuheORTvOL1SG4eeJ5R2PMa7OZJoMOSRih5T0vdsqXRuB2P7S1jy6MICUJQT_ekbLeNt7ExxyZOlx0juWbFbEX0gRPKCKXkJ03kb63jODWeCXbYmEHvMMD-lEXERwAmTr1DbblaOuJBlsTMjRBzvy8JNLaXdSgcncAO9cozN-6wG5CSGu5QdjC5V-1MjgtqDywmMJ_EpUtSxVXyVPLTMQoChv3RcNXBxmhYjBtw5fXbfCFY-x3v0kaozgUb91LutguuBjNzZWDc6mTQnetxfM_0jBZrwuy8wUQDWcwk9YEilKl_OPGApGkscR77MHl6B_P80d0RBoi1hg1MgOgsJbTwmvKXdXQLAbVpCQpJm0c1VO3R9ecF0z7jsNIrgVEfkW6UI8k1v_bHRpMEpWAdUcanNk1WSocb9CGM4DdM5__eqksCQJD1sVYz0zwzgELNYAJZ4tbxkl97pGtYNfMfRWST3BJPuwyMy7-LFzSYwOWpys2JB1kF8lF9yKVmtTTftC4CO6-ZQKNQUUYoXlN-vnnDy2S-ig6mlSzypui6eHvnZw5Us6LThWL8GsVy5DtwvNb5iD3QywjjPV1i09c84rOefm10nmVi93DVVeCtoC6HE1LBMcCko_wDCicK0uNENLa8a3vWNywakl9vRijFLcmFtasTcCJ_KNYR8KlisSlplYtXw72VjZSXGFzZaHuYDysNm8ZwT2doY32DnZGdWXyYFE7Wkg6H0UD5i0xIqXVRoCXHJ730ryhLYRbg_M3Ygc480rOwnraeDpg3uaBq4-L4AaSHO78xc-KVPtmlq7l2HieCrZLJg9t40xmrf-2Gd2g6JhmZaVUzkV2-vKvjbd53i1xG8m0zxGOojhCVlT55YCF3IBMP6AR2HhhO582ioxX9_SS-jw840840-ot3D1fgWOpSRIWT-MNa8-qkH13AxOvc6HuLEOjlHss62FcMn_GBq4GC5e99Eep2hjCY_xzaLP_adKxbmZqR9jEFzuoIDD5ZqY-8Rg5-xuHBKz393sSy1CmbbZ57ttaubVHMG4bBlHsRSoOr_iVXCT7aC4pFd-VgJI1rrVPfBGhs8Ly-t9Rsenoeku2sXTUzAHStGRofIPu-wBJa4cLl8QKPPw_2MjIZ6XbBz9bliq5uk3tqfTyFwQMQoTZNxdBcqMgXjB2NNQ2xGpsdDzH4-PseAupeBqppesU90wAKHWwfNWUGPHn8FUfkDzscKqYJ2cWGJW6F393KBI__idU21iBerZNwKQpibZ6uVDkL9tILVE9eD43lss8bFCRxLzxkdU5lom_j3Q6UmO1OMfeMC0s-4uVZQRYCkZsVUWhRpI4bKdjEa37AFq9df_bwo_4skqHDtgIKl8lJ_dZd4wnMdTQk1BPiGKuNvPYGWsxBahsxxOFB4vaiuWcvo6YzmYFlK5APdPWH_SY1QzGperCuV4GefYtqCQFzPDkxUjeAs8vX4kR8UCa9nQlHd3Blmx2ssWywtrsmD6mw5WVTkN7hH8JOdAFcc1XODDqwyGHttBj-ACkdzfnjjy0rox7NsIDYIRfuQd9dtURNnlriz3KCJ6ZjHYylRLRUa0qfE2j8j9g_A0S_5udHlHD3Vsx9cY6Grb8hGbrf36hsG8lLpgx2inhBIZX4Ei0_Ly-uXMh7ZWJaKNsnASLBd_Yia4S5EekAGdpKCJUl4M2feSBnZYvkNSQ_IzZmN15UXJ-sjinxr2095utNPUcMYwB07xRxxwxZt1-3n8sMHYWzpJnhuzhWu8z1BdBgCCzG1HFX3zjhV5MNf39wz2-wUeXUjrP94zva4HHNNJsY5bDEaPC_utXGKcUX0bsQDVDsvvOXqBj-icW_khJoJvkq-z5sdq5Ax_R7HAwWLVFGts64oHIviqu5UVZAmcMji3i2ozU7TLxWdzR10HsBV0IjymeqFd4c5qWbx3wHO6RCkSfJlMgc8VogbpDNPNTDLx2L_Ce_l1GXCqEJb1J_FntYgMN0iVg-ZhOkqITsuuZtOf5n8doDU2rW11dZ4TIvR5ZkSzMNgsYMkFVSlZSRri7rYapTrz.FLyo6nESbmtzFhkwsJ5h7A",
  "rumViewTags": {
    "light_account": {
      "fetched": false
    }
  }
}
"""

# ！！！在这里选择你要生成的优惠类型 ！！！
# 可选值: "team-1-month-free" 或 "plus-1-month-free"
TARGET_PROMO = "team-1-month-free"


# ==========================================

def get_checkout_url(access_token, workspace_name, mode, promo_id, proxy_url):
    """
    通用请求函数
    :param mode: "custom" 生成新页面, "redirect" 生成老页面
    :param promo_id: 优惠码
    """
    url = "https://chatgpt.com/backend-api/payments/checkout"

    # 基础 Payload (Plus 和 Team 通用的部分)
    payload = {
        "billing_details": {
            "country": "US",
            "currency": "USD"
        },
        "cancel_url": "https://chatgpt.com/#pricing",
        "promo_campaign": {
            "promo_campaign_id": promo_id,
            "is_coupon_from_query_param": False
        },
        "checkout_ui_mode": mode
    }

    # 根据优惠码动态决定 plan_name 和附加参数
    if promo_id == "team-1-month-free":
        payload["plan_name"] = "chatgptteamplan"
        payload["team_plan_data"] = {
            "workspace_name": workspace_name,
            "price_interval": "month",
            "seat_quantity": 5
        }
    elif promo_id == "plus-1-month-free":
        payload["plan_name"] = "chatgptplusplan"
        # Plus 套餐不需要 team_plan_data，所以不添加
    else:
        return None, f"未知的优惠码配置: {promo_id}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Origin": "https://chatgpt.com",
        "Referer": "https://chatgpt.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            proxies=proxies,
            impersonate="chrome120",
            timeout=15
        )

        if response.status_code == 403:
            return None, "被 Cloudflare 拦截 (403 Forbidden)"

        response.raise_for_status()
        data = response.json()

        # 解析新页面链接
        if mode == "custom" and "checkout_session_id" in data:
            processor = data.get("processor_entity", "openai_llc")
            session_id = data["checkout_session_id"]
            return f"https://chatgpt.com/checkout/{processor}/{session_id}", None

        # 解析老页面链接
        elif mode == "redirect" and "url" in data:
            return data["url"], None

        else:
            return None, f"未知的返回格式: {json.dumps(data)}"

    except Exception as e:
        return None, str(e)


def generate_both_checkout_pages():
    try:
        auth_data = json.loads(AUTH_DATA_JSON)
        access_token = auth_data.get("accessToken")
        email = auth_data.get("user", {}).get("email", "")

        if not access_token:
            print("❌ 错误: 未能在 JSON 中找到 accessToken")
            return
    except json.JSONDecodeError:
        print("❌ 错误: JSON 格式不正确")
        return

    # 提取邮箱前缀作为工作区名称 (仅 Team 会用到，提取了备用)
    workspace_name = email.split("@")[0] if email and "@" in email else "zhizhishu"

    # 你的本地代理端口
    proxy_url = "http://127.0.0.1:10808"

    plan_display = "Plus 套餐" if TARGET_PROMO == "plus-1-month-free" else "Team 套餐"
    print(f"⏳ 正在生成 {plan_display} 链接 (使用优惠: {TARGET_PROMO})...")
    print(f"🌐 代理节点: {proxy_url}")
    print("-" * 50)

    # 1. 生成新页面链接
    print("[1/2] 正在请求新页面链接...")
    new_url, new_err = get_checkout_url(access_token, workspace_name, "custom", TARGET_PROMO, proxy_url)
    if new_url:
        print(f"✅ 新页面生成成功!\n🔗 链接: {new_url}")
    else:
        print(f"❌ 新页面生成失败: {new_err}")

    print("-" * 50)

    # 2. 生成老页面链接
    print("[2/2] 正在请求老页面链接...")
    old_url, old_err = get_checkout_url(access_token, workspace_name, "redirect", TARGET_PROMO, proxy_url)
    if old_url:
        print(f"✅ 老页面生成成功!\n🔗 链接: {old_url}")
    else:
        print(f"❌ 老页面生成失败: {old_err}")


if __name__ == "__main__":
    generate_both_checkout_pages()