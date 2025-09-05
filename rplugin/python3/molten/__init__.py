import json
import os
from typing import Any, Dict, List, Optional, Tuple
from itertools import chain

import pynvim
from pynvim.api import Buffer
from molten.code_cell import CodeCell
from molten.images import Canvas, get_canvas_given_provider, WeztermCanvas
from molten.info_window import create_info_window
from molten.ipynb import export_outputs, get_default_import_export_file, import_outputs
from molten.save_load import MoltenIOError, get_default_save_file, load, save
from molten.moltenbuffer import MoltenKernel
from molten.options import MoltenOptions
from molten.outputbuffer import OutputBuffer
from molten.position import DynamicPosition, Position
from molten.runtime import get_available_kernels
from molten.utils import MoltenException, notify_error, notify_info, notify_warn, nvimui
from molten.outline import MagicCellOutlineParser, OutlineRenderer
from pynvim import Nvim


@pynvim.plugin
class Molten:
    """The plugin class. Provides an interface for interacting with the plugin via vim functions,
    user commands and user autocommands.

    Invariants that must be maintained in order for this plugin to work:
    - Any CodeCell which belongs to some MoltenKernel _a_ never overlaps with any CodeCell which
      belongs to some MoltenKernel _b_.
    """

    nvim: Nvim
    canvas: Optional[Canvas]
    initialized: bool

    highlight_namespace: int
    extmark_namespace: int

    timer: Optional[int]
    input_timer: Optional[int]

    options: MoltenOptions

    # list of nvim buf numbers to a list of MoltenKernels 'attached' to that buffer
    buffers: Dict[int, List[MoltenKernel]]
    # list of kernel names to the MoltenKernel object that handles that kernel
    # duplicate names are sufixed with (n)
    molten_kernels: Dict[str, MoltenKernel]
    # outline related components
    outline_parser: MagicCellOutlineParser
    outline_renderer: OutlineRenderer

    def __init__(self, nvim: Nvim):
        self.nvim = nvim
        self.initialized = False

        self.canvas = None
        self.buffers = {}
        self.timer = None
        self.input_timer = None
        self.molten_kernels = {}
        
        # 初始化outline组件
        self.outline_parser = MagicCellOutlineParser()
        self.outline_renderer = OutlineRenderer(nvim)

    def _initialize(self) -> None:
        assert not self.initialized

        self.options = MoltenOptions(self.nvim)

        self.canvas = get_canvas_given_provider(self.nvim, self.options)
        self.canvas.init()

        self.highlight_namespace = self.nvim.funcs.nvim_create_namespace("molten-highlights")
        self.extmark_namespace = self.nvim.funcs.nvim_create_namespace("molten-extmarks")

        self.timer = self.nvim.eval(
            f"timer_start({self.options.tick_rate}, 'MoltenTick', {{'repeat': -1}})"
        )  # type: ignore

        self.input_timer = self.nvim.eval(
            f"timer_start({self.options.tick_rate}, 'MoltenTickInput', {{'repeat': -1}})"
        )  # type: ignore

        self._setup_highlights()
        self._set_autocommands()

        self.nvim.exec_lua("_prompt_init = require('prompt').prompt_init")
        self.nvim.exec_lua("_select_and_run = require('prompt').select_and_run")
        self.nvim.exec_lua("_prompt_init_and_run = require('prompt').prompt_init_and_run")

        self.initialized = True

    def _set_autocommands(self) -> None:
        self.nvim.command("augroup molten")
        self.nvim.command("autocmd CursorMoved  * call MoltenOnCursorMoved()")
        self.nvim.command("autocmd CursorMovedI * call MoltenOnCursorMoved()")
        self.nvim.command("autocmd WinScrolled  * call MoltenOnWinScrolled()")
        self.nvim.command("autocmd BufEnter     * call MoltenUpdateInterface()")
        self.nvim.command("autocmd BufLeave     * call MoltenBufLeave()")
        self.nvim.command("autocmd BufUnload    * call MoltenOnBufferUnload()")
        self.nvim.command("autocmd ExitPre      * call MoltenOnExitPre()")
        self.nvim.command("augroup END")

    def _setup_highlights(self) -> None:
        self.nvim.exec_lua("_hl_utils = require('hl_utils')")
        hl_utils = self.nvim.lua._hl_utils
        hl_utils.set_default_highlights(self.options.hl.defaults)

    def _deinitialize(self) -> None:
        for molten_kernels in self.buffers.values():
            for molten_kernel in molten_kernels:
                molten_kernel.deinit()
        if self.canvas is not None:
            self.canvas.deinit()
        if self.timer is not None:
            self.nvim.funcs.timer_stop(self.timer)
        if self.input_timer is not None:
            self.nvim.funcs.timer_stop(self.input_timer)

    def _initialize_if_necessary(self) -> None:
        if not self.initialized:
            self._initialize()

    def _get_current_buf_kernels(self, requires_instance: bool) -> Optional[List[MoltenKernel]]:
        self._initialize_if_necessary()

        maybe_molten = self.buffers.get(self.nvim.current.buffer.number)
        if requires_instance and (maybe_molten is None or len(maybe_molten) == 0):
            raise MoltenException(
                "Molten is not initialized in this buffer; run `:MoltenInit` to initialize."
            )
        return maybe_molten

    def _clear_on_buf_leave(self) -> None:
        if not self.initialized:
            return

        for molten_kernels in self.buffers.values():
            for molten_kernel in molten_kernels:
                molten_kernel.clear_interface()
                molten_kernel.clear_open_output_windows()

    def _clear_interface(self) -> None:
        if not self.initialized:
            return

        for molten_kernels in self.buffers.values():
            for molten_kernel in molten_kernels:
                molten_kernel.clear_virt_outputs()
        self._clear_on_buf_leave()

    def _update_interface(self) -> None:
        """Called on load, show_output/hide_output and buf enter"""
        if not self.initialized:
            return

        molten_kernels = self._get_current_buf_kernels(False)
        if molten_kernels is None:
            return

        for m in molten_kernels:
            m.update_interface()

    def _on_cursor_moved(self, scrolled=False) -> None:
        if not self.initialized:
            return

        molten_kernels = self._get_current_buf_kernels(False)
        if molten_kernels is None:
            return

        for m in molten_kernels:
            m.on_cursor_moved(scrolled)

    def _initialize_buffer(self, kernel_name: str, shared=False) -> MoltenKernel | None:
        assert self.canvas is not None
        if shared:  # use an existing molten kernel, for a new neovim buffer
            molten = self.molten_kernels.get(kernel_name)
            if molten is not None:
                molten.add_nvim_buffer(self.nvim.current.buffer)
                self.buffers[self.nvim.current.buffer.number] = [molten]
                return molten

            notify_warn(
                self.nvim,
                f"No running kernel {kernel_name} to share. Continuing with a new kernel.",
            )

        kernel_id = kernel_name
        if self.molten_kernels.get(kernel_name) is not None:
            kernel_id = f"{kernel_name}_{len(self.molten_kernels)}"

        try:
            molten = MoltenKernel(
                self.nvim,
                self.canvas,
                self.highlight_namespace,
                self.extmark_namespace,
                self.nvim.current.buffer,
                self.options,
                kernel_name,
                kernel_id,
            )

            self.add_kernel(self.nvim.current.buffer, kernel_id, molten)
            molten._doautocmd("MoltenInitPost")
            if isinstance(self.canvas, WeztermCanvas):
                self.canvas.wezterm_split()

            return molten
        except Exception as e:
            notify_error(
                self.nvim, f"Could not initialize kernel named '{kernel_name}'.\nCaused By: {e}"
            )

    def add_kernel(self, buffer: Buffer, kernel_id: str, kernel: MoltenKernel):
        """Add a new MoltenKernel to be tracked by Molten.
        - Adds the new kernel to the buffer list for the given buffer
        - Adds the new kernel to the molten_kernels list, with a suffix if the name is already taken
        """
        if self.buffers.get(buffer.number) is None:
            self.buffers[buffer.number] = [kernel]
        else:
            self.buffers[buffer.number].append(kernel)

        self.molten_kernels[kernel_id] = kernel

    @pynvim.command("MoltenInit", nargs="*", sync=True, complete="file")  # type: ignore
    @nvimui  # type: ignore
    def command_init(self, args: List[str]) -> None:
        self._initialize_if_necessary()

        shared = False
        if len(args) > 0 and args[0] == "shared":
            shared = True
            args = args[1:]

        if len(args) > 0:
            kernel_name = args[0]
            self._initialize_buffer(kernel_name, shared=shared)
        else:
            PROMPT = "Select the kernel to launch:"
            available_kernels = [(x, False) for x in get_available_kernels()]
            running_kernels = [(x, True) for x in self.molten_kernels.keys()]

            if shared:
                # only show running kernels
                available_kernels = []

            kernels = available_kernels + running_kernels
            if len(kernels) == 0:
                notify_error(
                    self.nvim, f"Unable to find any {'shared' if shared else ''}kernels to launch."
                )
                return

            self.nvim.lua._prompt_init(kernels, PROMPT)

    def _deinit_buffer(self, molten_kernels: List[MoltenKernel]) -> None:
        # Have to copy this to get around reference issues
        for kernel in [x for x in molten_kernels]:
            kernel.deinit()
            for buf in kernel.buffers:
                self.buffers[buf.number].remove(kernel)
                if len(self.buffers[buf.number]) == 0:
                    del self.buffers[buf.number]
            del self.molten_kernels[kernel.kernel_id]

    def _do_evaluate_expr(self, kernel_name: str, expr):
        self._initialize_if_necessary()

        kernels = self._get_current_buf_kernels(True)
        assert kernels is not None

        kernel = None
        for k in kernels:
            if k.kernel_id == kernel_name:
                kernel = k
                break
        if kernel is None:
            raise MoltenException(f"Kernel {kernel_name} not found")

        bufno = self.nvim.current.buffer.number
        cell = CodeCell(
            self.nvim,
            DynamicPosition(self.nvim, self.extmark_namespace, bufno, 0, 0),
            DynamicPosition(self.nvim, self.extmark_namespace, bufno, 0, 0, right_gravity=True),
        )

        kernel.run_code(expr, cell)

    def _get_sorted_buf_cells(self, kernels: List[MoltenKernel], bufnr: int) -> List[CodeCell]:
        return sorted([x for x in chain(*[k.outputs.keys() for k in kernels]) if x.bufno == bufnr])

    def _find_magic_cell_boundaries(self, bufnr: int) -> List[Tuple[int, int]]:
        """查找缓冲区中所有由 #%% 分隔的cell边界
        
        Returns:
            List[Tuple[int, int]]: 每个tuple包含(开始行号, 结束行号)的列表
        """
        lines = self.nvim.api.buf_get_lines(bufnr, 0, -1, False)
        cell_boundaries = []
        cell_starts = []
        
        # 查找所有 #%% 标记的行
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if stripped_line.startswith('#%%'):
                cell_starts.append(i)
        
        # 如果没有找到任何cell标记，返回空列表
        if not cell_starts:
            return []
        
        # 生成cell边界对
        for i in range(len(cell_starts)):
            start_line = cell_starts[i]
            # 下一个cell的开始就是当前cell的结束
            if i + 1 < len(cell_starts):
                end_line = cell_starts[i + 1] - 1
            else:
                # 最后一个cell延续到文件末尾
                end_line = len(lines) - 1
            
            # 确保有有效的cell内容（至少包含魔法命令行）
            if end_line >= start_line:
                cell_boundaries.append((start_line, end_line))
        
        return cell_boundaries

    def _find_current_magic_cell(self, bufnr: int, cursor_line: int) -> Optional[Tuple[int, int]]:
        """查找cursor所在的魔法cell
        
        Args:
            bufnr: 缓冲区编号
            cursor_line: cursor所在的行号 (0-based)
            
        Returns:
            Optional[Tuple[int, int]]: 如果找到，返回(开始行号, 结束行号)，否则返回None
        """
        cell_boundaries = self._find_magic_cell_boundaries(bufnr)
        
        for start_line, end_line in cell_boundaries:
            if start_line <= cursor_line <= end_line:
                return (start_line, end_line)
        
        return None

    @pynvim.command("MoltenDeinit", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_deinit(self) -> None:
        self._initialize_if_necessary()

        kernels = self._get_current_buf_kernels(True)
        assert kernels is not None

        self._clear_interface()

        self._deinit_buffer(kernels)

    @pynvim.command("MoltenInfo", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_info(self) -> None:
        create_info_window(self.nvim, self.molten_kernels, self.buffers, self.initialized)

    def _do_evaluate(self, kernel_name: str, pos: Tuple[Tuple[int, int], Tuple[int, int]]) -> None:
        self._initialize_if_necessary()

        kernels = self._get_current_buf_kernels(True)
        assert kernels is not None

        kernel = None
        for k in kernels:
            if k.kernel_id == kernel_name:
                kernel = k
                break
        if kernel is None:
            raise MoltenException(f"Kernel {kernel_name} not found")

        bufno = self.nvim.current.buffer.number
        span = CodeCell(
            self.nvim,
            DynamicPosition(self.nvim, self.extmark_namespace, bufno, *pos[0]),
            DynamicPosition(self.nvim, self.extmark_namespace, bufno, *pos[1], right_gravity=True),
        )

        code = span.get_text(self.nvim)

        # delete overlapping cells from other kernels. Maintains the invariant that all code cells
        # from different kernels are disjoint
        for k in kernels:
            if k.kernel_id != kernel.kernel_id:
                if not k.try_delete_overlapping_cells(span):
                    return

        kernel.run_code(code, span)

    @pynvim.function("MoltenUpdateOption", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def function_update_option(self, args) -> None:
        self._initialize_if_necessary()

        if len(args) == 2:
            option, value = args
            self.options.update_option(option, value)
        else:
            notify_error(
                self.nvim,
                f"Wrong number of arguments passed to :MoltenUpdateOption, expected 2, given {len(args)}",
            )

    @pynvim.function("MoltenAvailableKernels", sync=True)  # type: ignore
    def function_available_kernels(self, _):
        """List of string kernel names that molten knows about"""
        return get_available_kernels()

    @pynvim.function("MoltenRunningKernels", sync=True)  # type: ignore
    def function_list_running_kernels(self, args: List[Optional[bool]]) -> List[str]:
        """List all the running kernels. When passed [True], returns only buf local kernels"""
        if not self.initialized:
            return []
        if len(args) > 0 and args[0]:
            buf = self.nvim.current.buffer.number
            if buf not in self.buffers:
                return []
            return [x.kernel_id for x in self.buffers[buf]]
        return list(self.molten_kernels.keys())

    @pynvim.function("MoltenStatusLineKernels", sync=True)  # type: ignore
    def function_status_line_kernels(self, args) -> str:
        kernels = self.function_list_running_kernels(args)
        return " ".join(kernels)

    @pynvim.function("MoltenStatusLineInit", sync=True)  # type: ignore
    def function_status_line_init(self, _) -> str:
        if self.initialized:
            return "Molten"
        return ""

    @pynvim.command("MoltenNext", sync=True, nargs="*")  # type: ignore
    @nvimui
    def command_next(self, args: List[str]) -> None:
        count = 1
        if len(args) > 0:
            try:
                count = int(args[0])
            except ValueError:
                count = 1

        c = self.nvim.api.win_get_cursor(0)
        bufnr = self.nvim.current.buffer.number
        pos = Position(bufnr, c[0] - 1, c[1])
        kernels = self._get_current_buf_kernels(True)
        assert kernels is not None

        all_cells = self._get_sorted_buf_cells(kernels, bufnr)

        starting_index = None
        match all_cells:
            case [first, *_] if pos < first.begin:
                starting_index = 0
                if count > 0:
                    count -= 1
            case [*_, last] if last.end < pos:
                starting_index = len(all_cells) - 1
                if count < 0:
                    count += 1
            case _:
                for i, cell in enumerate(all_cells):
                    if pos in cell or (
                        i <= len(all_cells) - 2 and pos < all_cells[i + 1].begin and cell.end < pos
                    ):
                        starting_index = i

        if starting_index is not None:
            target_idx = (starting_index + count) % len(all_cells)
            target_pos = all_cells[target_idx].begin
            self.nvim.api.win_set_cursor(0, (target_pos.lineno + 1, target_pos.colno))
        else:
            notify_warn(self.nvim, "No cells to jump to")

    @pynvim.command("MoltenGoto", sync=True, nargs="*")  # type: ignore
    @nvimui
    def command_goto(self, args: List[str]) -> None:
        count = 1
        if len(args) > 0:
            try:
                count = int(args[0])
            except ValueError:
                count = 1

        kernels = self._get_current_buf_kernels(True)
        assert kernels is not None

        all_cells = self._get_sorted_buf_cells(kernels, self.nvim.current.buffer.number)
        if len(all_cells) == 0:
            notify_warn(self.nvim, "No cells to jump to")
            return

        target_pos = all_cells[(count - 1) % len(all_cells)].begin
        self.nvim.api.win_set_cursor(0, (target_pos.lineno + 1, target_pos.colno))

    @pynvim.command("MoltenPrev", sync=True, nargs="*")  # type: ignore
    @nvimui
    def command_prev(self, args: List[str]) -> None:
        count = -1
        if len(args) > 0:
            try:
                count = -int(args[0])
            except ValueError:
                count = -1
        self.command_next([str(count)])

    @pynvim.command("MoltenEnterOutput", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_enter_output_window(self) -> None:
        molten_kernels = self._get_current_buf_kernels(True)
        assert molten_kernels is not None

        # We can do this iff we ensure that different kernels don't contain code cells that overlap
        for kernel in molten_kernels:
            kernel.enter_output()

    @pynvim.command("MoltenOpenInBrowser", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_open_in_browser(self) -> None:
        molten_kernels = self._get_current_buf_kernels(True)
        assert molten_kernels is not None

        for kernel in molten_kernels:
            if kernel.open_in_browser():
                notify_info(self.nvim, "Opened in browser")
                return

    @pynvim.command("MoltenImagePopup", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_image_popup(self) -> None:
        molten_kernels = self._get_current_buf_kernels(True)
        assert molten_kernels is not None

        for kernel in molten_kernels:
            if kernel.open_image_popup():
                return

    @pynvim.command("MoltenEvaluateArgument", nargs="*", sync=True)  # type: ignore
    @nvimui
    def commnand_molten_evaluate_argument(self, args: List[str]) -> None:
        if len(args) > 0 and args[0] in map(
            lambda x: x.kernel_id, self.buffers[self.nvim.current.buffer.number]
        ):
            self._do_evaluate_expr(args[0], " ".join(args[1:]))
        else:
            self.kernel_check(
                f"MoltenEvaluateArgument %k {' '.join(args)}", self.nvim.current.buffer
            )

    @pynvim.command("MoltenEvaluateVisual", nargs="*", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_evaluate_visual(self, args) -> None:
        if len(args) > 0:
            kernel = args[0]
        else:
            self.kernel_check("MoltenEvaluateVisual %k", self.nvim.current.buffer)
            return
        _, lineno_begin, colno_begin, _ = self.nvim.funcs.getpos("'<")
        _, lineno_end, colno_end, _ = self.nvim.funcs.getpos("'>")

        if lineno_begin == 0 or colno_begin == 0 or lineno_end == 0 or colno_end == 0:
            notify_error(self.nvim, "No visual selection found")
            return

        span = (
            (
                lineno_begin - 1,
                min(colno_begin, len(self.nvim.funcs.getline(lineno_begin))) - 1,
            ),
            (
                lineno_end - 1,
                min(colno_end, len(self.nvim.funcs.getline(lineno_end))),
            ),
        )

        self._do_evaluate(kernel, span)

    @pynvim.function("MoltenEvaluateRange", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def evaulate_range(self, args) -> None:
        start_col, end_col = 1, 0
        kernel = None
        span = args
        if type(args[0]) == str:
            kernel = args[0]
            span = args[1:]

        if len(span) == 2:
            start_line, end_line = span
        elif len(span) == 4:
            start_line, end_line, start_col, end_col = span
        else:
            notify_error(self.nvim, f"Invalid args passed to MoltenEvaluateRange. Got: {args}")
            return

        if not kernel:
            self.kernel_check(
                f"call MoltenEvaluateRange('%k', {start_line}, {end_line}, {start_col}, {end_col})",
                self.nvim.current.buffer,
            )
            return

        span = (
            (start_line - 1, start_col - 1),
            (end_line - 1, end_col - 1),
        )

        self._do_evaluate(kernel.strip(), span)

    @pynvim.command("MoltenEvaluateOperator", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_evaluate_operator(self) -> None:
        self._initialize_if_necessary()

        self.nvim.options["operatorfunc"] = "MoltenOperatorfunc"
        self.nvim.feedkeys("g@")

    @pynvim.command("MoltenEvaluateLine", nargs="*", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_evaluate_line(self, args: List[str]) -> None:
        _, lineno, _, _, _ = self.nvim.funcs.getcurpos()
        lineno -= 1

        span = ((lineno, 0), (lineno, -1))

        if len(args) > 0 and args[0]:
            self._do_evaluate(args[0], span)
        else:
            self.kernel_check("MoltenEvaluateLine %k", self.nvim.current.buffer)

    @pynvim.command("MoltenEvaluateMagicCell", nargs="*", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_evaluate_magic_cell(self, args: List[str]) -> None:
        """运行cursor所在的魔法cell（由#%%分隔的代码块）"""
        _, lineno, _, _, _ = self.nvim.funcs.getcurpos()
        cursor_line = lineno - 1  # 转换为0-based行号
        bufnr = self.nvim.current.buffer.number
        
        # 查找当前cursor所在的魔法cell
        cell_boundaries = self._find_current_magic_cell(bufnr, cursor_line)
        if cell_boundaries is None:
            notify_error(self.nvim, "Cursor不在任何魔法cell中。请确保代码被#%%标记包围。")
            return
        
        start_line, end_line = cell_boundaries
        
        # 跳过魔法命令行本身，从下一行开始执行
        # 如果魔法命令行后面还有内容，则从魔法命令行的下一行开始
        code_start_line = start_line + 1
        if code_start_line > end_line:
            notify_warn(self.nvim, "魔法cell中没有可执行的代码。")
            return
        
        # 创建span用于执行
        span = (
            (code_start_line, 0),
            (end_line, -1)
        )
        
        if len(args) > 0 and args[0]:
            self._do_evaluate(args[0], span)
        else:
            self.kernel_check("MoltenEvaluateMagicCell %k", self.nvim.current.buffer)

    @pynvim.command("MoltenNextMagicCell", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_next_magic_cell(self) -> None:
        """跳转到下一个魔法cell"""
        _, lineno, _, _, _ = self.nvim.funcs.getcurpos()
        cursor_line = lineno - 1  # 转换为0-based行号
        bufnr = self.nvim.current.buffer.number
        
        cell_boundaries = self._find_magic_cell_boundaries(bufnr)
        if not cell_boundaries:
            notify_warn(self.nvim, "当前缓冲区中没有找到魔法cell。")
            return
        
        # 查找下一个cell
        next_cell = None
        for start_line, end_line in cell_boundaries:
            if start_line > cursor_line:
                next_cell = (start_line, end_line)
                break
        
        if next_cell is None:
            # 如果没有下一个cell，跳转到第一个cell（循环）
            next_cell = cell_boundaries[0]
        
        # 跳转到cell的开始位置
        self.nvim.api.win_set_cursor(0, (next_cell[0] + 1, 0))

    @pynvim.command("MoltenPrevMagicCell", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_prev_magic_cell(self) -> None:
        """跳转到上一个魔法cell"""
        _, lineno, _, _, _ = self.nvim.funcs.getcurpos()
        cursor_line = lineno - 1  # 转换为0-based行号
        bufnr = self.nvim.current.buffer.number
        
        cell_boundaries = self._find_magic_cell_boundaries(bufnr)
        if not cell_boundaries:
            notify_warn(self.nvim, "当前缓冲区中没有找到魔法cell。")
            return
        
        # 查找上一个cell
        prev_cell = None
        for start_line, end_line in reversed(cell_boundaries):
            if start_line < cursor_line:
                prev_cell = (start_line, end_line)
                break
        
        if prev_cell is None:
            # 如果没有上一个cell，跳转到最后一个cell（循环）
            prev_cell = cell_boundaries[-1]
        
        # 跳转到cell的开始位置
        self.nvim.api.win_set_cursor(0, (prev_cell[0] + 1, 0))

    @pynvim.command("MoltenToggleGlobalVirtText", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_toggle_global_virt_text(self) -> None:
        """全局开关虚拟文本输出功能"""
        self._initialize_if_necessary()
        
        # 切换全局设置
        current_value = self.options.virt_text_output
        new_value = not current_value
        
        # 更新选项
        self.options.update_option("virt_text_output", new_value)
        
        # 同时更新nvim全局变量，以便新的molten实例使用新设置
        self.nvim.vars["molten_virt_text_output"] = new_value
        
        # 获取所有kernel并应用新设置
        if new_value:
            # 启用虚拟文本输出 - 显示所有cell的虚拟输出
            for molten_kernels in self.buffers.values():
                for kernel in molten_kernels:
                    for cell, output in kernel.outputs.items():
                        output.virt_hidden = False
                        output.show_virtual_output(cell.end)
            notify_info(self.nvim, "✅ 虚拟文本输出已启用")
        else:
            # 禁用虚拟文本输出 - 清除所有虚拟输出
            for molten_kernels in self.buffers.values():
                for kernel in molten_kernels:
                    for cell, output in kernel.outputs.items():
                        output.clear_virt_output(cell.bufno)
            notify_info(self.nvim, "❌ 虚拟文本输出已禁用")

    @pynvim.command("MoltenRefreshVirtText", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_refresh_virt_text(self) -> None:
        """刷新所有虚拟文本输出的显示"""
        self._initialize_if_necessary()
        
        kernels = self._get_current_buf_kernels(False)
        if kernels is None:
            notify_warn(self.nvim, "当前缓冲区没有活跃的molten kernel")
            return
        
        if not self.options.virt_text_output:
            notify_warn(self.nvim, "虚拟文本输出功能未启用。使用 :MoltenToggleGlobalVirtText 启用")
            return
        
        refresh_count = 0
        for kernel in kernels:
            for cell, output in kernel.outputs.items():
                # 先清除现有的虚拟输出
                output.clear_virt_output(cell.bufno)
                # 重新显示虚拟输出
                output.virt_hidden = False
                output.show_virtual_output(cell.end)
                refresh_count += 1
        
        notify_info(self.nvim, f"🔄 已刷新 {refresh_count} 个cell的虚拟文本输出")

    @pynvim.command("MoltenVirtTextStatus", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_virt_text_status(self) -> None:
        """显示虚拟文本输出的当前状态"""
        self._initialize_if_necessary()
        
        # 显示全局设置状态
        global_status = "启用" if self.options.virt_text_output else "禁用"
        
        kernels = self._get_current_buf_kernels(False)
        if kernels is None:
            notify_info(self.nvim, f"📊 虚拟文本输出全局状态: {global_status} | 当前缓冲区: 无活跃kernel")
            return
        
        # 统计当前缓冲区的虚拟输出状态
        total_cells = 0
        visible_cells = 0
        hidden_cells = 0
        
        for kernel in kernels:
            for cell, output in kernel.outputs.items():
                total_cells += 1
                if output.virt_text_id is not None and not output.virt_hidden:
                    visible_cells += 1
                else:
                    hidden_cells += 1
        
        status_msg = f"📊 虚拟文本状态: {global_status} | 总计: {total_cells} | 可见: {visible_cells} | 隐藏: {hidden_cells}"
        notify_info(self.nvim, status_msg)

    @pynvim.command("MoltenToggleBufferVirtText", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_toggle_buffer_virt_text(self) -> None:
        """切换当前缓冲区的虚拟文本输出显示"""
        self._initialize_if_necessary()
        
        kernels = self._get_current_buf_kernels(True)
        assert kernels is not None
        
        if not self.options.virt_text_output:
            notify_warn(self.nvim, "虚拟文本输出功能未启用。使用 :MoltenToggleGlobalVirtText 启用")
            return
        
        # 检查当前缓冲区是否有可见的虚拟输出
        has_visible = False
        total_cells = 0
        
        for kernel in kernels:
            for cell, output in kernel.outputs.items():
                total_cells += 1
                if output.virt_text_id is not None and not output.virt_hidden:
                    has_visible = True
                    break
            if has_visible:
                break
        
        if total_cells == 0:
            notify_warn(self.nvim, "当前缓冲区没有执行过的cell")
            return
        
        # 根据当前状态切换
        if has_visible:
            # 隐藏所有虚拟输出
            for kernel in kernels:
                for cell, output in kernel.outputs.items():
                    output.clear_virt_output(cell.bufno)
            notify_info(self.nvim, f"❌ 已隐藏当前缓冲区的 {total_cells} 个cell的虚拟文本输出")
        else:
            # 显示所有虚拟输出
            for kernel in kernels:
                for cell, output in kernel.outputs.items():
                    output.virt_hidden = False
                    output.show_virtual_output(cell.end)
            notify_info(self.nvim, f"✅ 已显示当前缓冲区的 {total_cells} 个cell的虚拟文本输出")

    @pynvim.command("MoltenShowAllVirtText", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_show_all_virt_text(self) -> None:
        """强制显示当前缓冲区所有cell的虚拟文本输出"""
        self._initialize_if_necessary()
        
        kernels = self._get_current_buf_kernels(True)
        assert kernels is not None
        
        if not self.options.virt_text_output:
            notify_warn(self.nvim, "虚拟文本输出功能未启用。使用 :MoltenToggleGlobalVirtText 启用")
            return
        
        show_count = 0
        for kernel in kernels:
            for cell, output in kernel.outputs.items():
                output.virt_hidden = False
                output.show_virtual_output(cell.end)
                show_count += 1
        
        if show_count > 0:
            notify_info(self.nvim, f"✅ 已强制显示 {show_count} 个cell的虚拟文本输出")
        else:
            notify_warn(self.nvim, "当前缓冲区没有可显示的cell输出")

    @pynvim.command("MoltenHideAllVirtText", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_hide_all_virt_text(self) -> None:
        """隐藏当前缓冲区所有cell的虚拟文本输出"""
        self._initialize_if_necessary()
        
        kernels = self._get_current_buf_kernels(True)
        assert kernels is not None
        
        hide_count = 0
        for kernel in kernels:
            for cell, output in kernel.outputs.items():
                if output.virt_text_id is not None:
                    output.clear_virt_output(cell.bufno)
                    hide_count += 1
        
        if hide_count > 0:
            notify_info(self.nvim, f"❌ 已隐藏 {hide_count} 个cell的虚拟文本输出")
        else:
            notify_info(self.nvim, "当前缓冲区没有可见的虚拟文本输出")

    @pynvim.command("MoltenToggleMagicCellVirtText", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_toggle_magic_cell_virt_text(self) -> None:
        """切换当前魔法cell的虚拟文本输出显示"""
        self._initialize_if_necessary()
        
        kernels = self._get_current_buf_kernels(True)
        assert kernels is not None
        
        if not self.options.virt_text_output:
            notify_warn(self.nvim, "虚拟文本输出功能未启用。使用 :MoltenToggleGlobalVirtText 启用")
            return
        
        # 获取当前cursor位置和魔法cell边界
        _, lineno, _, _, _ = self.nvim.funcs.getcurpos()
        cursor_line = lineno - 1  # 转换为0-based行号
        bufnr = self.nvim.current.buffer.number
        
        cell_boundaries = self._find_current_magic_cell(bufnr, cursor_line)
        if cell_boundaries is None:
            notify_error(self.nvim, "Cursor不在任何魔法cell中。请确保代码被#%%标记包围。")
            return
        
        start_line, end_line = cell_boundaries
        
        # 查找在这个魔法cell范围内的所有molten cell
        magic_cell_outputs = []
        for kernel in kernels:
            for cell, output in kernel.outputs.items():
                cell_start = cell.begin.lineno
                cell_end = cell.end.lineno
                # 检查molten cell是否在魔法cell范围内
                if (start_line <= cell_start <= end_line) or (start_line <= cell_end <= end_line):
                    magic_cell_outputs.append((cell, output))
        
        if not magic_cell_outputs:
            notify_warn(self.nvim, "当前魔法cell中没有已执行的molten cell")
            return
        
        # 检查是否有可见的虚拟输出
        has_visible = any(
            output.virt_text_id is not None and not output.virt_hidden 
            for cell, output in magic_cell_outputs
        )
        
        # 根据当前状态切换
        if has_visible:
            # 隐藏魔法cell中的所有虚拟输出
            for cell, output in magic_cell_outputs:
                output.clear_virt_output(cell.bufno)
            notify_info(self.nvim, f"❌ 已隐藏当前魔法cell中 {len(magic_cell_outputs)} 个molten cell的虚拟文本输出")
        else:
            # 显示魔法cell中的所有虚拟输出
            for cell, output in magic_cell_outputs:
                output.virt_hidden = False
                output.show_virtual_output(cell.end)
            notify_info(self.nvim, f"✅ 已显示当前魔法cell中 {len(magic_cell_outputs)} 个molten cell的虚拟文本输出")

    @pynvim.command("MoltenToggleMagicCellOutput", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_toggle_magic_cell_output(self) -> None:
        """切换当前魔法cell的浮动窗口输出显示"""
        self._initialize_if_necessary()
        
        kernels = self._get_current_buf_kernels(True)
        assert kernels is not None
        
        # 获取当前cursor位置和魔法cell边界
        _, lineno, _, _, _ = self.nvim.funcs.getcurpos()
        cursor_line = lineno - 1  # 转换为0-based行号
        bufnr = self.nvim.current.buffer.number
        
        cell_boundaries = self._find_current_magic_cell(bufnr, cursor_line)
        if cell_boundaries is None:
            notify_error(self.nvim, "Cursor不在任何魔法cell中。请确保代码被#%%标记包围。")
            return
        
        start_line, end_line = cell_boundaries
        
        # 查找在这个魔法cell范围内的所有molten cell
        magic_cell_outputs = []
        for kernel in kernels:
            for cell, output in kernel.outputs.items():
                cell_start = cell.begin.lineno
                cell_end = cell.end.lineno
                # 检查molten cell是否在魔法cell范围内
                if (start_line <= cell_start <= end_line) or (start_line <= cell_end <= end_line):
                    magic_cell_outputs.append((cell, output))
        
        if not magic_cell_outputs:
            notify_warn(self.nvim, "当前魔法cell中没有已执行的molten cell")
            return
        
        # 检查是否有打开的浮动窗口
        has_open_windows = any(
            output.display_win is not None and output.display_win.valid
            for cell, output in magic_cell_outputs
        )
        
        # 根据当前状态切换
        if has_open_windows:
            # 关闭魔法cell中的所有浮动窗口
            for cell, output in magic_cell_outputs:
                output.clear_float_win()
            notify_info(self.nvim, f"❌ 已关闭当前魔法cell中 {len(magic_cell_outputs)} 个molten cell的浮动窗口输出")
        else:
            # 显示魔法cell中的所有浮动窗口
            for cell, output in magic_cell_outputs:
                output.show_floating_win(cell.end)
            notify_info(self.nvim, f"✅ 已显示当前魔法cell中 {len(magic_cell_outputs)} 个molten cell的浮动窗口输出")

    @pynvim.command("MoltenToggleGlobalOutput", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_toggle_global_output(self) -> None:
        """全局开关浮动窗口输出功能"""
        self._initialize_if_necessary()
        
        # 获取所有kernel
        if not self.molten_kernels:
            notify_warn(self.nvim, "没有活跃的molten kernel")
            return
        
        # 检查是否有打开的浮动窗口
        has_open_windows = False
        all_outputs = []
        
        for kernel in self.molten_kernels.values():
            for cell, output in kernel.outputs.items():
                all_outputs.append((cell, output))
                if output.display_win is not None and output.display_win.valid:
                    has_open_windows = True
        
        if not all_outputs:
            notify_warn(self.nvim, "没有已执行的cell")
            return
        
        # 根据当前状态切换
        if has_open_windows:
            # 关闭所有浮动窗口
            for cell, output in all_outputs:
                output.clear_float_win()
            notify_info(self.nvim, f"❌ 已关闭所有 {len(all_outputs)} 个cell的浮动窗口输出")
        else:
            # 显示所有浮动窗口
            for cell, output in all_outputs:
                output.show_floating_win(cell.end)
            notify_info(self.nvim, f"✅ 已显示所有 {len(all_outputs)} 个cell的浮动窗口输出")

    def kernel_check(self, command: str, buffer: Buffer) -> None:
        """Figure out if there is more than one kernel attached to the given buffer. If there is,
        prompt the user for the kernel name, and run the given command with the new kernel subbed in
        for %k. If there is no kernel, throw an error. If there is one kernel, use it
        """
        self._initialize_if_necessary()

        kernels = self.buffers.get(buffer.number)
        if not kernels and self.options.auto_init_behavior != "raise":
            available_kernels = [(x, False) for x in get_available_kernels()]
            shared_kernels = [(x, True) for x in self.molten_kernels.keys()]
            PROMPT = "You Need to Initialize a Kernel First:"
            self.nvim.lua._prompt_init_and_run(available_kernels + shared_kernels, PROMPT, command)
        elif not kernels:  # and auto_init_behavior == "raise"
            raise MoltenException(
                "Molten is not initialized in this buffer; run `:MoltenInit` to initialize."
            )
        elif len(kernels) == 1:
            import re
            pat = r'(^|[^\\])%k'
            c = re.sub(pat, lambda x: x[1] + kernels[0].kernel_id, command)
            c = c.replace(r"\%k", "%k") # un-escape escaped chars
            self.nvim.command(c)
        else:
            PROMPT = "Please select a kernel:"
            available_kernels = [kernel.kernel_id for kernel in kernels]
            self.nvim.lua._select_and_run(available_kernels, PROMPT, command)

    @pynvim.command("MoltenReevaluateAll", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_reevaluate_all(self) -> None:
        molten_kernels = self._get_current_buf_kernels(True)
        assert molten_kernels is not None

        for kernel in molten_kernels:
            kernel.reevaluate_all()

    @pynvim.command("MoltenReevaluateCell", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_evaluate_cell(self) -> None:
        molten_kernels = self._get_current_buf_kernels(True)
        assert molten_kernels is not None

        # we can do this iff we ensure that different kernels don't contain code cells that overlap
        in_cell = False
        for kernel in molten_kernels:
            if kernel.reevaluate_cell():
                in_cell = True

        if not in_cell:
            notify_error(self.nvim, "Not in a cell")

    @pynvim.command("MoltenInterrupt", nargs="*", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_interrupt(self, args) -> None:
        molten_kernels = self._get_current_buf_kernels(True)
        assert molten_kernels is not None

        if len(args) > 0:
            kernel = args[0]
        else:
            self.kernel_check("MoltenInterrupt %k", self.nvim.current.buffer)
            return

        for molten in molten_kernels:
            if molten.kernel_id == kernel:
                molten.interrupt()
                return

        notify_error(self.nvim, f"Unable to find kernel: {kernel}")

    @pynvim.command("MoltenRestart", nargs="*", sync=True, bang=True)  # type: ignore
    @nvimui  # type: ignore
    def command_restart(self, args, bang) -> None:
        molten_kernels = self._get_current_buf_kernels(True)
        assert molten_kernels is not None

        if len(args) > 0:
            kernel = args[0]
        else:
            self.kernel_check(f"MoltenRestart{'!' if bang else ''} %k", self.nvim.current.buffer)
            return

        for molten in molten_kernels:
            if molten.kernel_id == kernel:
                molten.restart(delete_outputs=bang)
                return
        notify_error(self.nvim, f"Unable to find kernel: {kernel}")

    @pynvim.command("MoltenDelete", nargs=0, sync=True, bang=True)  # type: ignore
    @nvimui  # type: ignore
    def command_delete(self, bang) -> None:
        molten_kernels = self._get_current_buf_kernels(True)
        assert molten_kernels is not None

        for molten in molten_kernels:
            if bang:
                # Delete all cells in current buffer
                molten.clear_buffer(self.nvim.current.buffer.number)
            elif molten.selected_cell is not None:
                molten.delete_current_cell()
                return

    @pynvim.command("MoltenShowOutput", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_show_output(self) -> None:
        self._initialize_if_necessary()

        molten_kernels = self._get_current_buf_kernels(True)
        assert molten_kernels is not None

        for molten in molten_kernels:
            molten.should_show_floating_win = True
            # Show output for selected cell if it exists
            if molten.selected_cell is not None and molten.selected_cell in molten.outputs:
                molten.outputs[molten.selected_cell].show_floating_win(molten.selected_cell.end)
            self._update_interface()

    @pynvim.command("MoltenHideOutput", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_hide_output(self) -> None:
        molten_kernels = self._get_current_buf_kernels(False)
        if molten_kernels is None:
            # get the current buffer, and then search for it in all molten buffers
            cur_buf = self.nvim.current.buffer
            for moltenbuf in self.buffers.values():
                # if we find it, then we know this is a molten output, and we can safely quit and
                # call hide to hide it
                output_windows = map(
                    lambda x: x.display_buf, chain(*[o.outputs.values() for o in moltenbuf])
                )
                if cur_buf in output_windows:
                    self.nvim.command("q")
                    self.nvim.command(":MoltenHideOutput")
                    return
            return

        for molten in molten_kernels:
            molten.should_show_floating_win = False
            # Also clear all output windows explicitly
            for output_buffer in molten.outputs.values():
                output_buffer.clear_float_win()

        self._update_interface()

    @pynvim.command("MoltenImportOutput", nargs="*", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_import(self, args) -> None:
        self._initialize_if_necessary()

        buf = self.nvim.current.buffer
        if len(args) > 0:
            path = args[0]
        else:
            path = get_default_import_export_file(self.nvim, buf)

        if len(args) > 1:
            kernel = args[1]
        else:
            path = path.replace("%k", r"\%k")
            self.kernel_check(f"MoltenImportOutput {path} %k", buf)
            return

        kernels = self._get_current_buf_kernels(True)
        assert kernels is not None
        for molten in kernels:
            if molten.kernel_id == kernel:
                import_outputs(self.nvim, molten, path)
                break

    @pynvim.command("MoltenExportOutput", nargs="*", sync=True, bang=True)  # type: ignore
    @nvimui  # type: ignore
    def command_export(self, args, bang: bool) -> None:
        kernels = self._get_current_buf_kernels(True)
        assert kernels is not None

        buf = self.nvim.current.buffer
        if len(args) > 0:
            path = args[0]
        else:
            path = get_default_import_export_file(self.nvim, buf)

        if len(args) > 1:
            kernel = args[1]
        else:
            path = path.replace("%k", r"\%k")
            self.kernel_check(f"MoltenExportOutput{'!' if bang else ''} {path} %k", buf)
            return

        for molten in kernels:
            if molten.kernel_id == kernel:
                export_outputs(self.nvim, molten, path, bang)
                break

    @pynvim.command("MoltenSave", nargs="*", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_save(self, args) -> None:
        kernels = self._get_current_buf_kernels(True)
        assert kernels is not None

        buf = self.nvim.current.buffer
        if len(args) > 0:
            path = args[0]
        else:
            path = get_default_save_file(self.options, buf)

        if len(args) > 1:
            kernel = args[1]
        else:
            path = path.replace("%k", r"\%k")
            self.kernel_check(f"MoltenSave {path} %k", buf)
            return

        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        for molten in kernels:
            if molten.kernel_id == kernel:
                with open(path, "w") as file:
                    json.dump(save(molten, buf.number), file)
                break
        notify_info(self.nvim, f"Saved kernel `{kernel}` to: {path}")

    @pynvim.command("MoltenLoad", nargs="*", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_load(self, args) -> None:
        self._initialize_if_necessary()

        shared = False

        if len(args) > 0 and args[0] == "shared":
            shared = True
            args = args[1:]

        if len(args) > 0:
            path = args[0]
        else:
            path = get_default_save_file(self.options, self.nvim.current.buffer)

        if self.nvim.current.buffer.number in self.buffers:
            raise MoltenException(
                "Molten is already initialized for this buffer; MoltenLoad initializes Molten."
            )

        with open(path) as file:
            data = json.load(file)

        molten = None

        try:
            notify_info(self.nvim, f"Attempting to load from: {path}")

            MoltenIOError.assert_has_key(data, "version", int)
            if (version := data["version"]) != 1:
                raise MoltenIOError(f"Bad version: {version}")

            MoltenIOError.assert_has_key(data, "kernel", str)
            kernel_name = data["kernel"]

            molten = self._initialize_buffer(kernel_name, shared=shared)
            if molten:
                load(self.nvim, molten, self.nvim.current.buffer, data)

                self._update_interface()
        except MoltenIOError as err:
            if molten is not None:
                self._deinit_buffer([molten])

            raise MoltenException("Error while doing Molten IO: " + str(err))

    # Internal functions which are exposed to VimScript

    @pynvim.function("MoltenBufLeave", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def function_clear_interface(self, _: List[Any]) -> None:
        self._clear_on_buf_leave()

    @pynvim.function("MoltenOnBufferUnload", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def function_on_buffer_unload(self, _: Any) -> None:
        abuf_str = self.nvim.funcs.expand("<abuf>")
        if not abuf_str:
            return

        molten = self.buffers.get(int(abuf_str))
        if molten is None:
            return

        self._deinit_buffer(molten)

    @pynvim.function("MoltenOnExitPre", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def function_on_exit_pre(self, _: Any) -> None:
        self._deinitialize()

    @pynvim.function("MoltenTick", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def function_molten_tick(self, _: Any) -> None:
        self._initialize_if_necessary()

        molten_kernels = self._get_current_buf_kernels(False)
        if molten_kernels is None:
            return

        for m in molten_kernels:
            m.tick()

    @pynvim.function("MoltenTickInput", sync=False)  # type: ignore
    @nvimui  # type: ignore
    def function_molten_tick_input(self, _: Any) -> None:
        self._initialize_if_necessary()

        molten_kernels = self._get_current_buf_kernels(False)
        if molten_kernels is None:
            return

        for m in molten_kernels:
            m.tick_input()

    @pynvim.function("MoltenSendStdin", sync=False)  # type: ignore
    @nvimui  # type: ignore
    def function_molten_send_stdin(self, args: Tuple[str, str]) -> None:
        molten_kernels = self._get_current_buf_kernels(False)
        if molten_kernels is None:
            return

        for m in molten_kernels:
            if m.kernel_id == args[0]:
                m.send_stdin(args[1])

    @pynvim.function("MoltenUpdateInterface", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def function_update_interface(self, _: Any) -> None:
        self._update_interface()

    @pynvim.function("MoltenOnCursorMoved", sync=True)
    @nvimui
    def function_on_cursor_moved(self, _) -> None:
        self._on_cursor_moved()

    @pynvim.function("MoltenOnWinScrolled", sync=True)
    @nvimui
    def function_on_win_scrolled(self, _) -> None:
        self._on_cursor_moved(scrolled=True)

    @pynvim.function("MoltenOperatorfunc", sync=True)
    @nvimui
    def function_molten_operatorfunc(self, args) -> None:
        if not args:
            return

        kind = args[0]

        _, lineno_begin, colno_begin, _ = self.nvim.funcs.getpos("'[")
        _, lineno_end, colno_end, _ = self.nvim.funcs.getpos("']")

        if kind == "line":
            colno_begin = 1
            colno_end = 0
        elif kind == "char":
            colno_begin = min(colno_begin, len(self.nvim.funcs.getline(lineno_begin)))
            colno_end = min(colno_end, len(self.nvim.funcs.getline(lineno_end))) + 1
        else:
            raise MoltenException(f"this kind of selection is not supported: '{kind}'")

        span = (
            (lineno_begin, colno_begin),
            (lineno_end, colno_end),
        )

        self.kernel_check(
            f"call MoltenEvaluateRange('%k', {span[0][0]}, {span[1][0]}, {span[0][1]}, {span[1][1]})",
            self.nvim.current.buffer,
        )

    @pynvim.function("MoltenDefineCell", sync=True)
    def function_molten_define_cell(self, args: List[int]) -> None:
        if not args:
            return

        molten_kernels = self._get_current_buf_kernels(True)
        assert molten_kernels is not None
        assert self.canvas is not None

        start = args[0]
        end = args[1]

        if len(args) == 3:
            kernel = args[2]
        elif len(self.buffers[self.nvim.current.buffer.number]) == 1:
            kernel = self.buffers[self.nvim.current.buffer.number][0].kernel_id
        else:
            raise MoltenException(
                "MoltenDefineCell called without a kernel argument while multiple kernels are active"
            )

        bufno = self.nvim.current.buffer.number
        span = CodeCell(
            self.nvim,
            DynamicPosition(self.nvim, self.extmark_namespace, bufno, start - 1, 0),
            DynamicPosition(
                self.nvim, self.extmark_namespace, bufno, end - 1, -1, right_gravity=True
            ),
        )

        for molten in molten_kernels:
            if molten.kernel_id == kernel:
                molten.outputs[span] = OutputBuffer(
                    self.nvim, self.canvas, molten.extmark_namespace, self.options
                )
                break

    @pynvim.command("MoltenShowOutline", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_show_outline(self) -> None:
        """显示当前缓冲区的magic cell outline"""
        self._initialize_if_necessary()
        
        # 获取当前缓冲区的内容
        bufnr = self.nvim.current.buffer.number
        lines = self.nvim.api.buf_get_lines(bufnr, 0, -1, False)
        
        # 解析outline
        outline_items = self.outline_parser.parse_buffer_outline(lines)
        
        if not outline_items:
            notify_warn(self.nvim, "当前缓冲区中没有找到magic cell")
            return
        
        # 显示outline窗口
        buffer_name = self.nvim.api.buf_get_name(bufnr)
        title = f"Outline: {os.path.basename(buffer_name)}"
        self.outline_renderer.show_outline(outline_items, title)
        
        notify_info(self.nvim, f"显示了 {len(outline_items)} 个magic cell的outline")

    @pynvim.command("MoltenHideOutline", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_hide_outline(self) -> None:
        """隐藏outline窗口"""
        self.outline_renderer.close_outline()
        notify_info(self.nvim, "已关闭outline窗口")

    @pynvim.command("MoltenToggleOutline", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_toggle_outline(self) -> None:
        """切换outline窗口显示"""
        if (self.outline_renderer.outline_win and 
            self.nvim.api.nvim_win_is_valid(self.outline_renderer.outline_win)):
            self.command_hide_outline()
        else:
            self.command_show_outline()

    @pynvim.function("MoltenOutlineGoto", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def function_outline_goto(self, _) -> None:
        """从outline窗口跳转到对应位置"""
        if (not self.outline_renderer.outline_win or 
            not self.nvim.api.nvim_win_is_valid(self.outline_renderer.outline_win)):
            return
        
        # 获取当前行号
        cursor = self.nvim.api.nvim_win_get_cursor(self.outline_renderer.outline_win)
        line_num = cursor[0] - 1  # 转换为0-based
        
        # 跳转到对应位置
        self.outline_renderer.goto_outline_item(line_num)

    @pynvim.function("MoltenOutlineClose", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def function_outline_close(self, _) -> None:
        """关闭outline窗口"""
        self.command_hide_outline()

    @pynvim.command("MoltenGotoMagicCell", nargs="1", sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_goto_magic_cell(self, args: List[str]) -> None:
        """跳转到指定的magic cell"""
        if not args:
            notify_error(self.nvim, "请指定要跳转的cell编号或名称")
            return
        
        target = args[0]
        bufnr = self.nvim.current.buffer.number
        lines = self.nvim.api.buf_get_lines(bufnr, 0, -1, False)
        
        outline_items = self.outline_parser.parse_buffer_outline(lines)
        
        if not outline_items:
            notify_warn(self.nvim, "当前缓冲区中没有找到magic cell")
            return
        
        # 查找目标cell
        target_item = None
        
        # 尝试按编号查找
        try:
            cell_index = int(target) - 1  # 转换为0-based索引
            if 0 <= cell_index < len(outline_items):
                target_item = outline_items[cell_index]
        except ValueError:
            # 按名称查找
            for item in outline_items:
                if target.lower() in item.name.lower():
                    target_item = item
                    break
        
        if target_item:
            # 跳转到目标cell
            self.nvim.api.nvim_win_set_cursor(0, (target_item.line_start + 1, 0))
            notify_info(self.nvim, f"已跳转到: {target_item.name}")
        else:
            notify_error(self.nvim, f"未找到匹配的magic cell: {target}")

    @pynvim.command("MoltenListMagicCells", nargs=0, sync=True)  # type: ignore
    @nvimui  # type: ignore
    def command_list_magic_cells(self) -> None:
        """列出当前缓冲区的所有magic cell"""
        bufnr = self.nvim.current.buffer.number
        lines = self.nvim.api.buf_get_lines(bufnr, 0, -1, False)
        
        outline_items = self.outline_parser.parse_buffer_outline(lines)
        
        if not outline_items:
            notify_warn(self.nvim, "当前缓冲区中没有找到magic cell")
            return
        
        # 构建显示信息
        cell_info = []
        for i, item in enumerate(outline_items):
            func_count = len([child for child in item.children if child.type.value in ['function', 'method']])
            class_count = len([child for child in item.children if child.type.value == 'class'])
            
            info = f"{i+1}. {item.name} (行 {item.line_start+1}-{item.line_end+1})"
            if func_count > 0 or class_count > 0:
                info += f" - {func_count}个函数, {class_count}个类"
            cell_info.append(info)
        
        # 显示信息
        message = f"发现 {len(outline_items)} 个magic cell:\n" + "\n".join(cell_info)
        notify_info(self.nvim, message)

    @pynvim.command("MoltenToggleVirtual", nargs="0", sync=True, bang=True)  # type: ignore
    @nvimui  # type: ignore
    def command_toggle_virtual(self, args: List[Any], bang: bool) -> None:
        """
        Toggle the virtual-text output on/off for the cell under the cursor.
        With a bang (`:MoltenToggleVirtual!`), toggle ALL cells in this buffer.
        """
        kernels = self._get_current_buf_kernels(True)
        assert kernels is not None

        # If called with !, toggle EVERY cell
        if bang:
            # if any cell is currently visible, hide all; otherwise show all
            any_visible = any(
                outbuf.virt_text_id is not None and not outbuf.virt_hidden
                for kern in kernels
                for outbuf in kern.outputs.values()
            )
            for kern in kernels:
                for cell, outbuf in kern.outputs.items():
                    if any_visible:
                        outbuf.clear_virt_output(cell.end.bufno)
                    else:
                        outbuf.virt_hidden = False
                        outbuf.show_virtual_output(cell.end)
            return

        # Otherwise, just toggle the cell under the cursor
        for kern in kernels:
            cell = kern._get_selected_span()
            if cell is not None:
                outbuf = kern.outputs[cell]
                outbuf.toggle_virtual_output(cell.end)
                return
