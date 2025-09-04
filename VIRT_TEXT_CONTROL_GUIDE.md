# Molten虚拟文本输出控制指南

## 概述

molten-nvim现在提供了强大的虚拟文本输出控制功能，让您可以实时开关、刷新和管理虚拟文本输出的显示。虚拟文本输出会在代码cell下方显示执行结果，并且在您离开cell后仍然保持可见。

## 🎯 新增命令

### 1. 全局控制命令

#### `:MoltenToggleGlobalVirtText`
全局开关虚拟文本输出功能。

**功能:**
- 切换整个molten实例的虚拟文本输出设置
- 更新全局配置变量 `g:molten_virt_text_output`
- 立即应用到所有已存在的cell输出

**效果:**
- 启用时：显示所有buffer中所有cell的虚拟文本输出
- 禁用时：清除所有虚拟文本输出

#### `:MoltenVirtTextStatus`
显示虚拟文本输出的当前状态。

**显示信息:**
- 全局设置状态（启用/禁用）
- 当前缓冲区的统计信息：总cell数、可见数、隐藏数

### 2. 缓冲区级别控制命令

#### `:MoltenToggleBufferVirtText`
切换当前缓冲区的虚拟文本输出显示。

**智能切换:**
- 如果有可见的虚拟输出 → 隐藏所有
- 如果没有可见的虚拟输出 → 显示所有

**前提条件:** 全局虚拟文本输出功能必须启用

#### `:MoltenShowAllVirtText`
强制显示当前缓冲区所有cell的虚拟文本输出。

**用途:**
- 恢复被隐藏的虚拟输出
- 确保所有执行过的cell都显示结果

#### `:MoltenHideAllVirtText`
隐藏当前缓冲区所有cell的虚拟文本输出。

**用途:**
- 清理界面，专注于代码
- 临时隐藏输出但不禁用功能

### 3. 刷新和维护命令

#### `:MoltenRefreshVirtText`
刷新所有虚拟文本输出的显示。

**适用场景:**
- 虚拟文本显示异常时
- 切换主题或配色后
- 手动同步虚拟输出状态

## 🔧 建议的键盘映射

```lua
-- 全局控制
vim.keymap.set('n', '<leader>mvt', ':MoltenToggleGlobalVirtText<CR>', { desc = 'Toggle global virt text' })
vim.keymap.set('n', '<leader>mvs', ':MoltenVirtTextStatus<CR>', { desc = 'Virt text status' })

-- 缓冲区控制
vim.keymap.set('n', '<leader>mvb', ':MoltenToggleBufferVirtText<CR>', { desc = 'Toggle buffer virt text' })
vim.keymap.set('n', '<leader>mvh', ':MoltenHideAllVirtText<CR>', { desc = 'Hide all virt text' })
vim.keymap.set('n', '<leader>mvv', ':MoltenShowAllVirtText<CR>', { desc = 'Show all virt text' })

-- 刷新
vim.keymap.set('n', '<leader>mvr', ':MoltenRefreshVirtText<CR>', { desc = 'Refresh virt text' })
```

或者使用Vimscript：

```vim
" 全局控制
nnoremap <leader>mvt :MoltenToggleGlobalVirtText<CR>
nnoremap <leader>mvs :MoltenVirtTextStatus<CR>

" 缓冲区控制
nnoremap <leader>mvb :MoltenToggleBufferVirtText<CR>
nnoremap <leader>mvh :MoltenHideAllVirtText<CR>
nnoremap <leader>mvv :MoltenShowAllVirtText<CR>

" 刷新
nnoremap <leader>mvr :MoltenRefreshVirtText<CR>
```

## 📋 常用工作流程

### 基本工作流程

1. **启用虚拟文本输出**
   ```vim
   :MoltenToggleGlobalVirtText
   ```

2. **执行代码并查看输出**
   ```vim
   :MoltenEvaluateLine  " 或其他执行命令
   ```

3. **管理输出显示**
   ```vim
   :MoltenToggleBufferVirtText  " 切换当前缓冲区的显示
   ```

### 高级控制流程

1. **检查当前状态**
   ```vim
   :MoltenVirtTextStatus
   ```

2. **精确控制显示**
   ```vim
   :MoltenHideAllVirtText    " 隐藏所有
   :MoltenShowAllVirtText    " 显示所有
   ```

3. **解决显示问题**
   ```vim
   :MoltenRefreshVirtText    " 刷新显示
   ```

## ⚙️ 配置选项

### 相关的全局配置变量

```lua
-- 启用虚拟文本输出
vim.g.molten_virt_text_output = true

-- 虚拟文本最大显示行数
vim.g.molten_virt_text_max_lines = 12

-- 虚拟文本位置微调
vim.g.molten_virt_lines_off_by_1 = false

-- 输出显示设置
vim.g.molten_output_show_exec_time = true
vim.g.molten_wrap_output = true
```

### 运行时动态更新

```lua
-- 使用MoltenUpdateOption动态更新设置
vim.fn.MoltenUpdateOption("virt_text_output", true)
vim.fn.MoltenUpdateOption("virt_text_max_lines", 20)
```

## 🚨 故障排除

### 常见问题

**问题1:** "虚拟文本输出功能未启用"
**解决:** 使用 `:MoltenToggleGlobalVirtText` 启用全局功能

**问题2:** 虚拟文本显示不正确或位置错误
**解决:** 使用 `:MoltenRefreshVirtText` 刷新显示

**问题3:** 部分cell的虚拟输出不显示
**解决:** 使用 `:MoltenShowAllVirtText` 强制显示所有输出

**问题4:** 虚拟文本过多影响阅读
**解决:** 使用 `:MoltenHideAllVirtText` 临时隐藏，或调整 `molten_virt_text_max_lines`

### 状态检查

使用 `:MoltenVirtTextStatus` 命令可以快速了解：
- 全局功能是否启用
- 当前缓冲区有多少cell
- 有多少输出可见/隐藏

### 重置到默认状态

如果遇到问题，可以按以下步骤重置：

1. 禁用虚拟文本输出：`:MoltenToggleGlobalVirtText`（如果当前是启用状态）
2. 清除所有虚拟输出：`:MoltenHideAllVirtText`
3. 重新启用：`:MoltenToggleGlobalVirtText`
4. 刷新显示：`:MoltenRefreshVirtText`

## 🎨 与现有功能的协调

### 与浮动窗口输出的关系

- 虚拟文本输出和浮动窗口输出可以同时使用
- 当启用虚拟文本输出时，浮动窗口不会自动打开
- 可以手动使用 `:MoltenShowOutput` 显示浮动窗口

### 与cell高亮的配合

- 虚拟文本输出不影响cell高亮功能
- 选中cell时仍然会显示高亮边框
- 虚拟文本会显示在cell下方，不覆盖代码

### 与其他molten命令的兼容性

- 所有现有的molten命令都完全兼容
- `:MoltenToggleVirtual` 仍然可以用于切换单个cell的虚拟输出
- 新的全局控制命令提供了更强大的批量管理能力

## 💡 最佳实践

1. **工作开始时**：使用 `:MoltenVirtTextStatus` 检查状态
2. **代码开发时**：启用虚拟文本输出以便查看结果
3. **代码审查时**：可能需要隐藏虚拟输出以专注于代码
4. **演示时**：根据需要切换虚拟输出显示
5. **遇到问题时**：首先尝试 `:MoltenRefreshVirtText`

这些新功能让您可以更灵活地控制molten-nvim的虚拟文本输出，提升您的Jupyter-style编程体验！
