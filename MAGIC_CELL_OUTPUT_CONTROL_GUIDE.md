# 魔法Cell输出控制功能指南

## 概述

molten-nvim现在提供了针对魔法cell（由`#%%`分隔的代码块）的精细化输出控制功能。这些新功能让您可以轻松管理特定魔法cell的虚拟文本输出和浮动窗口输出，同时也提供了全局的输出控制选项。

## 🎯 新增命令

### 1. 魔法Cell虚拟文本控制

#### `:MoltenToggleMagicCellVirtText`
切换当前魔法cell的虚拟文本输出显示。

**功能特点:**
- 自动识别cursor所在的魔法cell（由`#%%`标记分隔）
- 智能切换该魔法cell内所有molten cell的虚拟文本输出
- 包含图片在内的所有输出类型都会同步显示/隐藏
- 提供清晰的状态反馈

**使用前提:**
- 全局虚拟文本输出功能必须启用（`g:molten_virt_text_output = true`）
- cursor必须位于魔法cell内

**智能切换逻辑:**
- 如果魔法cell内有可见的虚拟输出 → 隐藏所有
- 如果魔法cell内没有可见的虚拟输出 → 显示所有

### 2. 魔法Cell浮动窗口控制

#### `:MoltenToggleMagicCellOutput`
切换当前魔法cell的浮动窗口输出显示。

**功能特点:**
- 控制魔法cell内所有molten cell的浮动窗口输出
- 支持图片、文本、错误信息等所有输出类型
- 智能检测当前状态并进行相应切换

**智能切换逻辑:**
- 如果魔法cell内有打开的浮动窗口 → 关闭所有
- 如果魔法cell内没有打开的浮动窗口 → 显示所有

### 3. 全局浮动窗口控制

#### `:MoltenToggleGlobalOutput`
全局开关所有molten kernel的浮动窗口输出。

**功能特点:**
- 控制所有kernel中所有cell的浮动窗口输出
- 跨缓冲区操作，影响所有已执行的cell
- 提供统一的输出管理体验

**智能切换逻辑:**
- 如果有任何打开的浮动窗口 → 关闭所有
- 如果没有打开的浮动窗口 → 显示所有

## 🔧 建议的键盘映射

### Lua配置
```lua
-- 魔法cell控制
vim.keymap.set('n', '<leader>mcv', ':MoltenToggleMagicCellVirtText<CR>', 
  { desc = 'Toggle magic cell virt text' })
vim.keymap.set('n', '<leader>mco', ':MoltenToggleMagicCellOutput<CR>', 
  { desc = 'Toggle magic cell output' })

-- 全局控制
vim.keymap.set('n', '<leader>mgo', ':MoltenToggleGlobalOutput<CR>', 
  { desc = 'Toggle global output' })

-- 与现有功能结合使用
vim.keymap.set('n', '<leader>mc', ':MoltenEvaluateMagicCell<CR>', 
  { desc = 'Run magic cell' })
vim.keymap.set('n', '<leader>mn', ':MoltenNextMagicCell<CR>', 
  { desc = 'Next magic cell' })
vim.keymap.set('n', '<leader>mp', ':MoltenPrevMagicCell<CR>', 
  { desc = 'Previous magic cell' })
```

### Vimscript配置
```vim
" 魔法cell控制
nnoremap <leader>mcv :MoltenToggleMagicCellVirtText<CR>
nnoremap <leader>mco :MoltenToggleMagicCellOutput<CR>

" 全局控制
nnoremap <leader>mgo :MoltenToggleGlobalOutput<CR>

" 与现有功能结合使用
nnoremap <leader>mc :MoltenEvaluateMagicCell<CR>
nnoremap <leader>mn :MoltenNextMagicCell<CR>
nnoremap <leader>mp :MoltenPrevMagicCell<CR>
```

## 📋 典型工作流程

### 基本工作流程

1. **创建魔法cell文件**
   ```python
   #%% Cell 1: 数据导入
   import pandas as pd
   import matplotlib.pyplot as plt
   data = pd.read_csv('data.csv')
   
   #%% Cell 2: 数据处理
   processed_data = data.dropna()
   print(processed_data.head())
   
   #%% Cell 3: 数据可视化
   plt.figure(figsize=(10, 6))
   plt.plot(processed_data['x'], processed_data['y'])
   plt.show()
   ```

