# 垂直层级Outline功能使用指南

## 概述

垂直层级Outline是molten-nvim的一个全新功能，提供了类似IDE的多层级代码导航体验。它将代码结构分解为多个垂直排列的窗口，从左到右显示不同的调用层级，支持hjkl键位导航。

## ✨ 功能特性

### 🔍 多层级显示
- **第一层：Magic Cells** - 显示所有`#%%`分隔的代码块
- **第二层：Functions/Classes** - 显示选中cell中的函数和类
- **第三层：Methods** - 显示选中类的方法
- **第四层：Variables** - 显示相关变量（可扩展）

### 🎯 垂直窗口布局
- **从左到右排列**：每个层级占用一个独立窗口
- **自动调整大小**：根据屏幕宽度自动计算窗口宽度
- **层级关联**：选择上层项目时，下层窗口自动更新内容

### 🚀 vim键位导航
- **h**：向左移动到上一层级
- **l**：向右移动到下一层级
- **j**：在当前层级向下移动
- **k**：在当前层级向上移动
- **回车**：选择当前项目并跳转到代码位置
- **q/Esc**：关闭垂直outline

### 🔗 LSP集成
- **符号识别**：使用LSP获取准确的函数、类、变量信息
- **类型检测**：支持多种符号类型（函数、类、方法、变量等）
- **兼容性**：LSP不可用时自动降级为基础解析

## 🛠 新增命令

### 主要命令

#### `:MoltenShowVerticalOutline`
显示垂直层级outline。

**功能：**
- 解析当前文件中的所有magic cell
- 创建多个垂直排列的浮动窗口
- 显示层级化的代码结构

#### `:MoltenHideVerticalOutline`
隐藏垂直outline窗口。

#### `:MoltenToggleVerticalOutline`
切换垂直outline窗口的显示/隐藏状态。

## 📖 使用方法

### 基本使用流程

1. **打开Python文件**：确保文件包含`#%%`魔法命令
2. **显示垂直outline**：运行`:MoltenShowVerticalOutline`
3. **导航浏览**：使用hjkl键位在不同层级间移动
4. **选择跳转**：按回车键跳转到选中的代码位置
5. **关闭outline**：按q或Esc关闭

### 导航示例

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Cells     │  │ Functions   │  │  Methods    │
├─────────────┤  ├─────────────┤  ├─────────────┤
│📘 [1] 导入   │  │🔧 process() │  │⚙️ __init__  │
│📘 [2] 数据   │  │🏛️ DataModel │  │⚙️ validate  │
│📘 [3] 处理   │◄─│🔧 analyze() │  │⚙️ save      │
│📘 [4] 输出   │  │📝 config    │  └─────────────┘
└─────────────┘  └─────────────┘
      ▲               ▲               ▲
      h               当前位置          l
```

### 键位操作详解

- **h（左移）**：从Functions层移动到Cells层
- **l（右移）**：从Cells层移动到Functions层，从Functions层移动到Methods层
- **j/k（上下）**：在当前层级内移动，同时更新右侧相关层级
- **回车**：跳转到选中项目的代码位置并关闭outline
- **q/Esc**：直接关闭所有outline窗口

## 🎨 视觉效果

### 图标说明
- 📘 Magic Cell
- 🔧 函数 (Function)
- 🏛️ 类 (Class)  
- ⚙️ 方法 (Method)
- 📝 变量 (Variable)

### 窗口样式
- **边框**：圆角边框，美观现代
- **标题**：每个窗口显示层级名称和编号
- **高亮**：当前行高亮显示，便于识别位置
- **大小**：自适应屏幕宽度，最小宽度25列

## ⚙️ 配置建议

### 推荐键位映射

```lua
-- 垂直outline快捷键
vim.keymap.set('n', '<leader>ov', ':MoltenToggleVerticalOutline<CR>', 
  { desc = 'Toggle Vertical Outline', silent = true })
vim.keymap.set('n', '<leader>oV', ':MoltenShowVerticalOutline<CR>', 
  { desc = 'Show Vertical Outline', silent = true })
```

### LSP配置

确保您的Python LSP配置正确，以获得最佳的符号识别效果：

```lua
-- 示例：pyright配置
require('lspconfig').pyright.setup({
    settings = {
        python = {
            analysis = {
                typeCheckingMode = "basic",
                symbolsHierarchyDepthLimit = 10,
            }
        }
    }
})
```

## 🔧 高级功能

### 自动更新
- 当您在不同层级间移动时，相关的子层级会自动更新
- 选择不同的cell时，Functions层会显示该cell内的函数
- 选择不同的类时，Methods层会显示该类的方法

### 智能跳转
- 跳转后自动居中显示目标代码
- 保持原有窗口布局不变
- 支持跨文件跳转（如果符号在其他文件中）

## 🐛 故障排除

### 常见问题

1. **LSP符号不显示**
   - 确保LSP服务器正在运行
   - 检查当前文件类型是否支持LSP
   - 降级使用基础解析功能

2. **窗口显示异常**
   - 检查终端宽度是否足够（建议至少80列）
   - 尝试重新打开outline

3. **键位不响应**
   - 确保焦点在outline窗口中
   - 检查是否有其他插件冲突

### 调试信息

如果遇到问题，可以查看molten的日志：
```vim
:messages
```

## 🚀 性能优化

- 大文件时自动限制解析深度
- 智能缓存解析结果
- 异步LSP查询，不阻塞界面

## 🔮 未来计划

- [ ] 支持更多编程语言
- [ ] 添加搜索和过滤功能
- [ ] 支持自定义层级配置
- [ ] 集成调用图显示
- [ ] 支持代码折叠预览

---

垂直层级Outline功能让您能够像使用现代IDE一样浏览和导航Python代码结构，大大提升了在Neovim中进行数据科学和机器学习开发的效率！
