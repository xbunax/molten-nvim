"""
Molten Magic Cell Outline功能
提供基于#%%魔法命令的cell outline预览和函数outline预览
"""

import ast
import re
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class OutlineItemType(Enum):
    """Outline项目类型"""
    MAGIC_CELL = "magic_cell"
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"


@dataclass
class OutlineItem:
    """Outline项目数据结构"""
    name: str                    # 显示名称
    type: OutlineItemType       # 项目类型
    line_start: int             # 开始行号 (0-based)
    line_end: int               # 结束行号 (0-based)
    level: int                  # 缩进层级
    parent: Optional['OutlineItem'] = None  # 父项目
    children: List['OutlineItem'] = None    # 子项目
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
    
    def to_dict(self) -> dict:
        """转换为字典格式，用于存储到Neovim变量"""
        return {
            'name': self.name,
            'type': self.type.value,
            'line_start': self.line_start,
            'line_end': self.line_end,
            'level': self.level,
            'children': [child.to_dict() for child in self.children]
        }


class MagicCellOutlineParser:
    """Magic Cell和函数的Outline解析器"""
    
    def __init__(self):
        self.magic_cell_pattern = re.compile(r'^\s*#%%\s*(.*?)$')
    
    def parse_buffer_outline(self, lines: List[str]) -> List[OutlineItem]:
        """解析缓冲区内容，生成完整的outline结构"""
        outline_items = []
        
        # 1. 解析magic cells
        magic_cells = self._parse_magic_cells(lines)
        
        # 2. 为每个magic cell解析内部的函数和类
        for cell in magic_cells:
            cell_lines = lines[cell.line_start:cell.line_end + 1]
            functions_and_classes = self._parse_functions_and_classes(
                cell_lines, cell.line_start
            )
            cell.children = functions_and_classes
            outline_items.append(cell)
        
        return outline_items
    
    def _parse_magic_cells(self, lines: List[str]) -> List[OutlineItem]:
        """解析magic cells"""
        cells = []
        cell_starts = []
        
        # 查找所有#%%标记的行
        for i, line in enumerate(lines):
            match = self.magic_cell_pattern.match(line)
            if match:
                cell_title = match.group(1).strip() or f"Cell {len(cell_starts) + 1}"
                cell_starts.append((i, cell_title))
        
        # 生成cell边界
        for i, (start_line, title) in enumerate(cell_starts):
            if i + 1 < len(cell_starts):
                end_line = cell_starts[i + 1][0] - 1
            else:
                end_line = len(lines) - 1
            
            cell = OutlineItem(
                name=title,
                type=OutlineItemType.MAGIC_CELL,
                line_start=start_line,
                line_end=end_line,
                level=0
            )
            cells.append(cell)
        
        return cells
    
    def _parse_functions_and_classes(self, lines: List[str], offset: int) -> List[OutlineItem]:
        """解析代码块中的函数和类定义"""
        items = []
        code = '\n'.join(lines)
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    item = self._create_function_item(node, offset)
                    items.append(item)
                elif isinstance(node, ast.ClassDef):
                    item = self._create_class_item(node, offset, lines)
                    items.append(item)
        except SyntaxError:
            # 如果代码有语法错误，尝试简单的正则表达式解析
            items = self._parse_with_regex(lines, offset)
        
        return sorted(items, key=lambda x: x.line_start)
    
    def _create_function_item(self, node: ast.FunctionDef, offset: int) -> OutlineItem:
        """创建函数outline项目"""
        # 获取函数签名
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        
        signature = f"{node.name}({', '.join(args)})"
        
        return OutlineItem(
            name=signature,
            type=OutlineItemType.FUNCTION,
            line_start=node.lineno - 1 + offset,
            line_end=node.end_lineno - 1 + offset if node.end_lineno else node.lineno - 1 + offset,
            level=1
        )
    
    def _create_class_item(self, node: ast.ClassDef, offset: int, lines: List[str]) -> OutlineItem:
        """创建类outline项目"""
        class_item = OutlineItem(
            name=f"class {node.name}",
            type=OutlineItemType.CLASS,
            line_start=node.lineno - 1 + offset,
            line_end=node.end_lineno - 1 + offset if node.end_lineno else node.lineno - 1 + offset,
            level=1
        )
        
        # 解析类中的方法
        for child_node in node.body:
            if isinstance(child_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_item = self._create_method_item(child_node, offset, class_item)
                class_item.children.append(method_item)
        
        return class_item
    
    def _create_method_item(self, node: ast.FunctionDef, offset: int, parent: OutlineItem) -> OutlineItem:
        """创建方法outline项目"""
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        
        signature = f"{node.name}({', '.join(args)})"
        
        return OutlineItem(
            name=signature,
            type=OutlineItemType.METHOD,
            line_start=node.lineno - 1 + offset,
            line_end=node.end_lineno - 1 + offset if node.end_lineno else node.lineno - 1 + offset,
            level=2,
            parent=parent
        )
    
    def _parse_with_regex(self, lines: List[str], offset: int) -> List[OutlineItem]:
        """使用正则表达式解析函数和类（备用方案）"""
        items = []
        func_pattern = re.compile(r'^\s*(def|async\s+def)\s+(\w+)\s*\((.*?)\):')
        class_pattern = re.compile(r'^\s*class\s+(\w+).*?:')
        
        for i, line in enumerate(lines):
            func_match = func_pattern.match(line)
            if func_match:
                func_name = func_match.group(2)
                args = func_match.group(3)
                signature = f"{func_name}({args})"
                
                item = OutlineItem(
                    name=signature,
                    type=OutlineItemType.FUNCTION,
                    line_start=i + offset,
                    line_end=i + offset,  # 简化处理，只标记开始行
                    level=1
                )
                items.append(item)
            
            class_match = class_pattern.match(line)
            if class_match:
                class_name = class_match.group(1)
                
                item = OutlineItem(
                    name=f"class {class_name}",
                    type=OutlineItemType.CLASS,
                    line_start=i + offset,
                    line_end=i + offset,  # 简化处理，只标记开始行
                    level=1
                )
                items.append(item)
        
        return items


class VerticalOutlineRenderer:
    """垂直层级outline渲染器，实现从左到右的层级显示"""
    
    def __init__(self, nvim):
        self.nvim = nvim
        self.outline_windows = []  # 存储多个窗口的信息
        self.outline_buffers = []  # 存储多个缓冲区
        self.current_level = 0     # 当前激活的层级
        self.outline_items = []    # 存储outline数据
        self.lsp_client = None     # LSP客户端
        
    def show_vertical_outline(self, outline_items: List[OutlineItem], title: str = "Vertical Outline"):
        """显示垂直层级outline"""
        self.outline_items = outline_items
        
        # 清理现有窗口
        self._cleanup_windows()
        
        # 获取LSP符号信息（如果可用）
        self._get_lsp_symbols()
        
        # 创建层级结构
        levels = self._build_level_structure(outline_items)
        
        # 创建多个垂直窗口
        self._create_vertical_windows(levels, title)
        
        # 设置导航键位
        self._setup_vertical_navigation()
        
        # 聚焦到第一个窗口
        if self.outline_windows:
            self.nvim.api.set_current_win(self.outline_windows[0]['win'])
            
    def _get_lsp_symbols(self):
        """获取LSP符号信息"""
        try:
            # 尝试获取当前缓冲区的LSP符号
            current_buf = self.nvim.current.buffer
            buf_name = self.nvim.api.buf_get_name(current_buf.number)
            
            # 调用LSP获取符号
            lsp_symbols = self.nvim.call('luaeval', '''
                local params = {
                    textDocument = vim.lsp.util.make_text_document_params()
                }
                local results = {}
                local clients = vim.lsp.get_active_clients()
                
                for _, client in ipairs(clients) do
                    if client.supports_method("textDocument/documentSymbol") then
                        local result = client.request_sync("textDocument/documentSymbol", params, 5000)
                        if result and result.result then
                            table.insert(results, result.result)
                        end
                    end
                end
                
                return results
            ''')
            
            # 处理LSP符号结果
            if lsp_symbols:
                self._process_lsp_symbols(lsp_symbols)
                
        except Exception as e:
            # LSP不可用时使用基础解析
            pass
            
    def _process_lsp_symbols(self, lsp_symbols):
        """处理LSP符号信息"""
        # 将LSP符号转换为我们的outline项目格式
        # 这里可以获取更准确的函数、类、变量信息
        pass
        
    def _build_level_structure(self, outline_items: List[OutlineItem]) -> List[List[OutlineItem]]:
        """构建层级结构"""
        levels = []
        
        # 第一层：Magic Cells
        level_0 = [item for item in outline_items if item.type == OutlineItemType.MAGIC_CELL]
        if level_0:
            levels.append(level_0)
        
        # 第二层：当前选中cell的函数和类
        if level_0:
            current_cell = level_0[0]  # 默认选择第一个cell
            level_1 = []
            
            # 添加函数
            for item in outline_items:
                if (item.type in [OutlineItemType.FUNCTION, OutlineItemType.CLASS, OutlineItemType.VARIABLE] and
                    item.line_start >= current_cell.line_start and 
                    item.line_end <= current_cell.line_end):
                    level_1.append(item)
            
            if level_1:
                levels.append(level_1)
                
                # 第三层：选中函数/类的方法
                current_func = level_1[0]  # 默认选择第一个函数
                if current_func.type == OutlineItemType.CLASS:
                    level_2 = [child for child in current_func.children if child.type == OutlineItemType.METHOD]
                    if level_2:
                        levels.append(level_2)
        
        return levels
        
    def _create_vertical_windows(self, levels: List[List[OutlineItem]], title: str):
        """创建垂直排列的窗口"""
        if not levels:
            return
            
        # 计算窗口布局
        ui_width = self.nvim.api.get_option("columns")
        ui_height = self.nvim.api.get_option("lines")
        
        # 每个窗口的宽度
        window_width = min(25, ui_width // (len(levels) + 1))
        window_height = ui_height - 6
        
        # 创建每个层级的窗口
        for i, level_items in enumerate(levels):
            # 计算窗口位置
            col = i * (window_width + 2)  # 窗口间隔2列
            row = 2
            
            # 创建缓冲区
            buf_handle = self.nvim.api.create_buf(False, True)
            
            # 兼容性处理
            if hasattr(buf_handle, 'number'):
                buf = buf_handle
            else:
                buf = self.nvim.buffers[buf_handle]
            
            # 设置缓冲区名称
            level_name = self._get_level_name(i)
            self.nvim.api.buf_set_name(buf.number, f"[{title} - {level_name}]")
            
            # 渲染内容
            lines = self._render_level_content(level_items, i)
            self.nvim.api.buf_set_lines(buf.number, 0, -1, False, lines)
            
            # 设置缓冲区选项
            self.nvim.api.buf_set_option(buf.number, 'modifiable', False)
            self.nvim.api.buf_set_option(buf.number, 'buftype', 'nofile')
            
            # 创建浮动窗口
            win_config = {
                'relative': 'editor',
                'width': window_width,
                'height': window_height,
                'col': col,
                'row': row,
                'style': 'minimal',
                'border': 'rounded',
                'title': f"{level_name} (Level {i+1})",
                'title_pos': 'center'
            }
            
            win = self.nvim.api.open_win(buf.number, False, win_config)
            
            # 设置窗口选项
            self.nvim.api.win_set_option(win, 'wrap', False)
            self.nvim.api.win_set_option(win, 'cursorline', True)
            self.nvim.api.win_set_option(win, 'number', False)
            self.nvim.api.win_set_option(win, 'relativenumber', False)
            
            # 存储窗口信息
            window_info = {
                'win': win,
                'buf': buf.number,
                'level': i,
                'items': level_items
            }
            self.outline_windows.append(window_info)
            self.outline_buffers.append(buf.number)
            
    def _get_level_name(self, level: int) -> str:
        """获取层级名称"""
        names = ["Cells", "Functions", "Methods", "Variables"]
        return names[level] if level < len(names) else f"Level {level + 1}"
        
    def _render_level_content(self, items: List[OutlineItem], level: int) -> List[str]:
        """渲染层级内容"""
        lines = []
        
        for i, item in enumerate(items):
            # 选择图标
            icon = self._get_item_icon(item.type)
            
            # 格式化显示
            if item.type == OutlineItemType.MAGIC_CELL:
                # Cell显示：编号 + 名称
                cell_num = i + 1
                name = item.name.replace("# Magic Cell: ", "").strip() or f"Cell {cell_num}"
                line = f"{icon} [{cell_num}] {name}"
            else:
                # 函数/类显示：名称 + 行号
                line = f"{icon} {item.name} ({item.line_start + 1})"
            
            lines.append(line)
            
        return lines if lines else ["(Empty)"]
        
    def _get_item_icon(self, item_type: OutlineItemType) -> str:
        """获取项目类型图标"""
        icons = {
            OutlineItemType.MAGIC_CELL: "📘",
            OutlineItemType.FUNCTION: "🔧",
            OutlineItemType.CLASS: "🏛️", 
            OutlineItemType.METHOD: "⚙️",
            OutlineItemType.VARIABLE: "📝"
        }
        return icons.get(item_type, "•")
        
    def _setup_vertical_navigation(self):
        """设置垂直导航键位"""
        # 为每个窗口设置键位映射
        for window_info in self.outline_windows:
            buf_num = window_info['buf']
            level = window_info['level']
            
            # hjkl导航键位
            mappings = [
                # h: 向左移动到上一层级
                ('n', 'h', f':lua molten_vertical_outline_move_left({level})<CR>', {'silent': True}),
                # l: 向右移动到下一层级  
                ('n', 'l', f':lua molten_vertical_outline_move_right({level})<CR>', {'silent': True}),
                # j: 在当前层级向下
                ('n', 'j', f':lua molten_vertical_outline_move_down({level})<CR>', {'silent': True}),
                # k: 在当前层级向上
                ('n', 'k', f':lua molten_vertical_outline_move_up({level})<CR>', {'silent': True}),
                # 回车: 选择/跳转
                ('n', '<CR>', f':lua molten_vertical_outline_select({level})<CR>', {'silent': True}),
                # q/Esc: 关闭
                ('n', 'q', ':lua molten_vertical_outline_close()<CR>', {'silent': True}),
                ('n', '<Esc>', ':lua molten_vertical_outline_close()<CR>', {'silent': True}),
            ]
            
            for mode, key, cmd, opts in mappings:
                self.nvim.api.buf_set_keymap(buf_num, mode, key, cmd, opts)
                
        # 设置Lua导航函数
        self._setup_lua_navigation_functions()
        
    def _setup_lua_navigation_functions(self):
        """设置Lua导航函数"""
        lua_code = f'''
        -- 垂直outline导航函数
        local vertical_outline_windows = {[win['win'] for win in self.outline_windows]}
        local current_level = 0
        
        function molten_vertical_outline_move_left(level)
            if level > 0 then
                local target_win = vertical_outline_windows[level]  -- level-1 in 0-based
                if target_win and vim.api.nvim_win_is_valid(target_win) then
                    vim.api.nvim_set_current_win(target_win)
                    current_level = level - 1
                end
            end
        end
        
        function molten_vertical_outline_move_right(level)
            if level < {len(self.outline_windows) - 1} then
                local target_win = vertical_outline_windows[level + 2]  -- level+1 in 0-based  
                if target_win and vim.api.nvim_win_is_valid(target_win) then
                    vim.api.nvim_set_current_win(target_win)
                    current_level = level + 1
                end
            end
        end
        
        function molten_vertical_outline_move_down(level)
            vim.cmd('normal! j')
            -- 更新相关层级
            molten_vertical_outline_update_dependent_levels(level)
        end
        
        function molten_vertical_outline_move_up(level)
            vim.cmd('normal! k')
            -- 更新相关层级
            molten_vertical_outline_update_dependent_levels(level)
        end
        
        function molten_vertical_outline_select(level)
            local cursor = vim.api.nvim_win_get_cursor(0)
            local line_num = cursor[1] - 1  -- 转换为0-based
            
            -- 调用Python函数处理选择
            vim.fn.MoltenVerticalOutlineSelect(level, line_num)
        end
        
        function molten_vertical_outline_update_dependent_levels(level)
            -- 当选择改变时，更新依赖的层级
            local cursor = vim.api.nvim_win_get_cursor(0)
            local line_num = cursor[1] - 1
            
            vim.fn.MoltenVerticalOutlineUpdateLevels(level, line_num)
        end
        
        function molten_vertical_outline_close()
            vim.fn.MoltenVerticalOutlineClose()
        end
        '''
        
        try:
            self.nvim.exec_lua(lua_code)
        except Exception as e:
            # 如果Lua执行失败，至少设置基本的关闭功能
            pass
            
    def update_dependent_levels(self, changed_level: int, selected_index: int):
        """更新依赖层级"""
        if changed_level >= len(self.outline_windows) - 1:
            return
            
        # 获取当前选择的项目
        current_window = self.outline_windows[changed_level]
        if selected_index >= len(current_window['items']):
            return
            
        selected_item = current_window['items'][selected_index]
        
        # 更新下一层级
        next_level = changed_level + 1
        if next_level < len(self.outline_windows):
            self._update_level_content(next_level, selected_item)
            
    def _update_level_content(self, level: int, parent_item: OutlineItem):
        """更新指定层级的内容"""
        if level >= len(self.outline_windows):
            return
            
        window_info = self.outline_windows[level]
        
        # 根据父项目获取子项目
        new_items = []
        
        if level == 1:  # 函数层级
            # 获取选中cell中的函数
            for item in self.outline_items:
                if (item.type in [OutlineItemType.FUNCTION, OutlineItemType.CLASS] and
                    item.line_start >= parent_item.line_start and 
                    item.line_end <= parent_item.line_end):
                    new_items.append(item)
        elif level == 2:  # 方法层级
            # 获取选中类的方法
            new_items = [child for child in parent_item.children if child.type == OutlineItemType.METHOD]
            
        # 更新窗口内容
        window_info['items'] = new_items
        lines = self._render_level_content(new_items, level)
        self.nvim.api.buf_set_option(window_info['buf'], 'modifiable', True)
        self.nvim.api.buf_set_lines(window_info['buf'], 0, -1, False, lines)
        self.nvim.api.buf_set_option(window_info['buf'], 'modifiable', False)
        
    def select_item(self, level: int, item_index: int):
        """选择项目并跳转"""
        if level >= len(self.outline_windows) or item_index >= len(self.outline_windows[level]['items']):
            return
            
        selected_item = self.outline_windows[level]['items'][item_index]
        
        # 关闭outline窗口
        self.close_vertical_outline()
        
        # 跳转到目标位置
        self._jump_to_item(selected_item)
        
    def _jump_to_item(self, item: OutlineItem):
        """跳转到指定项目"""
        # 找到原始文件窗口
        for win in self.nvim.api.list_wins():
            buf = self.nvim.api.win_get_buf(win)
            buf_name = self.nvim.api.buf_get_name(buf)
            
            # 跳过outline窗口
            if not any(f"[{self._get_level_name(i)}" in buf_name for i in range(4)):
                self.nvim.api.set_current_win(win)
                self.nvim.api.win_set_cursor(win, [item.line_start + 1, 0])
                self.nvim.command('normal! zz')  # 居中显示
                break
                
    def close_vertical_outline(self):
        """关闭垂直outline"""
        # 关闭所有窗口
        for window_info in self.outline_windows:
            try:
                if self.nvim.api.win_is_valid(window_info['win']):
                    self.nvim.api.win_close(window_info['win'], True)
            except:
                pass
                
        # 删除所有缓冲区
        for buf_num in self.outline_buffers:
            try:
                if self.nvim.api.buf_is_valid(buf_num):
                    self.nvim.api.buf_delete(buf_num, {'force': True})
            except:
                pass
                
        # 清理状态
        self.outline_windows.clear()
        self.outline_buffers.clear()
        self.current_level = 0
        
    def _cleanup_windows(self):
        """清理现有窗口"""
        self.close_vertical_outline()


class OutlineRenderer:
    """Outline渲染器，负责在Neovim中显示outline"""
    
    def __init__(self, nvim):
        self.nvim = nvim
        self.outline_buf = None
        self.outline_win = None
        self.outline_items = []
        
    
    def _create_outline_window(self, title: str):
        """创建居中的outline弹出窗口"""
        # 创建缓冲区
        self.outline_buf = self.nvim.api.create_buf(False, True)
        self.nvim.api.buf_set_name(self.outline_buf, f"[{title}]")
        
        # 计算窗口尺寸和位置 - 居中显示
        ui_width = self.nvim.api.get_option("columns")
        ui_height = self.nvim.api.get_option("lines")
        
        # 窗口尺寸：宽度为屏幕的60%，高度为屏幕的70%
        width = int(ui_width * 0.6)
        height = int(ui_height * 0.7)
        
        # 居中位置
        col = int((ui_width - width) / 2)
        row = int((ui_height - height) / 2)
        
        # 创建居中的浮动窗口
        win_config = {
            'relative': 'editor',
            'width': width,
            'height': height,
            'col': col,
            'row': row,
            'style': 'minimal',
            'border': 'rounded',
            'title': title,
            'title_pos': 'center'
        }
        
        self.outline_win = self.nvim.api.open_win(self.outline_buf, True, win_config)  # 设置为True使窗口获得焦点
        
        # 设置窗口选项
        self.nvim.api.win_set_option(self.outline_win, 'wrap', False)
        self.nvim.api.win_set_option(self.outline_win, 'cursorline', True)
        self.nvim.api.win_set_option(self.outline_win, 'number', False)
        self.nvim.api.win_set_option(self.outline_win, 'relativenumber', False)
    
    def _render_outline_content(self, outline_items: List[OutlineItem]) -> List[str]:
        """渲染outline内容"""
        lines = []
        
        for item in outline_items:
            lines.extend(self._render_outline_item(item))
        
        return lines
    
    def _render_outline_item(self, item: OutlineItem) -> List[str]:
        """渲染单个outline项目"""
        lines = []
        indent = "  " * item.level
        
        # 选择图标
        icon = self._get_item_icon(item.type)
        
        # 格式化行
        line = f"{indent}{icon} {item.name}"
        lines.append(line)
        
        # 递归渲染子项目
        for child in item.children:
            lines.extend(self._render_outline_item(child))
        
        return lines
    
    def _get_item_icon(self, item_type: OutlineItemType) -> str:
        """获取项目类型对应的图标"""
        icons = {
            OutlineItemType.MAGIC_CELL: "📘",
            OutlineItemType.FUNCTION: "🔧",
            OutlineItemType.CLASS: "🏛️",
            OutlineItemType.METHOD: "⚙️",
            OutlineItemType.VARIABLE: "📝"
        }
        return icons.get(item_type, "•")
    
    def _setup_outline_syntax(self):
        """设置outline语法高亮"""
        # 使用API直接设置buffer的语法高亮
        try:
            # 设置buffer的文件类型
            self.nvim.api.buf_set_option(self.outline_buf, 'filetype', 'molten-outline')
            
            # 定义语法高亮规则 - 使用API调用
            current_win = self.nvim.api.get_current_win()
            self.nvim.api.set_current_win(self.outline_win)
            
            syntax_rules = [
                'syntax match OutlineMagicCell /📘.*/',
                'syntax match OutlineFunction /🔧.*/',
                'syntax match OutlineClass /🏛️.*/',
                'syntax match OutlineMethod /⚙️.*/',
                'syntax match OutlineVariable /📝.*/',
            ]
            
            for rule in syntax_rules:
                self.nvim.command(rule)
            
            # 设置高亮组
            highlight_groups = [
                'highlight OutlineMagicCell guifg=#61AFEF gui=bold',
                'highlight OutlineFunction guifg=#C678DD',
                'highlight OutlineClass guifg=#E06C75 gui=bold',
                'highlight OutlineMethod guifg=#98C379',
                'highlight OutlineVariable guifg=#D19A66',
            ]
            
            for group in highlight_groups:
                self.nvim.command(group)
                
            # 恢复原来的窗口
            self.nvim.api.set_current_win(current_win)
            
        except Exception as e:
            # 如果语法高亮设置失败，继续运行但不设置高亮
            pass
    
    def _setup_outline_keymaps(self):
        """设置outline窗口的键盘映射"""
        # 设置缓冲区变量，存储outline数据
        self.nvim.api.buf_set_var(self.outline_buf, 'molten_outline_renderer', id(self))
        
        # 存储outline项目数据，用于导航
        self.nvim.api.buf_set_var(self.outline_buf, 'molten_outline_items', 
                                  [item.to_dict() for item in self.current_outline_items])
        
        # 设置键盘映射
        keymaps = [
            # 基本导航
            ('n', 'j', ':call v:lua.molten_outline_nav("down")<CR>', {'noremap': True, 'silent': True}),
            ('n', 'k', ':call v:lua.molten_outline_nav("up")<CR>', {'noremap': True, 'silent': True}),
            ('n', '<Down>', ':call v:lua.molten_outline_nav("down")<CR>', {'noremap': True, 'silent': True}),
            ('n', '<Up>', ':call v:lua.molten_outline_nav("up")<CR>', {'noremap': True, 'silent': True}),
            
            # 跳转和预览
            ('n', '<CR>', ':call v:lua.molten_outline_goto()<CR>', {'noremap': True, 'silent': True}),
            ('n', 'o', ':call v:lua.molten_outline_goto()<CR>', {'noremap': True, 'silent': True}),
            ('n', 'p', ':call v:lua.molten_outline_preview()<CR>', {'noremap': True, 'silent': True}),
            
            # 退出
            ('n', 'q', ':call v:lua.molten_outline_close()<CR>', {'noremap': True, 'silent': True}),
            ('n', '<Esc>', ':call v:lua.molten_outline_close()<CR>', {'noremap': True, 'silent': True}),
            
            # 展开/折叠
            ('n', 'za', ':call v:lua.molten_outline_toggle()<CR>', {'noremap': True, 'silent': True}),
            ('n', '<Space>', ':call v:lua.molten_outline_toggle()<CR>', {'noremap': True, 'silent': True}),
        ]
        
        for mode, key, cmd, opts in keymaps:
            self.nvim.api.buf_set_keymap(self.outline_buf, mode, key, cmd, opts)
            
        # 设置Lua函数
        self._setup_lua_functions()
        
        # 存储当前outline项目，用于导航
        self.current_outline_items = []
    
    def goto_outline_item(self, line_num: int):
        """跳转到outline项目对应的位置"""
        # 获取当前行对应的outline项目
        item = self._get_item_by_line(line_num)
        if item:
            # 跳转到原始缓冲区的对应位置
            original_win = self._get_original_window()
            if original_win:
                self.nvim.api.set_current_win(original_win)
                self.nvim.api.win_set_cursor(original_win, (item.line_start + 1, 0))
    
    def _get_item_by_line(self, line_num: int) -> Optional[OutlineItem]:
        """根据outline窗口的行号获取对应的outline项目"""
        # 这里需要建立行号到outline项目的映射
        # 简化实现：遍历所有项目，找到对应的行
        current_line = 0
        
        def find_item(items: List[OutlineItem]) -> Optional[OutlineItem]:
            nonlocal current_line
            for item in items:
                if current_line == line_num:
                    return item
                current_line += 1
                
                # 递归查找子项目
                result = find_item(item.children)
                if result:
                    return result
            return None
        
        return find_item(self.outline_items)
    
    def _get_original_window(self):
        """获取原始编辑窗口"""
        # 查找非outline窗口
        for win in self.nvim.api.list_wins():
            if win != self.outline_win:
                buf = self.nvim.api.win_get_buf(win)
                buf_name = self.nvim.api.buf_get_name(buf)
                if not buf_name.startswith('[') and not buf_name.endswith(']'):
                    return win
        return None
    
    def close_outline(self):
        """关闭outline窗口"""
        if self.outline_win and self.nvim.api.win_is_valid(self.outline_win):
            self.nvim.api.win_close(self.outline_win, True)
            self.outline_win = None
        
        if self.outline_buf and self.nvim.api.buf_is_valid(self.outline_buf):
            self.nvim.api.buf_delete(self.outline_buf, {'force': True})
            self.outline_buf = None
    
    def _setup_lua_functions(self):
        """设置Lua辅助函数"""
        lua_code = '''
        -- Molten Outline 导航函数
        local function get_outline_bufnr()
            for _, bufnr in ipairs(vim.api.nvim_list_bufs()) do
                local buf_name = vim.api.nvim_buf_get_name(bufnr)
                if buf_name:match("%[Outline:.*%]") then
                    return bufnr
                end
            end
            return nil
        end
        
        local function get_current_item()
            local bufnr = get_outline_bufnr()
            if not bufnr then return nil end
            
            local cursor = vim.api.nvim_win_get_cursor(0)
            local line_num = cursor[1] - 1  -- 转换为0-based
            
            -- 获取outline项目数据
            local ok, items = pcall(vim.api.nvim_buf_get_var, bufnr, 'molten_outline_items')
            if not ok or not items then return nil end
            
            -- 递归查找当前行对应的项目
            local function find_item_by_line(items_list, current_line)
                for _, item in ipairs(items_list) do
                    if current_line == 0 then
                        return item
                    end
                    current_line = current_line - 1
                    
                    if #item.children > 0 then
                        local result = find_item_by_line(item.children, current_line)
                        if result then
                            return result
                        end
                        current_line = current_line - #item.children
                    end
                end
                return nil
            end
            
            return find_item_by_line(items, line_num)
        end
        
        function molten_outline_nav(direction)
            if direction == "down" then
                vim.cmd('normal! j')
            elseif direction == "up" then
                vim.cmd('normal! k')
            end
            
            -- 自动预览
            molten_outline_preview()
        end
        
        function molten_outline_goto()
            local item = get_current_item()
            if not item then return end
            
            -- 找到原始文件窗口
            local original_win = nil
            for _, win in ipairs(vim.api.nvim_list_wins()) do
                local buf = vim.api.nvim_win_get_buf(win)
                local buf_name = vim.api.nvim_buf_get_name(buf)
                if not buf_name:match("%[Outline:.*%]") and buf_name ~= "" then
                    original_win = win
                    break
                end
            end
            
            -- 关闭outline窗口
            molten_outline_close()
            
            -- 跳转到目标位置
            if original_win then
                vim.api.nvim_set_current_win(original_win)
                vim.api.nvim_win_set_cursor(original_win, {item.line_start + 1, 0})
                vim.cmd('normal! zz')  -- 居中显示
            end
        end
        
        function molten_outline_preview()
            local item = get_current_item()
            if not item then return end
            
            -- 在状态行显示预览信息
            local preview_text = string.format("Line %d: %s", item.line_start + 1, item.name)
            vim.api.nvim_echo({{preview_text, "Normal"}}, false, {})
        end
        
        function molten_outline_close()
            local bufnr = get_outline_bufnr()
            if bufnr then
                local wins = vim.api.nvim_list_wins()
                for _, win in ipairs(wins) do
                    if vim.api.nvim_win_get_buf(win) == bufnr then
                        vim.api.nvim_win_close(win, true)
                        break
                    end
                end
            end
        end
        
        function molten_outline_toggle()
            -- 简单的展开/折叠功能（占位符）
            vim.api.nvim_echo({{"Toggle not implemented yet", "WarningMsg"}}, false, {})
        end
        '''
        
        try:
            self.nvim.exec_lua(lua_code)
        except Exception as e:
            # 如果Lua函数设置失败，继续运行
            pass
    
    def show_outline(self, outline_items: List[OutlineItem], title: str):
        """显示outline窗口"""
        # 存储当前outline项目
        self.current_outline_items = outline_items
        self.outline_items = outline_items
        
        # 如果窗口不存在或无效，创建新窗口
        if self.outline_win is None or not self.nvim.api.win_is_valid(self.outline_win):
            self._create_outline_window(title)
        
        # 渲染内容
        content_lines = self._render_outline_content(outline_items)
        self.nvim.api.buf_set_lines(self.outline_buf, 0, -1, False, content_lines)
        
        # 设置语法高亮
        self._setup_outline_syntax()
        
        # 设置键盘映射
        self._setup_outline_keymaps()