2. **初始化和执行**
   ```vim
   :MoltenInit python3              " 初始化kernel
   :MoltenToggleGlobalVirtText      " 启用虚拟文本输出
   :MoltenEvaluateMagicCell         " 执行当前魔法cell
   ```

3. **精细化输出控制**
   ```vim
   :MoltenToggleMagicCellVirtText   " 切换当前魔法cell的虚拟文本输出
   :MoltenToggleMagicCellOutput     " 切换当前魔法cell的浮动窗口输出
   ```

### 高级控制流程

1. **批量管理输出**
   ```vim
   :MoltenToggleGlobalOutput        " 全局控制所有浮动窗口
   :MoltenToggleGlobalVirtText      " 全局控制所有虚拟文本
   ```

2. **专注模式工作流程**
   ```vim
   " 隐藏所有输出，专注于代码编辑
   :MoltenToggleGlobalOutput
   :MoltenToggleGlobalVirtText
   
   " 只显示当前魔法cell的输出
   :MoltenToggleMagicCellVirtText
   ```

3. **演示模式工作流程**
   ```vim
   " 显示所有输出用于演示
   :MoltenToggleGlobalOutput
   :MoltenToggleGlobalVirtText
   
   " 逐个魔法cell进行演示
   :MoltenNextMagicCell
   :MoltenEvaluateMagicCell
   ```

## 🎨 图片输出支持

### 自动同步功能
- **虚拟文本切换时**: 图片会与文本输出同步显示/隐藏
- **浮动窗口切换时**: 图片会在窗口中正确显示/清除
- **支持的图片格式**: matplotlib图表、PIL图片、SVG、PNG等

### 配置建议
```lua
-- 确保图片功能正常工作
vim.g.molten_image_provider = "image.nvim"  -- 或 "wezterm"
vim.g.molten_image_location = "both"        -- 虚拟文本和浮动窗口都显示
vim.g.molten_auto_image_popup = false       -- 避免自动弹出图片
```

## 🚨 故障排除

### 常见问题

**问题1:** "Cursor不在任何魔法cell中"
- **原因**: cursor位置不在`#%%`标记的代码块内
- **解决**: 确保cursor在`#%%`行和下一个`#%%`行之间（或文件末尾）

**问题2:** "当前魔法cell中没有已执行的molten cell"
- **原因**: 魔法cell内的代码还没有通过molten执行
- **解决**: 先使用`:MoltenEvaluateMagicCell`执行代码

**问题3:** "虚拟文本输出功能未启用"
- **原因**: 全局虚拟文本功能被禁用
- **解决**: 使用`:MoltenToggleGlobalVirtText`启用

**问题4:** 图片不显示或显示异常
- **原因**: 图片提供商配置问题
- **解决**: 检查`molten_image_provider`设置，确保相关插件已安装

### 状态检查命令
```vim
:MoltenVirtTextStatus              " 检查虚拟文本状态
:MoltenInfo                        " 检查molten整体状态
:checkhealth                       " 检查依赖项状态
```

## 💡 最佳实践

### 1. 工作模式建议
- **开发模式**: 启用虚拟文本输出，便于快速查看结果
- **调试模式**: 使用浮动窗口输出，便于详细查看错误信息
- **演示模式**: 根据需要切换输出显示，保持界面整洁
- **专注模式**: 隐藏所有输出，专注于代码编辑

### 2. 键盘映射建议
- 使用一致的前缀（如`<leader>m`）来组织魔法cell相关命令
- 将常用的切换命令映射到容易按的键位
- 考虑使用which-key.nvim等插件来显示可用命令

### 3. 文件组织建议
```python
#%% 配置和导入
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

#%% 数据加载
data = load_data()

#%% 数据清洗
cleaned_data = clean_data(data)

#%% 探索性数据分析
# 使用虚拟文本输出查看快速统计
print(cleaned_data.describe())

#%% 数据可视化
# 使用浮动窗口输出查看图表
plt.figure(figsize=(12, 8))
plot_data(cleaned_data)
plt.show()

#%% 模型训练
model = train_model(cleaned_data)

#%% 结果评估
evaluate_model(model, test_data)
```

### 4. 性能优化
- 对于包含大量输出的魔法cell，考虑调整`molten_virt_text_max_lines`
- 使用`molten_limit_output_chars`限制输出长度，避免性能问题
- 在不需要时及时关闭浮动窗口输出，释放资源

这些新功能让您可以更精细地控制molten-nvim的输出显示，提供了更好的交互式编程体验！
