# 🔒 安全策略 (Security Policy)

## 支持的版本

下表显示 V2 项目的版本支持情况：

| 版本 | 支持状态 | 安全更新 |
|---|---|---|
| v1.3.0 (latest) | ✅ 积极支持 | 接收 |
| v1.2.x | ⚠️ 关键 fix only | 接收 |
| < v1.2 | ❌ 不支持 | 不接收 |

## 🚨 报告漏洞

**请勿在公开 issue 报告安全漏洞。**

### 报告方式

通过以下任一方式私下报告:

1. **GitHub Security Advisories** (推荐)
   - https://github.com/PerfectZQ888/FIFA-WorldCup-2026-V2/security/advisories/new
   - 私密报告, 只有维护者可见

2. **Email**
   - 通过 GitHub profile 找到维护者邮箱

### 报告内容

请包含:

- 漏洞类型 (例: XSS, SQL injection, 远程代码执行, 信息泄露)
- 受影响文件 / 函数 / API
- 复现步骤 (PoC 代码、curl 命令、截图)
- 影响评估 (影响哪些用户 / 数据)
- 你的修复建议 (如果有)

### 响应时间

| 阶段 | 时间 |
|---|---|
| 初次确认 | 48 小时内 |
| 严重性评估 | 1 周内 |
| 修复发布 (Critical) | 7 天内 |
| 修复发布 (High) | 30 天内 |
| 修复发布 (Medium/Low) | 下一个 release |

## 🔐 已采取的安全措施

- ✅ 全仓敏感信息扫描 (0 命中)
- ✅ 内网 IP 不硬编码 (分享用 `window.location.origin`)
- ✅ GitHub 仓库公开前移除开发期敏感信息
- ✅ Fine-grained PAT 最小权限原则
- ✅ Workflow 文件需 PAT `workflows: write` scope 才能修改
- ✅ systemd `PrivateTmp` + `ProtectSystem` 隔离

## 🛡️ 用户自查清单

部署前检查:

- [ ] 8001 端口有防火墙限制
- [ ] 没用 root 运行 (systemd 改 `User=non-root-user`)
- [ ] `requirements.txt` 用固定版本 (不是 `>=`)
- [ ] 后端日志不记录敏感数据 (密码 / token)
- [ ] 公开部署用 HTTPS (前置 nginx/Caddy 反向代理)
- [ ] 定期 `git pull` 更新到最新版本

## 📜 披露政策

我们遵循 **协调披露 (Coordinated Disclosure)**:
- 修复发布前不公开漏洞细节
- 修复发布后 90 天内公开详情
- 致谢报告者 (除非希望匿名)

## 📞 联系方式

- 🐛 安全问题: GitHub Security Advisories (推荐)
- 💬 一般问题: [Discussions](https://github.com/PerfectZQ888/FIFA-WorldCup-2026-V2/discussions)
- 🐛 非安全问题: [Issues](https://github.com/PerfectZQ888/FIFA-WorldCup-2026-V2/issues)

---

🙏 感谢帮我们保持 V2 安全！
