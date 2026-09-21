# IP_Range

全球各国家/地区 IPv4 地址段（CIDR 格式）集合。

## 目录结构

```
IP_Range/
├── README.md                          # 本文件
├── China_IP/                          # 中国大陆 IP 段
│   ├── China_IP.txt                   # 中国大陆 IPv4 CIDR 列表（8,792 条，数据来源 APNIC）
│   └── chnroutes.py                   # Python 3 脚本，从 APNIC 自动获取并生成 CIDR 列表
├── 中国香港/中国香港.txt               # 3,073 条
├── 中国台湾/中国台湾.txt               # 728 条
├── 中国澳门/中国澳门.txt               # 31 条
├── 美国/美国.txt                       # 4,489 条
├── 英国/英国.txt                       # 679 条
├── 德国/德国.txt                       # 436 条
├── 日本/日本.txt                       # 527 条
├── ... (共 139 个国家/地区)
```

## 文件说明

### China_IP/ 目录

| 文件 | 说明 |
|------|------|
| `China_IP.txt` | 中国大陆 IPv4 地址段 CIDR 列表，共 8,792 条。数据从 APNIC `delegated-apnic-latest` 自动提取 |
| `chnroutes.py` | Python 3 脚本，从 APNIC 实时获取中国 IP 分配数据，支持生成多种平台的路由规则 |

#### chnroutes.py 用法

```bash
# 生成 CIDR 格式列表（默认输出 China_IP.txt）
python3 chnroutes.py -p cidr

# 生成 OpenVPN 路由配置
python3 chnroutes.py -p openvpn -m 5

# 生成 Linux 路由脚本
python3 chnroutes.py -p linux

# 生成 Windows 批处理脚本
python3 chnroutes.py -p win

# 生成 macOS 路由脚本
python3 chnroutes.py -p mac

# 生成 Android 路由脚本
python3 chnroutes.py -p android
```

### 国家/地区目录

每个国家/地区对应一个独立文件夹，文件夹内包含同名的 `.txt` 文件。

- 文件格式：每行一条 CIDR 记录，如 `1.36.0.0/16`
- 数据来源：国内外 IP 地址段归属表
- 覆盖范围：中国港澳台 + 全球 139 个主要国家/地区
- 总记录数：约 15,263 条

## 使用场景

- **路由器分流配置**：在 OpenWrt PassWall/PassWall2 中用作直连/代理分流规则
- **防火墙规则**：生成 iptables/nftables 规则，按国家/地区放行或阻断流量
- **VPN 分流**：在 OpenVPN 配置中添加路由，使特定国家 IP 走直连
- **GeoIP 过滤**：用于 DNS 分流、CDN 选优等场景

## 数据来源

| 数据 | 来源 |
|------|------|
| 中国大陆 IP | APNIC - `https://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest` |
| 中国港澳台 IP | 国内外 IP 地址段归属表 |
| 国外国家 IP | 国内外 IP 地址段归属表（掩码 ≤ /16 的大网段） |

## 注意事项

- 国外国家 IP 段仅包含掩码 ≤ /16 的大网段，小于 /16 的零散小段未收录
- 中国大陆 IP 段由脚本从 APNIC 实时获取，可定期运行 `chnroutes.py` 更新
- IP 地址段数据会随时间变化，建议定期更新
- 文件中的数据仅供参考，不保证完整性和准确性