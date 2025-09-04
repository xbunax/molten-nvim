# molten-nvim HTTPS连接设置指南

## 概述

这个修改版本的molten-nvim支持通过HTTPS连接远程Jupyter Server，包括对自签名证书的支持。

## 主要改进

### 🔧 核心修复
1. **WebSocket协议自动适配**: 自动根据输入URL选择`ws://`或`wss://`协议
2. **SSL证书支持**: 支持自签名证书，默认不验证证书
3. **配置选项**: 添加`molten_verify_ssl`配置选项

### 🆕 新增功能
- 完整的HTTPS支持
- 自签名证书处理
- SSL验证配置选项

## 快速开始

### 1. 基本配置

在你的Neovim配置中添加：

```lua
-- 基本molten配置
vim.g.molten_image_provider = "image.nvim"
vim.g.molten_output_win_max_height = 20

-- HTTPS相关配置
vim.g.molten_verify_ssl = false  -- 允许自签名证书（推荐）
-- vim.g.molten_verify_ssl = true   -- 严格验证证书（生产环境）
```

### 2. 连接HTTPS Jupyter Server

#### 使用token认证
```vim
:MoltenInit https://your-server.com:8888?token=your_jupyter_token
```

#### 连接本地HTTPS服务器
```vim
:MoltenInit https://localhost:8888?token=your_token
```

#### 连接自签名证书服务器
```vim
" 确保设置了 molten_verify_ssl = false
:MoltenInit https://self-signed-server.com:8888?token=your_token
```

## 配置选项

### molten_verify_ssl

控制SSL证书验证行为：

```lua
-- 不验证SSL证书（默认，推荐用于开发环境）
vim.g.molten_verify_ssl = false

-- 严格验证SSL证书（推荐用于生产环境）
vim.g.molten_verify_ssl = true
```

## 测试连接

使用提供的测试脚本验证连接：

```bash
python test_https_connection.py "https://your-server.com:8888?token=your_token"
```

## 故障排除

### 常见问题

#### 1. 连接超时
- 检查防火墙设置
- 确认Jupyter Server正在运行
- 验证URL和端口是否正确

#### 2. SSL证书错误
```
SSL: CERTIFICATE_VERIFY_FAILED
```
**解决方案**: 设置`vim.g.molten_verify_ssl = false`

#### 3. WebSocket连接失败
```
WebSocket connection failed
```
**解决方案**: 
- 确认Jupyter Server支持WebSocket
- 检查代理设置

#### 4. 认证失败
```
401 Unauthorized
```
**解决方案**:
- 验证token是否正确
- 确认token没有过期

### 调试步骤

1. **验证Jupyter Server状态**:
   ```bash
   curl -k https://your-server.com:8888/api/kernels
   ```

2. **检查token**:
   ```bash
   curl -k -H "Authorization: token your_token" https://your-server.com:8888/api/kernels
   ```

3. **测试WebSocket连接**:
   使用浏览器开发者工具检查WebSocket连接

## 安全建议

### 开发环境
- 使用`molten_verify_ssl = false`以支持自签名证书
- 确保网络环境安全

### 生产环境
- 使用`molten_verify_ssl = true`
- 使用由受信任CA签发的证书
- 定期更新token

## 兼容性

- ✅ 支持HTTP连接（向后兼容）
- ✅ 支持HTTPS连接（新功能）
- ✅ 支持自签名证书
- ✅ 支持token认证
- ✅ 兼容现有配置

## 技术实现细节

### WebSocket协议选择
```python
# 自动根据HTTP协议选择WebSocket协议
ws_scheme = "wss" if parsed_url.scheme == "https" else "ws"
```

### SSL配置
```python
# 自签名证书支持
sslopt = {
    "cert_reqs": ssl.CERT_NONE,
    "check_hostname": False,
} if not verify_ssl else None
```

## 贡献

如果遇到问题或有改进建议，欢迎：
1. 提交Issue
2. 创建Pull Request
3. 参与讨论
