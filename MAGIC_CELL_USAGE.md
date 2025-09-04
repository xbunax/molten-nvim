# 魔法Cell功能使用指南

## 概述

molten-nvim现在支持识别和运行由`#%%`魔法命令分隔的代码cell。这个功能让您可以像在Jupyter Notebook中一样，将Python文件分成多个可独立运行的代码块。

## 魔法命令格式

使用`#%%`来标记一个新的cell的开始。每个cell从`#%%`行开始，到下一个`#%%`行（或文件末尾）结束。

```python
#%% Cell 1: 数据导入
import pandas as pd
import numpy as np

#%% Cell 2: 数据处理  
data = pd.read_csv('data.csv')
processed_data = data.dropna()

#%% Cell 3: 数据分析
result = processed_data.describe()
print(result)
```

## 新增命令

### 1. `:MoltenEvaluateMagicCell`
运行cursor当前所在的魔法cell中的代码。

**用法:**
- `:MoltenEvaluateMagicCell` - 自动选择kernel或提示选择
- `:MoltenEvaluateMagicCell python3` - 使用指定的kernel

**特点:**
- 自动跳过`#%%`魔法命令行，只执行实际的代码
- 如果cursor不在任何魔法cell中，会显示错误信息
- 与现有的molten输出系统完全兼容

### 2. `:MoltenNextMagicCell`
跳转到下一个魔法cell的开始位置。

**特点:**
- 如果当前在最后一个cell，会循环跳转到第一个cell
- 如果没有找到魔法cell，会显示警告信息

### 3. `:MoltenPrevMagicCell`
跳转到上一个魔法cell的开始位置。

**特点:**
- 如果当前在第一个cell，会循环跳转到最后一个cell
- 如果没有找到魔法cell，会显示警告信息

## 建议的键盘映射

在您的Neovim配置中添加以下键盘映射：

```lua
-- 运行当前魔法cell
vim.keymap.set('n', '<leader>mc', ':MoltenEvaluateMagicCell<CR>', { desc = 'Run magic cell' })

-- 在魔法cell之间导航
vim.keymap.set('n', '<leader>mn', ':MoltenNextMagicCell<CR>', { desc = 'Next magic cell' })
vim.keymap.set('n', '<leader>mp', ':MoltenPrevMagicCell<CR>', { desc = 'Previous magic cell' })
```

或者使用Vimscript：

```vim
" 运行当前魔法cell
nnoremap <leader>mc :MoltenEvaluateMagicCell<CR>

" 在魔法cell之间导航
nnoremap <leader>mn :MoltenNextMagicCell<CR>
nnoremap <leader>mp :MoltenPrevMagicCell<CR>
```

## 使用流程

1. **创建文件**: 创建一个Python文件，使用`#%%`来分隔不同的代码块
2. **初始化kernel**: 使用`:MoltenInit python3`（或其他kernel）初始化molten
3. **导航**: 使用`:MoltenNextMagicCell`和`:MoltenPrevMagicCell`在cell之间移动
4. **运行**: 将cursor放在要运行的cell中，使用`:MoltenEvaluateMagicCell`运行代码
5. **查看输出**: 输出会显示在molten的输出窗口中，就像其他molten命令一样

## 示例文件

查看`magic_cell_example.py`文件以获得完整的使用示例。

## 与现有功能的兼容性

- 魔法cell功能与现有的molten功能完全兼容
- 您仍然可以使用`:MoltenEvaluateVisual`、`:MoltenEvaluateLine`等命令
- 输出显示、kernel管理等功能保持不变
- 魔法cell和手动创建的cell可以在同一个文件中共存

## 注意事项

- `#%%`必须在行的开头（可以有前导空格）
- 魔法命令行本身不会被执行，只执行cell中的实际代码
- 如果cell中没有可执行的代码（只有`#%%`行），会显示警告
- 确保在运行魔法cell之前已经初始化了适当的kernel

## 故障排除

**问题**: "Cursor不在任何魔法cell中"
**解决**: 确保您的cursor位于`#%%`行和下一个`#%%`行之间，或者在最后一个`#%%`行之后

**问题**: "当前缓冲区中没有找到魔法cell"
**解决**: 检查您的文件是否包含`#%%`标记，确保格式正确

**问题**: "魔法cell中没有可执行的代码"
**解决**: 在`#%%`行下面添加一些Python代码
