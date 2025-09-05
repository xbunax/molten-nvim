# Magic Cell Outline功能使用指南

## 概述

Molten-nvim现在支持强大的Magic Cell Outline功能，提供基于`#%%`魔法命令的代码大纲预览和智能导航。这个功能类似于IDE中的代码大纲视图，让您可以快速浏览和导航Python文件中的magic cell结构。

## ✨ 新功能特性

### 🔍 智能代码解析
- **Magic Cell识别**：自动识别`#%%`分隔的代码块
- **函数和类解析**：使用AST解析器提取函数、类、方法定义
- **层级结构显示**：展示代码的层次结构关系
- **语法错误容错**：即使代码有语法错误也能提供基本的outline

### 🎯 可视化大纲
- **浮动窗口显示**：在编辑器右侧显示大纲窗口
- **图标化界面**：使用emoji图标区分不同类型的代码元素
- **语法高亮**：不同类型的代码元素使用不同颜色高亮
- **实时更新**：代码修改时自动刷新大纲

### 🚀 快速导航
- **点击跳转**：在大纲窗口中点击项目直接跳转到对应代码
- **键盘导航**：支持键盘快捷键进行快速导航
- **智能搜索**：支持按编号或名称跳转到指定cell

## 🛠 新增命令

### 大纲显示命令

#### `:MoltenShowOutline`
显示当前缓冲区的magic cell outline。

**功能：**
- 解析当前文件中的所有magic cell
- 分析每个cell内的函数和类定义
- 在右侧浮动窗口显示层级结构

#### `:MoltenHideOutline`
隐藏outline窗口。

#### `:MoltenToggleOutline`
切换outline窗口的显示/隐藏状态。

### 导航命令

#### `:MoltenGotoMagicCell <target>`
跳转到指定的magic cell。

**参数：**
- `<target>`：可以是cell编号（如：1, 2, 3）或cell名称的部分匹配

**示例：**
```vim
:MoltenGotoMagicCell 1          " 跳转到第1个cell
:MoltenGotoMagicCell 数据导入    " 跳转到名称包含"数据导入"的cell
```

#### `:MoltenListMagicCells`
列出当前缓冲区的所有magic cell信息。

**显示信息：**
- Cell编号和名称
- 行号范围
- 包含的函数和类数量

### Outline窗口操作

在outline窗口中可以使用以下快捷键：

- `<Enter>`：跳转到选中的代码元素
- `q` 或 `<Esc>`：关闭outline窗口

## 📋 使用示例

### 示例Python文件

```python
#%% Cell 1: 数据导入和初始化
import pandas as pd
import numpy as np

def load_data(filepath):
    """加载数据文件"""
    return pd.read_csv(filepath)

class DataManager:
    """数据管理器，负责数据的读取和预处理"""
    
    def __init__(self, spark):
        self.spark = spark
    
    def load_price_prediction_data(self, request_pt: str):
        """加载价格预测数据"""
        logging.info(f"开始加载价格预测数据，请求时间点: {request_pt}")
        return processed_data

#%% Cell 2: 数据处理
def prepare_optimization_data():
    """准备优化数据"""
    start_time = time.time()
    
    # 添加lambda字段
    lambda_df = spark.sql("SELECT * FROM lambda_table")
    
    return processed_data

#%% Cell 3: 数据分析
result = processed_data.describe()
print(result)
```

### Outline显示效果

```
📘 Cell 1: 数据导入和初始化
  🔧 load_data(filepath)
  🏛️ class DataManager
    ⚙️ __init__(self, spark)
    ⚙️ load_price_prediction_data(self, request_pt)
📘 Cell 2: 数据处理
  🔧 prepare_optimization_data()
📘 Cell 3: 数据分析
```

## ⚙️ 配置设置

### Lazy.nvim配置

```lua
return {
    {
        "benlubas/molten-nvim",
        version = "^1.0.0",
        dependencies = { "3rd/image.nvim" },
        build = ":UpdateRemotePlugins",
        config = function()
            -- Molten基础配置
            vim.g.molten_image_provider = "image.nvim"
            vim.g.molten_output_win_max_height = 20
            
            -- 设置outline功能
            require('molten_outline_config').setup({
                auto_refresh = true,  -- 启用自动刷新
            })
        end,
    },
}
```

### 键盘映射配置

