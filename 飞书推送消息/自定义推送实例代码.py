# -*- coding: utf-8 -*-
# @Time       :
# Description :
"""
 *  describe :
 *  author   :
 *  time     :
"""

import requests
import json
import sys


# 获取访问令牌
def get_access_token():
    app_id = "cli_a5d1873e50fad00b"
    app_secret = "ZNZpmg2LeQtiTWevfpVCOeHFPuFqs3c3"
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    params = {
        "app_id": app_id,
        "app_secret": app_secret
    }
    response = requests.post(url, params=params)
    return response.json().get("tenant_access_token")


# 机器人推送消息到群
def get_all_field_names(text_list):
    text = "RAT - JIRA存在无对应关系\n" + ",\n".join(text_list)
    access_token = get_access_token()
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {
        "Authorization": "Bearer " + access_token
    }
    body = {
        "receive_id": "oc_bf6be67fb690bfc6832508e70d360d2f",
        "msg_type": "text",
        "content": {
            "text": text
        }
    }
    response = requests.post(url=url, headers=headers, json=body)
    response_json = response.json()
    print(response_json)
    print(response_json['msg'])
    if response_json['msg'] == 'ok':
        print("消息推送，mesid为：" + response_json["data"]["message_id"])
    else:
        print("发送失败")
        sys.exit(1)


# 机器人推送消息到人
def get_all_field_names(text_list):
    text = "RAT - JIRA存在无对应关系\n" + ",\n".join(text_list)
    access_token = get_access_token()
    url = f"https://open.feishu.cn/open-apis/message/v4/batch_send/"
    headers = {
        "Authorization": "Bearer " + access_token
    }
    body = {
        "open_ids": ["ou_bc2706e06dd34fb00b4c320671427d9e"],
        "msg_type": "text",
        "content": {
            "text": text
        }
    }
    response = requests.post(url=url, headers=headers, json=body)
    response_json = response.json()
    print(response_json)
    print(response_json['msg'])
    if response_json['msg'] == 'ok':
        print("消息推送，mesid为：" + response_json["data"]["message_id"])
    else:
        print("发送失败")
        sys.exit(1)
