import http.client
import base64
import json
from config import UDPApiSecret, ApimUrl, KVuser, KVPasswd, SecretsEngines, NETWORK_ENV


def get_bearer_token():
    encoded_u = base64.b64encode(UDPApiSecret[NETWORK_ENV].encode()).decode()
    conn = http.client.HTTPSConnection(ApimUrl[NETWORK_ENV])
    payload = 'grant_type=client_credentials'
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic %s' % encoded_u,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    conn.request("POST", "/token", payload, headers)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    print(data)
    json_data = json.loads(data)
    token = json_data["access_token"]
    return token


def get_vault_secret(token, key, path):
    conn2 = http.client.HTTPSConnection(ApimUrl[NETWORK_ENV])
    payload2 = json.dumps({
        "typeOfAuth": "LDAP",
        "engine": "KV",
        "namespace": "NameSpaceName",
        "userName": KVuser,
        "password": KVPasswd,
        "path": path,
        "typeOfResponse": "json",
        "role_id": "",
        "secret_id": ""
    })
    headers2 = {
        'Authorization': 'Bearer %s' % token,
        'Content-Type': 'application/json'
    }
    conn2.request(
        "POST", "URL" + SecretsEngines[NETWORK_ENV], payload2, headers2)
    res2 = conn2.getresponse()
    data2 = res2.read().decode("utf-8")

    json_data = json.loads(data2)
    secret = json_data[key]
    return secret