```lua
-- Outline控制
vim.keymap.set('n', '<leader>mo', ':MoltenShowOutline<CR>', { desc = 'Show outline' })
vim.keymap.set('n', '<leader>mO', ':MoltenToggleOutline<CR>', { desc = 'Toggle outline' })
vim.keymap.set('n', '<leader>mh', ':MoltenHideOutline<CR>', { desc = 'Hide outline' })

-- Magic cell导航
vim.keymap.set('n', '<leader>ml', ':MoltenListMagicCells<CR>', { desc = 'List cells' })
vim.keymap.set('n', '<leader>mg', ':MoltenGotoMagicCell ', { desc = 'Go to cell' })

-- 快速跳转（1-9）
for i = 1, 9 do
    vim.keymap.set('n', '<leader>m' .. i, ':MoltenGotoMagicCell ' .. i .. '<CR>', 
        { desc = 'Go to cell ' .. i })
end

-- 增强导航
vim.keymap.set('n', '<leader>mn', ':MoltenNextMagicCell<CR>', { desc = 'Next cell' })
vim.keymap.set('n', '<leader>mp', ':MoltenPrevMagicCell<CR>', { desc = 'Previous cell' })
vim.keymap.set('n', '<leader>mc', ':MoltenEvaluateMagicCell<CR>', { desc = 'Run cell' })
```

## 🎨 自定义配置

### 高亮组自定义

```lua
-- 自定义outline高亮
vim.api.nvim_set_hl(0, 'MoltenOutlineMagicCell', { fg = '#61AFEF', bold = true })
vim.api.nvim_set_hl(0, 'MoltenOutlineFunction', { fg = '#C678DD' })
vim.api.nvim_set_hl(0, 'MoltenOutlineClass', { fg = '#E06C75', bold = true })
vim.api.nvim_set_hl(0, 'MoltenOutlineMethod', { fg = '#98C379' })
vim.api.nvim_set_hl(0, 'MoltenOutlineVariable', { fg = '#D19A66' })
```

### 窗口样式自定义

可以通过修改`outline.py`中的窗口配置来自定义outline窗口的外观：

```python
# 在OutlineRenderer._create_outline_window方法中修改
win_config = {
    'relative': 'editor',
    'width': 50,           # 调整宽度
    'height': height - 2,  # 调整高度
    'col': 0,              # 改为左侧显示
    'row': 1,
    'style': 'minimal',
    'border': 'double',    # 改为双边框
    'title': title,
    'title_pos': 'left'    # 标题左对齐
}
```

## 🔧 高级用法

### 工作流程建议

1. **文件结构规划**
   ```python
   #%% 1. 导入和配置
   # 所有import语句和全局配置
   
   #%% 2. 数据加载
   # 数据读取和预处理函数
   
   #%% 3. 数据分析
   # 分析和可视化代码
   
   #%% 4. 模型训练
   # 机器学习模型相关代码
   
   #%% 5. 结果输出
   # 结果保存和报告生成
   ```

2. **使用outline进行代码导航**
   - 打开文件后立即显示outline：`<leader>mo`
   - 使用数字键快速跳转：`<leader>m1`, `<leader>m2`...
   - 查看所有cell概览：`<leader>ml`

3. **结合现有molten功能**
   - 在outline中选择cell，然后运行：`<leader>mc`
   - 使用虚拟文本输出查看结果
   - 结合浮动窗口输出进行调试

### 自动化工作流

```lua
-- 创建自动命令，打开Python文件时自动显示outline
vim.api.nvim_create_autocmd("FileType", {
    pattern = "python",
    callback = function()
        -- 延迟显示outline，避免启动时的性能问题
        vim.defer_fn(function()
            if vim.fn.search('#%%', 'n') > 0 then  -- 检查是否有magic cell
                vim.cmd('MoltenShowOutline')
            end
        end, 500)
    end
})
```

## 🐛 故障排除

### 常见问题

**问题1**: "当前缓冲区中没有找到magic cell"
- **解决**: 确保文件中包含`#%%`标记，格式正确

**问题2**: Outline窗口显示空白
- **解决**: 检查Python代码是否有语法错误，修复后重新显示outline

**问题3**: 函数没有在outline中显示
- **解决**: 确保函数定义格式正确，使用标准的`def function_name():`格式

**问题4**: 跳转功能不工作
- **解决**: 确保outline窗口是活动的，或者使用命令行方式跳转

### 性能优化

- 对于大文件（>1000行），outline解析可能较慢
- 可以通过禁用自动刷新来提高性能：
  ```lua
  require('molten_outline_config').setup({
      auto_refresh = false
  })
  ```

## 🎯 最佳实践

1. **命名规范**：为magic cell使用描述性的名称
   ```python
   #%% 数据预处理：清洗和标准化
   #%% 特征工程：创建新特征
   #%% 模型训练：XGBoost分类器
   ```

2. **结构化组织**：将相关功能组织在同一个cell中
   ```python
   #%% 工具函数定义
   def helper_function1():
       pass
   
   def helper_function2():
       pass
   
   class UtilityClass:
       pass
   ```

3. **文档化**：在cell中添加docstring说明
   ```python
   #%% 数据分析模块
   """
   这个cell包含了数据分析的核心函数
   - analyze_data(): 主要分析函数
   - plot_results(): 结果可视化
   """
   ```

---

通过这些新功能，您可以更高效地浏览和导航复杂的Python数据科学项目，享受类似IDE的开发体验！
