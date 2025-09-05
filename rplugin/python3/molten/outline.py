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


class OutlineRenderer:
    """Outline渲染器，负责在Neovim中显示outline"""
    
    def __init__(self, nvim):
        self.nvim = nvim
        self.outline_buf = None
        self.outline_win = None
        self.outline_items = []
        
    def show_outline(self, outline_items: List[OutlineItem], title: str = "Magic Cell Outline"):
        """显示outline窗口"""
        self.outline_items = outline_items
        
        # 创建outline内容
        content_lines = self._render_outline_content(outline_items)
        
        # 创建或更新outline窗口
        if self.outline_win is None or not self.nvim.api.nvim_win_is_valid(self.outline_win):
            self._create_outline_window(title)
        
        # 设置缓冲区内容
        self.nvim.api.nvim_buf_set_lines(self.outline_buf, 0, -1, False, content_lines)
        
        # 设置语法高亮
        self._setup_outline_syntax()
        
        # 设置键盘映射
        self._setup_outline_keymaps()
    
    def _create_outline_window(self, title: str):
        """创建outline窗口"""
        # 创建缓冲区
        self.outline_buf = self.nvim.api.nvim_create_buf(False, True)
        self.nvim.api.nvim_buf_set_name(self.outline_buf, f"[{title}]")
        
        # 计算窗口尺寸和位置
        ui_width = self.nvim.api.nvim_get_option("columns")
        ui_height = self.nvim.api.nvim_get_option("lines")
        
        width = min(60, ui_width // 3)
        height = ui_height - 4
        
        # 创建浮动窗口
        win_config = {
            'relative': 'editor',
            'width': width,
            'height': height,
            'col': ui_width - width - 2,
            'row': 1,
            'style': 'minimal',
            'border': 'rounded',
            'title': title,
            'title_pos': 'center'
        }
        
        self.outline_win = self.nvim.api.nvim_open_win(self.outline_buf, False, win_config)
        
        # 设置窗口选项
        self.nvim.api.nvim_win_set_option(self.outline_win, 'wrap', False)
        self.nvim.api.nvim_win_set_option(self.outline_win, 'cursorline', True)
    
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
        # 定义语法高亮规则
        syntax_rules = [
            'syntax match OutlineMagicCell /📘.*/',
            'syntax match OutlineFunction /🔧.*/',
            'syntax match OutlineClass /🏛️.*/',
            'syntax match OutlineMethod /⚙️.*/',
            'syntax match OutlineVariable /📝.*/',
        ]
        
        for rule in syntax_rules:
            self.nvim.command(f'call nvim_buf_call({self.outline_buf}, function("execute", ["{rule}"]))')
        
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
    
    def _setup_outline_keymaps(self):
        """设置outline窗口的键盘映射"""
        # 设置缓冲区变量，存储outline数据
        self.nvim.api.nvim_buf_set_var(self.outline_buf, 'molten_outline_renderer', id(self))
    
    def goto_outline_item(self, line_num: int):
        """跳转到outline项目对应的位置"""
        # 获取当前行对应的outline项目
        item = self._get_item_by_line(line_num)
        if item:
            # 跳转到原始缓冲区的对应位置
            original_win = self._get_original_window()
            if original_win:
                self.nvim.api.nvim_set_current_win(original_win)
                self.nvim.api.nvim_win_set_cursor(original_win, (item.line_start + 1, 0))
    
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
        for win in self.nvim.api.nvim_list_wins():
            if win != self.outline_win:
                buf = self.nvim.api.nvim_win_get_buf(win)
                buf_name = self.nvim.api.nvim_buf_get_name(buf)
                if not buf_name.startswith('[') and not buf_name.endswith(']'):
                    return win
        return None
    
    def close_outline(self):
        """关闭outline窗口"""
        if self.outline_win and self.nvim.api.nvim_win_is_valid(self.outline_win):
            self.nvim.api.nvim_win_close(self.outline_win, True)
            self.outline_win = None
        
        if self.outline_buf and self.nvim.api.nvim_buf_is_valid(self.outline_buf):
            self.nvim.api.nvim_buf_delete(self.outline_buf, {'force': True})
            self.outline_buf = None
