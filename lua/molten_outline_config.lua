-- Molten Magic Cell Outline配置
-- 提供基于#%%魔法命令的cell outline预览和导航功能

local M = {}

-- 设置outline相关的键盘映射
function M.setup_keymaps()
    local opts = { noremap = true, silent = true }
    
    -- Outline显示控制
    vim.keymap.set('n', '<leader>mo', ':MoltenShowOutline<CR>', 
        vim.tbl_extend('force', opts, { desc = 'Show magic cell outline' }))
    
    vim.keymap.set('n', '<leader>mO', ':MoltenToggleOutline<CR>', 
        vim.tbl_extend('force', opts, { desc = 'Toggle magic cell outline' }))
    
    vim.keymap.set('n', '<leader>mh', ':MoltenHideOutline<CR>', 
        vim.tbl_extend('force', opts, { desc = 'Hide magic cell outline' }))
    
    -- Magic cell导航
    vim.keymap.set('n', '<leader>ml', ':MoltenListMagicCells<CR>', 
        vim.tbl_extend('force', opts, { desc = 'List all magic cells' }))
    
    vim.keymap.set('n', '<leader>mg', ':MoltenGotoMagicCell ', 
        { noremap = true, desc = 'Go to magic cell by number/name' })
    
    -- 快速跳转到特定编号的cell
    for i = 1, 9 do
        vim.keymap.set('n', '<leader>m' .. i, ':MoltenGotoMagicCell ' .. i .. '<CR>', 
            vim.tbl_extend('force', opts, { desc = 'Go to magic cell ' .. i }))
    end
    
    -- 增强的magic cell导航（与现有功能结合）
    vim.keymap.set('n', '<leader>mn', ':MoltenNextMagicCell<CR>', 
        vim.tbl_extend('force', opts, { desc = 'Next magic cell' }))
    
    vim.keymap.set('n', '<leader>mp', ':MoltenPrevMagicCell<CR>', 
        vim.tbl_extend('force', opts, { desc = 'Previous magic cell' }))
    
    -- Magic cell执行
    vim.keymap.set('n', '<leader>mc', ':MoltenEvaluateMagicCell<CR>', 
        vim.tbl_extend('force', opts, { desc = 'Run current magic cell' }))
end

-- 设置outline窗口的自动命令
function M.setup_autocommands()
    local augroup = vim.api.nvim_create_augroup("MoltenOutline", { clear = true })
    
    -- 当切换缓冲区时自动更新outline
    vim.api.nvim_create_autocmd({"BufEnter", "BufWritePost"}, {
        group = augroup,
        pattern = "*.py",
        callback = function()
            -- 检查是否有打开的outline窗口
            local outline_win = vim.fn.exists('*MoltenOutlineIsOpen') and vim.fn.MoltenOutlineIsOpen()
            if outline_win then
                -- 自动刷新outline
                vim.schedule(function()
                    vim.cmd('MoltenShowOutline')
                end)
            end
        end,
        desc = "Auto refresh outline when switching buffers"
    })
    
    -- 文本改变时延迟更新outline
    vim.api.nvim_create_autocmd({"TextChanged", "TextChangedI"}, {
        group = augroup,
        pattern = "*.py",
        callback = function()
            -- 设置延迟更新定时器
            if M.update_timer then
                vim.fn.timer_stop(M.update_timer)
            end
            
            M.update_timer = vim.fn.timer_start(1000, function()
                local outline_win = vim.fn.exists('*MoltenOutlineIsOpen') and vim.fn.MoltenOutlineIsOpen()
                if outline_win then
                    vim.schedule(function()
                        vim.cmd('MoltenShowOutline')
                    end)
                end
            end)
        end,
        desc = "Auto refresh outline on text changes"
    })
end

-- 设置outline窗口的高亮
function M.setup_highlights()
    -- 定义outline相关的高亮组
    local highlights = {
        MoltenOutlineMagicCell = { fg = '#61AFEF', bold = true },
        MoltenOutlineFunction = { fg = '#C678DD' },
        MoltenOutlineClass = { fg = '#E06C75', bold = true },
        MoltenOutlineMethod = { fg = '#98C379' },
        MoltenOutlineVariable = { fg = '#D19A66' },
    }
    
    for group, opts in pairs(highlights) do
        vim.api.nvim_set_hl(0, group, opts)
    end
end

-- 创建用户命令
function M.setup_commands()
    -- 创建快捷命令
    vim.api.nvim_create_user_command('MoltenOutlineSetup', function()
        M.setup_keymaps()
        M.setup_autocommands()
        M.setup_highlights()
        print("Molten Outline功能已设置完成!")
    end, { desc = 'Setup Molten Outline functionality' })
    
    -- 创建outline配置切换命令
    vim.api.nvim_create_user_command('MoltenOutlineToggleAutoRefresh', function()
        M.auto_refresh = not M.auto_refresh
        if M.auto_refresh then
            M.setup_autocommands()
            print("Outline自动刷新已启用")
        else
            vim.api.nvim_del_augroup_by_name("MoltenOutline")
            print("Outline自动刷新已禁用")
        end
    end, { desc = 'Toggle outline auto refresh' })
end

-- 提供一些实用函数
function M.get_current_magic_cell_info()
    -- 获取当前光标所在的magic cell信息
    local bufnr = vim.api.nvim_get_current_buf()
    local cursor_line = vim.api.nvim_win_get_cursor(0)[1] - 1  -- 转换为0-based
    
    -- 调用Python函数获取cell信息
    local ok, result = pcall(vim.fn.MoltenGetCurrentMagicCellInfo, cursor_line)
    if ok then
        return result
    else
        return nil
    end
end

function M.jump_to_function_in_current_cell(func_name)
    -- 在当前magic cell中跳转到指定函数
    local cell_info = M.get_current_magic_cell_info()
    if not cell_info then
        print("当前不在magic cell中")
        return
    end
    
    -- 搜索函数定义
    local pattern = "\\<def\\s\\+" .. func_name .. "\\s*("
    local flags = "W"  -- 不换行搜索
    local result = vim.fn.search(pattern, flags)
    
    if result > 0 then
        print("跳转到函数: " .. func_name)
    else
        print("未找到函数: " .. func_name)
    end
end

-- 初始化配置
function M.setup(opts)
    opts = opts or {}
    
    -- 设置默认选项
    M.auto_refresh = opts.auto_refresh ~= false  -- 默认启用自动刷新
    M.update_timer = nil
    
    -- 设置所有功能
    M.setup_keymaps()
    M.setup_autocommands()
    M.setup_highlights()
    M.setup_commands()
    
    print("Molten Magic Cell Outline功能已初始化!")
end

return M
