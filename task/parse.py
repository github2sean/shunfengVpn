import json
import base64
from urllib.parse import urlparse, unquote, parse_qs


def generate_vmess_config(vmess_config):
    """
    生成 Xray 配置文件
    :param vmess_config: 解码后的 VMess 配置字典
    :return: Xray 配置文件（JSON 格式）
    """
    xray_config = {
        "inbounds": [
            {
                "port": 1080,  # 本地监听端口
                "protocol": "socks",  # 本地协议
                "settings": {
                    "auth": "noauth",
                    "udp": True
                }
            }
        ],
        "outbounds": [
            {
                "protocol": "vmess",
                "settings": {
                    "vnext": [
                        {
                            "address": vmess_config["add"],  # 服务器地址
                            "port": int(vmess_config["port"]),  # 服务器端口
                            "users": [
                                {
                                    "id": vmess_config["id"],  # 用户 UUID
                                    "alterId": int(vmess_config.get("aid", 0)),  # 额外 ID
                                    "security": vmess_config.get("scy", "auto")  # 加密方式
                                }
                            ]
                        }
                    ]
                },
                "streamSettings": {
                    "network": vmess_config.get("net", "tcp"),  # 传输协议
                    "security": vmess_config.get("tls", ""),  # 传输层安全
                    "tcpSettings": {} if vmess_config.get("net") == "tcp" else None,
                    "wsSettings": {} if vmess_config.get("net") == "ws" else None,
                    "kcpSettings": {} if vmess_config.get("net") == "kcp" else None,
                    "httpSettings": {} if vmess_config.get("net") == "http" else None,
                    "quicSettings": {} if vmess_config.get("net") == "quic" else None
                }
            }
        ]
    }
    print("xray_vmess_config:", xray_config)
    return xray_config


def parse_vless_link(vless_link):
    # 解析 VLESS 链接
    parsed = urlparse(vless_link)

    # 提取基本信息
    uuid = parsed.username
    server_address = parsed.hostname
    port = parsed.port

    # 提取查询参数
    query_params = parse_qs(parsed.query)

    # 提取其他参数
    encryption = query_params.get('encryption', ['none'])[0]
    security = query_params.get('security', ['none'])[0]
    sni = query_params.get('sni', [None])[0]
    network_type = query_params.get('type', ['tcp'])[0]
    ws_host = query_params.get('host', [None])[0]
    ws_path = query_params.get('path', ['/'])[0]

    # 备注（片段）
    remark = parsed.fragment

    # 返回解析结果
    return {
        "uuid": uuid,
        "server_address": server_address,
        "port": port,
        "encryption": encryption,
        "security": security,
        "sni": sni,
        "network_type": network_type,
        "ws_host": ws_host,
        "ws_path": ws_path,
        "remark": remark
    }


def generate_xray_config(vless_data):
    # 生成 Xray 配置文件
    config = {
        "inbounds": [
            {
                "port": 1080,  # 本地监听端口
                "protocol": "socks",  # 本地协议
                "settings": {
                    "auth": "noauth",
                    "udp": True
                }
            }
        ],
        "outbounds": [
            {
                "protocol": "vless",
                "settings": {
                    "vnext": [
                        {
                            "address": vless_data["server_address"],
                            "port": vless_data["port"],
                            "users": [
                                {
                                    "id": vless_data["uuid"],
                                    "encryption": vless_data["encryption"],
                                    "level": 0
                                }
                            ]
                        }
                    ]
                },
                "streamSettings": {
                    "network": vless_data["network_type"],
                    "security": vless_data["security"],
                    "wsSettings": {
                        "path": vless_data["ws_path"],
                        "headers": {
                            "Host": vless_data["ws_host"]
                        }
                    },
                    "tlsSettings": {
                        "serverName": vless_data["sni"],
                        "allowInsecure": True  # 允许不安全的连接（仅用于测试）
                    }
                },
                "tag": "proxy"
            }
        ]
    }
    return config


def parse_trojan_link(ss_link):
    pass


def parse_shadowsocks_link(ss_link):
    """解析 Shadowsocks 链接"""
    if not ss_link.startswith("ss://"):
        raise ValueError("Invalid Shadowsocks link")

    # 去除协议头
    ss_link = ss_link[5:]

    # 处理 base64 编码部分
    if "@" not in ss_link:
        # 如果链接是 base64 编码的
        decoded = base64.b64decode(ss_link).decode("utf-8")
        method_password, server_port = decoded.split("@")
    else:
        # 如果链接是明文格式
        method_password, server_port = ss_link.split("@")

    # 解析方法、密码、服务器地址和端口
    method, password = method_password.split(":")
    server, port = server_port.split(":")

    # 解码可能的 URL 编码
    method = unquote(method)
    password = unquote(password)
    server = unquote(server)
    port = int(unquote(port))

    return {
        "method": method,
        "password": password,
        "server": server,
        "port": port
    }


def create_xray_config(ss_config):
    """生成 Xray 配置文件"""
    config = {
        "inbounds": [
            {
                "port": 1080,  # 本地监听端口
                "protocol": "socks",  # 本地协议
                "settings": {
                    "auth": "noauth",
                    "udp": True
                }
            }
        ],
        "outbounds": [
            {
                "protocol": "shadowsocks",  # 协议类型
                "settings": {
                    "servers": [
                        {
                            "address": ss_config["server"],  # 服务器地址
                            "port": ss_config["port"],  # 服务器端口
                            "method": ss_config["method"],  # 加密方法
                            "password": ss_config["password"]  # 密码
                        }
                    ]
                }
            }
        ]
    }
    return config


def main():
    # Shadowsocks 链接
    ss_link = "ss://YWVzLTI1Ni1nY206RkNFVU9BU1JRSkMwTE4wSw%3D%3D@183.61.177.235:15009#Youtube%E9%A1%BA%E4%B8%B0%E8%B5%84%E6%BA%90%20%20%E9%A6%99%E6%B8%AF%20203"

    # 解析 Shadowsocks 链接
    ss_config = parse_shadowsocks_link(ss_link)

    # 生成 Xray 配置文件
    xray_config = create_xray_config(ss_config)

    # 保存为 JSON 文件
    with open("xray_config.json", "w") as f:
        json.dump(xray_config, f, indent=2)

    print("Xray 配置文件已生成: xray_config.json")


if __name__ == "__main__":
    main()
