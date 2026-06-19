# 🤝 贡献指南 (Contributing)

欢迎为 V2 项目做贡献！🎉 无论是 bug fix、新功能、文档改进还是问题反馈。

## 📋 行为准则

参与项目前请阅读 [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)。

## 🐛 报告 Bug

1. 检查 [现有 issues](https://github.com/PerfectZQ888/FIFA-WorldCup-2026-V2/issues) 避免重复
2. 使用 [Bug 报告模板](https://github.com/PerfectZQ888/FIFA-WorldCup-2026-V2/issues/new?template=bug_report.md)
3. 提供: OS / Python 版本 / 部署方式 / 复现步骤 / 错误日志

## ✨ 提议新功能

1. 开 [Discussion](https://github.com/PerfectZQ888/FIFA-WorldCup-2026-V2/discussions) 讨论
2. 达成共识后用 [Feature 模板](https://github.com/PerfectZQ888/FIFA-WorldCup-2026-V2/issues/new?template=feature_request.md) 提 issue

## 🔧 提交 PR

### 准备工作

1. **Fork** 仓库并 clone
   ```bash
   git clone https://github.com/YOUR-USERNAME/FIFA-WorldCup-2026-V2.git
   cd FIFA-WorldCup-2026-V2
   ```

2. **创建分支** (从 main)
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/issue-123
   ```

3. **本地验证** (三个 OS 都最好试一下)
   ```bash
   # Linux
   ./start.sh && curl http://localhost:8001/api/health
   
   # macOS  
   ./start.sh && curl http://localhost:8001/api/health
   
   # Windows
   start.bat && curl http://localhost:8001/api/health
   ```

### 开发规范

#### Python (后端)
- **风格**: PEP 8
- **类型注解**: 用 `pathlib.Path`、`typing` 模块
- **跨平台**: 不用 `subprocess` / 硬编码路径
- **依赖**: 不加新依赖除非必要（更新 `requirements.txt`）
- **测试**: 改了什么就测什么 (5 路由 200: `/`, `/bracket`, `/api/health`, `/api/predictions`, `/api/matches/live`)

#### JavaScript / HTML / CSS (前端)
- **风格**: 现有风格 (2 空格缩进, 单引号)
- **跨平台**: 不用 `navigator.platform` 等 OS 检测
- **URL**: 用 `window.location.origin` 而不是硬编码
- **优化**: 5 文件拆分 (index/bracket/style/accuracy/calibration), 单一 ChartManager

#### Shell 脚本
- **兼容性**: bash 3.2+ (macOS 默认)
- **跨平台**: 用 `uname -s` 检测, 不要假设 `lsof` / `systemctl` 存在
- **错误处理**: `set -e`, 端口检查要 fallback
- **权限**: 修配置前 `cp file file.bak.ts`

#### 文档
- README / DEPLOY / CHANGELOG 同步更新
- 公开仓库前**扫敏感信息** (token / 内网 IP / 邮箱)

### 提交规范

- **commit message**: 用 [Conventional Commits](https://www.conventionalcommits.org/)
  ```
  feat: 添加 xx 功能
  fix: 修复 xx bug
  docs: 更新 xx 文档
  refactor: 重构 xx 模块
  style: 格式化代码
  test: 添加测试
  chore: 杂项 (build / ci)
  ```
- **每 commit 聚焦一件事**, 不混合 fix + feat
- **大改动** 拆成多个 commit

### 提交 PR 前

- [ ] 5 路由 200 (本地验证)
- [ ] 跨 OS 测试 (如适用)
- [ ] 无新警告 / 报错
- [ ] 敏感信息扫描 0 命中
- [ ] CHANGELOG.md 更新 (如适用)
- [ ] README/DEPLOY 更新 (如适用)
- [ ] commit message 规范

### 提交流程

```bash
# 1. 推送分支
git push origin feature/your-feature

# 2. 开 PR, 用 PR 模板填写:
#    - 变更说明
#    - 关联 issue
#    - 验证清单
#    - 截图 (UI 改动)
```

## 🏷️ 发布流程 (维护者)

只有维护者能发 release:

```bash
# 1. 更新 CHANGELOG.md
# 2. 提交
git add CHANGELOG.md
git commit -m "docs: update CHANGELOG for v1.x.x"

# 3. 打 tag
git tag -a v1.x.x -m "v1.x.x - 简短描述"

# 4. 推送 (触发 GitHub Actions 自动 build + release)
git push origin main
git push origin v1.x.x
```

## 📞 联系方式

- 🐛 Bug / 功能: [Issues](https://github.com/PerfectZQ888/FIFA-WorldCup-2026-V2/issues)
- 💬 讨论: [Discussions](https://github.com/PerfectZQ888/FIFA-WorldCup-2026-V2/discussions)
- 🔒 安全问题: 见 [SECURITY.md](./SECURITY.md)

---

🙏 感谢所有贡献者！
