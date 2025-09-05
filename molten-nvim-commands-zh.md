# Molten-nvim 命令文档

## 目录

1. [概述](#概述)
2. [基础命令](#基础命令)
3. [代码执行命令](#代码执行命令)
4. [魔法Cell命令](#魔法cell命令)
5. [虚拟文本输出控制命令](#虚拟文本输出控制命令)
6. [输出控制命令](#输出控制命令)
7. [导航命令](#导航命令)
8. [文件操作命令](#文件操作命令)
9. [Vim函数](#vim函数)
10. [配置选项](#配置选项)
11. [自动命令](#自动命令)
12. [高亮组](#高亮组)
13. [键盘映射建议](#键盘映射建议)

## 概述

Molten是一个用于在Neovim中交互式运行代码的插件，基于Jupyter内核。它提供了类似REPL的体验和类似笔记本的体验。本文档详细介绍了molten-nvim提供的所有命令、函数和配置选项。

## 基础命令

### `:MoltenInfo`
**参数：** 无  
**描述：** 显示插件状态信息，包括初始化状态、可用内核和运行中的内核

### `:MoltenInit [shared] [kernel]`
**参数：**
- `shared`（可选）：使用已运行的内核
- `kernel`（可选）：指定内核名称

**描述：** 为当前缓冲区初始化内核
- 如果指定`shared`，将使用已运行的内核
- 如果未指定内核，将提示用户选择

**示例：**
```vim
:MoltenInit                    " 提示选择内核
:MoltenInit python3           " 初始化python3内核
:MoltenInit shared python3    " 共享已有的python3内核
```

### `:MoltenDeinit`
**参数：** 无  
**描述：** 取消初始化当前缓冲区的运行时和molten实例（在vim关闭/缓冲区卸载时自动调用）

## 代码执行命令

### `:MoltenEvaluateLine [kernel]`
**参数：** `kernel`（可选）- 内核名称  
**描述：** 执行当前行

### `:MoltenEvaluateVisual [kernel]`
**参数：** `kernel`（可选）- 内核名称  
**描述：** 执行可视选择的代码（**不能使用范围调用！**）

**注意：** 必须在可视模式下使用

### `:MoltenEvaluateOperator [kernel]`
**参数：** `kernel`（可选）- 内核名称  
**描述：** 执行通过操作符选择的文本

**使用方法：** 设置为操作符函数，通常映射到按键

### `:MoltenEvaluateArgument [kernel] code`
**参数：**
- `kernel`（可选）- 内核名称
- `code` - 要执行的代码

**描述：** 在指定内核中执行给定的代码

### `:MoltenReevaluateCell`
**参数：** 无  
**描述：** 使用原始内核重新评估活动cell（包括新代码）

### `:MoltenReevaluateAll`
**参数：** 无  
**描述：** 重新评估当前缓冲区中的所有cell

## 魔法Cell命令

### `:MoltenEvaluateMagicCell [kernel]`
**参数：** `kernel`（可选）- 内核名称  
**描述：** 运行光标当前所在的魔法cell（由`#%%`分隔的代码块）

**特点：**
- 自动跳过`#%%`魔法命令行，只执行实际代码
- 如果光标不在任何魔法cell中，显示错误信息
- 与现有的molten输出系统完全兼容

### `:MoltenNextMagicCell`
**参数：** 无  
**描述：** 跳转到下一个魔法cell的开始位置

**特点：**
- 如果当前在最后一个cell，会循环跳转到第一个cell
- 如果没有找到魔法cell，显示警告信息

### `:MoltenPrevMagicCell`
**参数：** 无  
**描述：** 跳转到上一个魔法cell的开始位置

**特点：**
- 如果当前在第一个cell，会循环跳转到最后一个cell
- 如果没有找到魔法cell，显示警告信息

## 虚拟文本输出控制命令

### `:MoltenToggleGlobalVirtText`
**参数：** 无  
**描述：** 全局开关虚拟文本输出功能

**功能：**
- 切换整个molten实例的虚拟文本输出设置
- 更新全局配置变量`g:molten_virt_text_output`
- 立即应用到所有已存在的cell输出

### `:MoltenVirtTextStatus`
**参数：** 无  
**描述：** 显示虚拟文本输出的当前状态

**显示信息：**
- 全局设置状态（启用/禁用）
- 当前缓冲区的统计信息：总cell数、可见数、隐藏数

### `:MoltenToggleBufferVirtText`
**参数：** 无  
**描述：** 切换当前缓冲区的虚拟文本输出显示

**智能切换：**
- 如果有可见的虚拟输出 → 隐藏所有
- 如果没有可见的虚拟输出 → 显示所有

### `:MoltenShowAllVirtText`
**参数：** 无  
**描述：** 强制显示当前缓冲区所有cell的虚拟文本输出

### `:MoltenHideAllVirtText`
**参数：** 无  
**描述：** 隐藏当前缓冲区所有cell的虚拟文本输出

### `:MoltenRefreshVirtText`
**参数：** 无  
**描述：** 刷新所有虚拟文本输出的显示

**适用场景：**
- 虚拟文本显示异常时
- 切换主题或配色后
- 手动同步虚拟输出状态

### `:MoltenToggleMagicCellVirtText`
**参数：** 无  
**描述：** 切换当前魔法cell的虚拟文本输出显示

### `:MoltenToggleVirtual[!]`
**参数：** `!`（可选）- 切换所有cell  
**描述：** 切换光标下cell的虚拟文本输出
- 使用`!`时切换当前缓冲区的所有cell

## 输出控制命令

### `:MoltenShowOutput`
**参数：** 无  
**描述：** 显示活动cell的输出窗口

### `:MoltenHideOutput`
**参数：** 无  
**描述：** 隐藏当前打开的输出窗口

### `:MoltenEnterOutput`
**参数：** 无  
**描述：** 进入活动cell的输出窗口（如果未打开则打开但不进入）

**注意：** 必须使用`noautocmd`调用

### `:MoltenOpenInBrowser`
**参数：** 无  
**描述：** 在浏览器中打开当前输出（目前仅支持`text/html`输出）

### `:MoltenImagePopup`
**参数：** 无  
**描述：** 使用Python的`Image.show()`打开当前输出中的图像

### `:MoltenToggleMagicCellOutput`
**参数：** 无  
**描述：** 切换当前魔法cell的浮动窗口输出显示

### `:MoltenToggleGlobalOutput`
**参数：** 无  
**描述：** 全局开关浮动窗口输出功能

## 导航命令

### `:MoltenNext [n]`
**参数：** `n`（可选）- 跳转的cell数量，默认为1  
**描述：** 跳转到下一个代码cell，或跳转n个代码cell

**特点：**
- 值可以换行
- 负值向后移动

### `:MoltenPrev [n]`
**参数：** `n`（可选）- 跳转的cell数量，默认为1  
**描述：** 类似`MoltenNext`但向后移动

### `:MoltenGoto [n]`
**参数：** `n`（可选）- cell编号，默认为1（从1开始索引）  
**描述：** 跳转到第n个代码cell

## 文件操作命令

### `:MoltenSave [path] [kernel]`
**参数：**
- `path`（可选）- 保存路径
- `kernel`（可选）- 内核名称

**描述：** 将当前cell和评估输出保存到JSON文件
- 如果未指定路径，使用`g:molten_save_path`
- 目前每个文件只保存一个内核

### `:MoltenLoad [shared] [path]`
**参数：**
- `shared`（可选）- 使用共享内核
- `path`（可选）- 加载路径

**描述：** 从JSON文件加载cell位置和输出
- 如果指定`shared`，缓冲区共享已运行的内核

### `:MoltenExportOutput [!] [path] [kernel]`
**参数：**
- `!`（可选）- 强制导出
- `path`（可选）- 导出路径
- `kernel`（可选）- 内核名称

**描述：** 将输出导出到Jupyter notebook（`.ipynb`）文件

### `:MoltenImportOutput [path] [kernel]`
**参数：**
- `path`（可选）- 导入路径
- `kernel`（可选）- 内核名称

**描述：** 从Jupyter notebook（`.ipynb`）导入输出

## 其他命令

### `:MoltenDelete [!]`
**参数：** `!`（可选）- 删除所有cell  
**描述：** 删除活动cell
- 使用`!`时删除当前缓冲区中的所有cell

### `:MoltenInterrupt [kernel]`
**参数：** `kernel`（可选）- 内核名称  
**描述：** 向内核发送键盘中断，停止当前运行的代码

### `:MoltenRestart [!] [kernel]`
**参数：**
- `!`（可选）- 删除输出
- `kernel`（可选）- 内核名称

**描述：** 关闭并重启内核
- 使用`!`时删除所有输出

## Vim函数

### `MoltenEvaluateRange(start_line, end_line, [start_col, end_col])`
**描述：** 评估给定行号和列号之间的代码

**参数：**
- `start_line` - 开始行号（1-based）
- `end_line` - 结束行号（1-based）
- `start_col`（可选）- 开始列号
- `end_col`（可选）- 结束列号

**特点：**
- 范围包含边界，索引从1开始
- 列号可选，省略时捕获整行
- 传递`-1`作为`end_col`使用行的最后一列
- 传递`0`作为其他位置使用最后一行/列

**示例：**
```lua
-- 运行第1到23行（包含）：
vim.fn.MoltenEvaluateRange(1, 23)

-- 运行从第1行第4列开始，到第3行最后一列结束的代码
vim.fn.MoltenEvaluateRange(1, 3, 4, -1)

-- 使用python3内核运行第1到23行
vim.fn.MoltenEvaluateRange("python3", 1, 23)
```

### `MoltenUpdateOption(option, value)`
**描述：** 更新配置值，新值立即生效

**参数：**
- `option` - 选项名称（可以带或不带"molten"前缀）
- `value` - 新值

**示例：**
```lua
-- 这两个是相同的！
vim.fn.MoltenUpdateOption("auto_open_output", true)
vim.fn.MoltenUpdateOption("molten_auto_open_output", true)
```

### `MoltenRunningKernels(buffer_local)`
**描述：** 返回当前运行的内核ID列表

**参数：**
- `buffer_local` - 为true时只返回当前缓冲区的内核，否则返回所有运行的内核ID

**示例：**
```lua
vim.fn.MoltenRunningKernels(true)  -- 列出缓冲区本地内核ID
vim.fn.MoltenRunningKernels(false) -- 列出所有内核ID
```

### `MoltenAvailableKernels()`
**描述：** 返回molten知道的内核名称列表

**示例：**
```lua
vim.fn.MoltenAvailableKernels()
```

### `MoltenDefineCell(start_line, end_line, [kernel])`
**描述：** 在当前缓冲区中创建与内核关联的代码cell

**参数：**
- `start_line` - 开始行号
- `end_line` - 结束行号
- `kernel`（可选）- 内核名称

**注意：** 不运行代码或创建/打开输出窗口

**示例：**
```lua
-- 创建从第5行到第10行与python3内核关联的cell
vim.fn.MoltenDefineCell(5, 10, 'python3')
```

## 配置选项

以下是所有可用的配置变量，默认值用括号标出：

### 图像相关
- `g:molten_auto_image_popup`: `true` | (`false`) - 自动弹出图像输出
- `g:molten_image_location`: (`"both"`) | `"float"` | `"virt"` - 图像显示位置
- `g:molten_image_provider`: (`"none"`) | `"image.nvim"` | `"wezterm"` - 图像提供者

### 输出相关
- `g:molten_auto_open_output`: (`true`) | `false` - 自动打开浮动输出窗口
- `g:molten_virt_text_output`: `true` | (`false`) - 显示虚拟文本输出
- `g:molten_virt_text_max_lines`: (`12`) | int - 虚拟文本最大行数
- `g:molten_wrap_output`: `true` | (`false`) - 包装输出文本
- `g:molten_limit_output_chars`: (`1000000`) | int - 输出字符限制

### 窗口相关
- `g:molten_output_win_border`: (`{ "", "━", "", "" }`) - 输出窗口边框
- `g:molten_output_win_max_height`: (`999999`) | int - 输出窗口最大高度
- `g:molten_output_win_max_width`: (`999999`) | int - 输出窗口最大宽度
- `g:molten_output_win_cover_gutter`: (`true`) | `false` - 输出窗口是否覆盖行号列
- `g:molten_output_win_hide_on_leave`: (`true`) | `false` - 离开后隐藏输出窗口
- `g:molten_output_win_style`: (`false`) | `"minimal"` - 输出窗口样式
- `g:molten_output_win_zindex`: (`50`) | int - 输出窗口层级

### 行为相关
- `g:molten_auto_init_behavior`: `"raise"` | (`"init"`) - 自动初始化行为
- `g:molten_enter_output_behavior`: (`"open_then_enter"`) | `"open_and_enter"` | `"no_open"` - 进入输出行为
- `g:molten_tick_rate`: (`500`) | int - 更新频率（毫秒）

### 其他
- `g:molten_copy_output`: `true` | (`false`) - 自动复制输出到剪贴板
- `g:molten_save_path`: (`stdpath("data").."/molten"`) - 保存路径
- `g:molten_open_cmd`: (`nil`) - 打开命令

## 自动命令

Molten提供以下`User`自动命令用于进一步自定义：

- `MoltenInitPre`: 在`MoltenInit`初始化之前运行
- `MoltenInitPost`: 在`MoltenInit`初始化之后运行
- `MoltenDeinitPre`: 在`MoltenDeinit`去初始化之前运行
- `MoltenDeinitPost`: 在`MoltenDeinit`去初始化之后运行
- `MoltenKernelReady`: 内核首次准备就绪时运行，`data`字段包含`kernel_id`

### 使用示例

```lua
vim.api.nvim_create_autocmd("User", {
  pattern = "MoltenInitPost",
  callback = function()
    vim.keymap.set("v", "<localleader>r", ":<C-u>MoltenEvaluateVisual<CR>gv",
      { desc = "execute visual selection", buffer = true, silent = true })
    -- ... 更多映射
  end,
})

-- 获取内核ID
vim.api.nvim_create_autocmd("User", {
  pattern = "MoltenKernelReady",
  callback = function(e)
    print("Kernel id: " .. e.data.kernel_id)
  end
})
```

## 高亮组

可以自定义以下高亮组：

- `MoltenOutputBorder` = `FloatBorder`: 默认输出窗口边框
- `MoltenOutputBorderFail` = `MoltenOutputBorder`: 失败输出窗口边框
- `MoltenOutputBorderSuccess` = `MoltenOutputBorder`: 成功运行输出窗口边框
- `MoltenOutputWin` = `NormalFloat`: 输出窗口内部
- `MoltenOutputWinNC` = `MoltenOutputWin`: "非当前"输出窗口
- `MoltenOutputFooter` = `FloatFooter`: "x more lines"文本
- `MoltenCell` = `CursorLine`: 构成cell的代码
- `MoltenVirtualText` = `Comment`: 渲染为虚拟文本的输出

### 自定义高亮

```lua
-- 使用link选项链接到配色方案的颜色
vim.api.nvim_set_hl(0, "MoltenOutputBorder", { link = "FloatBorder" })
```

## 键盘映射建议

### 最小建议映射

```lua
vim.keymap.set("n", "<localleader>mi", ":MoltenInit<CR>",
    { silent = true, desc = "Initialize the plugin" })
vim.keymap.set("n", "<localleader>e", ":MoltenEvaluateOperator<CR>",
    { silent = true, desc = "run operator selection" })
vim.keymap.set("n", "<localleader>rl", ":MoltenEvaluateLine<CR>",
    { silent = true, desc = "evaluate line" })
vim.keymap.set("n", "<localleader>rr", ":MoltenReevaluateCell<CR>",
    { silent = true, desc = "re-evaluate cell" })
vim.keymap.set("v", "<localleader>r", ":<C-u>MoltenEvaluateVisual<CR>gv",
    { silent = true, desc = "evaluate visual selection" })
```

### 其他示例映射

```lua
-- 基础操作
vim.keymap.set("n", "<localleader>rd", ":MoltenDelete<CR>",
    { silent = true, desc = "molten delete cell" })
vim.keymap.set("n", "<localleader>oh", ":MoltenHideOutput<CR>",
    { silent = true, desc = "hide output" })
vim.keymap.set("n", "<localleader>os", ":noautocmd MoltenEnterOutput<CR>",
    { silent = true, desc = "show/enter output" })

-- 魔法cell操作
vim.keymap.set('n', '<leader>mc', ':MoltenEvaluateMagicCell<CR>', 
    { desc = 'Run magic cell' })
vim.keymap.set('n', '<leader>mn', ':MoltenNextMagicCell<CR>', 
    { desc = 'Next magic cell' })
vim.keymap.set('n', '<leader>mp', ':MoltenPrevMagicCell<CR>', 
    { desc = 'Previous magic cell' })

-- 虚拟文本控制
vim.keymap.set('n', '<leader>mvt', ':MoltenToggleGlobalVirtText<CR>', 
    { desc = 'Toggle global virt text' })
vim.keymap.set('n', '<leader>mvs', ':MoltenVirtTextStatus<CR>', 
    { desc = 'Virt text status' })
vim.keymap.set('n', '<leader>mvb', ':MoltenToggleBufferVirtText<CR>', 
    { desc = 'Toggle buffer virt text' })
vim.keymap.set('n', '<leader>mvr', ':MoltenRefreshVirtText<CR>', 
    { desc = 'Refresh virt text' })
```

## 状态行集成

Molten提供了一些函数用于在状态行中显示信息：

```lua
require('molten.status').initialized() -- "Molten"或""基于初始化信息
require('molten.status').kernels()     -- "kernel1 kernel2"附加到缓冲区的内核列表或""
require('molten.status').all_kernels() -- 与kernels相同，但显示所有内核
```

## 支持的输出类型

Molten当前处理以下MIME类型：

- `text/plain`: 纯文本，在输出窗口缓冲区中显示为文本
- `image/*`: 任何图像MIME类型，发送到`image.nvim`渲染
- `application/vnd.plotly.v1+json`: Plotly图形，使用Plotly + Kaleido渲染为PNG
- `text/latex`: LaTeX公式，使用pnglatex渲染为PNG
- `text/html`: 通过`:MoltenOpenInBrowser`命令在浏览器中显示

---

*此文档基于molten-nvim项目的源代码和README文件生成。如有疑问或需要更多信息，请参考项目的官方文档或源代码。*
