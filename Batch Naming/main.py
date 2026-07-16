import os
import shutil
import threading
import time
import datetime
import re
import csv
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

HISTORY_FILE = os.path.join(os.path.expanduser('~'), '.batch_rename_history.json')
SETTINGS_FILE = os.path.join(os.path.expanduser('~'), '.batch_rename_settings.json')
MAX_HISTORY = 10
MAX_UNDO = 5

LIGHT_THEME = {
    'bg': '#F0F4F8',
    'bg_gradient_start': '#F0F4F8',
    'bg_gradient_end': '#E8EDF3',
    'card_bg': '#FFFFFF',
    'card_shadow': '#E0E5EC',
    'text': '#1A1A2E',
    'text_light': '#5A5A7A',
    'text_placeholder': '#9CA3AF',
    'border': '#E5E7EB',
    'border_light': '#F3F4F6',
    'primary': '#6366F1',
    'primary_light': '#818CF8',
    'primary_dark': '#4F46E5',
    'success': '#10B981',
    'success_light': '#34D399',
    'warning': '#F59E0B',
    'warning_light': '#FBBF24',
    'danger': '#EF4444',
    'hover': '#F5F7FA',
    'selected': '#EEF2FF',
    'header_bg': '#6366F1',
    'header_text': '#FFFFFF'
}

DARK_THEME = {
    'bg': '#0F0F23',
    'bg_gradient_start': '#0F0F23',
    'bg_gradient_end': '#1A1A3E',
    'card_bg': '#1A1A2E',
    'card_shadow': '#0D0D1A',
    'text': '#E4E8F0',
    'text_light': '#8892A6',
    'text_placeholder': '#555E70',
    'border': '#2A2A4A',
    'border_light': '#1E1E3E',
    'primary': '#818CF8',
    'primary_light': '#A5B4FC',
    'primary_dark': '#6366F1',
    'success': '#34D399',
    'success_light': '#6EE7B7',
    'warning': '#FBBF24',
    'warning_light': '#FCD34D',
    'danger': '#F87171',
    'hover': '#252545',
    'selected': '#4338CA',
    'header_bg': '#1A1A2E',
    'header_text': '#E4E8F0'
}

PRESET_TEMPLATES = [
    {'name': '日期_序号', 'prefix': '{date}_', 'suffix': '', 'digit_mode': '自动'},
    {'name': 'IMG_日期_序号', 'prefix': 'IMG_{date}_', 'suffix': '', 'digit_mode': '3位'},
    {'name': '视频_{time}', 'prefix': '视频_{time}_', 'suffix': '', 'digit_mode': '自动'},
    {'name': '文档_{year}{month}', 'prefix': '文档_{year}{month}_', 'suffix': '', 'digit_mode': '自动'},
    {'name': '扫描件_序号', 'prefix': '扫描件_', 'suffix': '', 'digit_mode': '3位'},
    {'name': '{date}_{time}_序号', 'prefix': '{date}_{time}_', 'suffix': '', 'digit_mode': '自动'}
]


def generate_new_name(old_name, mode, params):
    name, ext = os.path.splitext(old_name)
    now = datetime.datetime.now()
    
    def replace_template(text):
        if not text:
            return text
        text = text.replace('{date}', now.strftime('%Y%m%d'))
        text = text.replace('{time}', now.strftime('%H%M%S'))
        text = text.replace('{year}', now.strftime('%Y'))
        text = text.replace('{month}', now.strftime('%m'))
        text = text.replace('{day}', now.strftime('%d'))
        text = text.replace('{hour}', now.strftime('%H'))
        text = text.replace('{minute}', now.strftime('%M'))
        text = text.replace('{second}', now.strftime('%S'))
        return text
    
    if mode == 'prefix_suffix':
        prefix = replace_template(params.get('prefix', ''))
        suffix = replace_template(params.get('suffix', ''))
        index = params.get('index', 0)
        total = params.get('total', 1)
        digit_mode = params.get('digit_mode', '自动')
        
        if digit_mode == '自动':
            digit_count = max(2, len(str(total))) if total > 0 else 2
        else:
            digit_count = int(digit_mode[0])
        
        num_str = str(index + 1).zfill(digit_count)
        
        return f"{prefix}{num_str}{suffix}{ext}"
    
    elif mode == 'replace':
        find_text = params.get('find_text', '')
        replace_text = replace_template(params.get('replace_text', ''))
        use_regex = params.get('use_regex', False)
        
        if find_text:
            if use_regex:
                try:
                    new_name = re.sub(find_text, replace_text, name)
                except re.error:
                    new_name = name.replace(find_text, replace_text)
            else:
                new_name = name.replace(find_text, replace_text)
            return f"{new_name}{ext}"
        return old_name
    
    elif mode == 'change_ext':
        new_ext = params.get('new_ext', '')
        if new_ext:
            if not new_ext.startswith('.'):
                new_ext = '.' + new_ext
            return f"{name}{new_ext}"
        return old_name
    
    return old_name


class CustomCheckbutton(tk.Frame):
    def __init__(self, parent, text="", variable=None, command=None, theme=None, **kwargs):
        super().__init__(parent, bg=theme['card_bg'] if theme else '#FFFFFF')
        
        self.variable = variable
        self.command = command
        self.theme = theme
        
        self.check_var = tk.StringVar(value="")
        
        self.btn = tk.Button(self, 
                            text="",
                            width=2,
                            font=('Microsoft YaHei UI', 10, 'bold'),
                            bg=theme['card_bg'] if theme else '#FFFFFF',
                            fg=theme['primary'] if theme else '#6366F1',
                            activebackground=theme['hover'] if theme else '#F5F7FA',
                            highlightthickness=1,
                            highlightcolor=theme['border'] if theme else '#E5E7EB',
                            highlightbackground=theme['border'] if theme else '#E5E7EB',
                            bd=1,
                            relief='solid',
                            command=self.toggle)
        self.btn.pack(side=tk.LEFT)
        
        self.label = tk.Label(self, 
                             text=text,
                             font=('Microsoft YaHei UI', 10),
                             bg=theme['card_bg'] if theme else '#FFFFFF',
                             fg=theme['text'] if theme else '#1A1A2E')
        self.label.pack(side=tk.LEFT, padx=(5, 0))
        
        if self.variable:
            self.check_var.set("✓" if self.variable.get() else "")
            self.update_button()
            self.variable.trace('w', self.on_var_change)
    
    def update_button(self):
        if self.check_var.get() == "✓":
            self.btn.config(text="✓", 
                           bg=self.theme['primary'] if self.theme else '#6366F1',
                           fg='#FFFFFF')
        else:
            self.btn.config(text="", 
                           bg=self.theme['card_bg'] if self.theme else '#FFFFFF',
                           fg=self.theme['primary'] if self.theme else '#6366F1')
    
    def toggle(self):
        if self.check_var.get() == "✓":
            self.check_var.set("")
        else:
            self.check_var.set("✓")
        
        self.update_button()
        
        if self.variable:
            self.variable.set(self.check_var.get() == "✓")
        
        if self.command:
            self.command()
    
    def on_var_change(self, *args):
        if self.variable:
            self.check_var.set("✓" if self.variable.get() else "")
            self.update_button()


class BatchRenameTool:
    def __init__(self, root):
        self.root = root
        self.root.title("批量文件重命名工具")
        self.root.geometry("1100x950")
        self.root.minsize(900, 650)
        
        self.folder_path = ""
        self.target_folder_path = ""
        self.all_files = []
        self.files = []
        self.undo_stack = []
        self.mode = tk.StringVar(value="prefix_suffix")
        self.target_mode = tk.StringVar(value="overwrite")
        self.filter_text = tk.StringVar(value="")
        self.sort_mode = tk.StringVar(value="name_asc")
        self.is_running = False
        self.current_theme = tk.StringVar(value="light")
        self.use_regex = tk.BooleanVar(value=False)
        self.recursive_mode = tk.BooleanVar(value=False)
        self.test_mode = tk.BooleanVar(value=False)
        self.always_on_top = tk.BooleanVar(value=False)
        self.rename_history = self.load_history()
        self.recent_folders = self.load_recent_folders()
        self._current_preview_file = None
        self._preview_names = []
        self._preview_image = None
        self._preview_filename = ""
        
        self.setup_styles()
        self.setup_ui()
        self.load_settings()
        
        if not HAS_DND:
            messagebox.showinfo("提示", "拖拽功能需要安装 tkinterdnd2 库\n请在终端运行: pip install tkinterdnd2")
        
        self.bind_shortcuts()
    
    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.apply_theme()
    
    def get_theme(self):
        return LIGHT_THEME if self.current_theme.get() == 'light' else DARK_THEME
    
    def apply_theme(self):
        theme = self.get_theme()
        
        self.style.configure('.', 
                            font=('Microsoft YaHei UI', 10),
                            background=theme['bg'])
        
        self.style.configure('TFrame', background=theme['bg'])
        self.style.configure('Header.TFrame', background=theme['header_bg'])
        
        self.style.configure('TLabel', 
                            background=theme['bg'], 
                            foreground=theme['text'],
                            font=('Microsoft YaHei UI', 10))
        
        self.style.configure('Header.TLabel',
                            background=theme['header_bg'],
                            foreground=theme['header_text'],
                            font=('Microsoft YaHei UI', 14, 'bold'))
        
        self.style.configure('TButton', 
                            font=('Microsoft YaHei UI', 10),
                            padding=8)
        
        self.style.map('TButton',
                       background=[('active', theme['hover']), ('!active', theme['card_bg'])],
                       foreground=[('active', theme['primary']), ('!active', theme['text'])],
                       relief=[('pressed', 'flat'), ('!pressed', 'flat')])
        
        self.style.configure('Primary.TButton', 
                            background=theme['primary'], 
                            foreground='#FFFFFF',
                            font=('Microsoft YaHei UI', 10, 'bold'),
                            padding=8,
                            borderwidth=0)
        
        self.style.map('Primary.TButton',
                       background=[('active', theme['primary_light']), ('!active', theme['primary'])],
                       foreground=[('active', '#FFFFFF'), ('!active', '#FFFFFF')],
                       relief=[('pressed', 'flat'), ('!pressed', 'flat')])
        
        self.style.configure('Secondary.TButton', 
                            background=theme['card_bg'], 
                            foreground=theme['text_light'],
                            font=('Microsoft YaHei UI', 10),
                            padding=8)
        
        self.style.map('Secondary.TButton',
                       background=[('active', theme['hover']), ('!active', theme['card_bg'])],
                       foreground=[('active', theme['text']), ('!active', theme['text_light'])],
                       relief=[('pressed', 'flat'), ('!pressed', 'flat')])
        
        self.style.configure('Danger.TButton', 
                            background=theme['danger'], 
                            foreground='#FFFFFF',
                            font=('Microsoft YaHei UI', 10, 'bold'),
                            padding=8)
        
        self.style.map('Danger.TButton',
                       background=[('active', '#DC2626'), ('!active', theme['danger'])],
                       foreground=[('active', '#FFFFFF'), ('!active', '#FFFFFF')],
                       relief=[('pressed', 'flat'), ('!pressed', 'flat')])
        
        self.style.configure('Card.TFrame', 
                            background=theme['card_bg'],
                            borderwidth=1,
                            relief='solid')
        
        self.style.configure('Card.TLabelframe',
                            background=theme['card_bg'],
                            font=('Microsoft YaHei UI', 11, 'bold'),
                            foreground=theme['text'],
                            borderwidth=1,
                            relief='solid',
                            padding=12)
        
        self.style.configure('TEntry', 
                            font=('Microsoft YaHei UI', 10),
                            padding=6)
        
        self.style.configure('TRadiobutton', 
                            background=theme['card_bg'], 
                            foreground=theme['text'],
                            font=('Microsoft YaHei UI', 10))
        
        self.style.configure('TCheckbutton', 
                            background=theme['card_bg'], 
                            foreground=theme['text'],
                            font=('Microsoft YaHei UI', 10))
        
        self.style.map('TCheckbutton',
                       indicatorcolor=[('selected', theme['primary']), ('!selected', theme['border'])],
                       background=[('selected', theme['selected']), ('!selected', theme['card_bg'])])
        
        self.style.configure('Treeview', 
                            font=('Microsoft YaHei UI', 10),
                            rowheight=30,
                            background=theme['card_bg'],
                            fieldbackground=theme['card_bg'],
                            foreground=theme['text'])
        
        self.style.map('Treeview',
                       background=[('selected', theme['selected']), ('active', theme['hover'])],
                       foreground=[('selected', theme['primary']), ('active', theme['text'])])
        
        self.style.configure('Treeview.Heading', 
                            font=('Microsoft YaHei UI', 10, 'bold'),
                            background=theme['bg'],
                            foreground=theme['text'],
                            relief='flat')
        
        self.style.map('Treeview.Heading',
                       background=[('active', theme['hover'])])
        
        self.style.configure('TCombobox', 
                            font=('Microsoft YaHei UI', 10),
                            padding=6)
        
        self.style.configure('TProgressbar',
                            troughcolor=theme['hover'],
                            background=theme['primary'])
        
        self.style.configure('TPanedwindow',
                            background=theme['border'],
                            sashwidth=6)
        
        self.root.configure(bg=theme['bg'])
        
        pass
        
        if hasattr(self, 'preview_canvas'):
            self.preview_canvas.config(bg=theme['card_bg'],
                                       highlightbackground=theme['border'])
        
        if hasattr(self, 'preview_label'):
            self.preview_label.config(foreground=theme['text_light'])
        
        if hasattr(self, 'stats_label'):
            self.stats_label.config(background=theme['bg'])
        
        if hasattr(self, 'status_label'):
            self.status_label.config(background=theme['bg'])
    
    def toggle_theme(self):
        self.current_theme.set('dark' if self.current_theme.get() == 'light' else 'light')
        self.apply_theme()
        self.save_settings()
    
    def toggle_always_on_top(self):
        self.always_on_top.set(not self.always_on_top.get())
        self.root.attributes('-topmost', self.always_on_top.get())
        
        if self.always_on_top.get():
            self.btn_always_on_top.config(text="🖥️ 已置顶", style='Primary.TButton')
        else:
            self.btn_always_on_top.config(text="🖥️ 置顶", style='Secondary.TButton')
        
        self.save_settings()
    
    def show_theme_config(self):
        if hasattr(self, 'theme_window') and self.theme_window.winfo_exists():
            self.theme_window.lift()
            return
        
        self.theme_window = tk.Toplevel(self.root)
        self.theme_window.title("主题设置")
        self.theme_window.geometry("450x350")
        self.theme_window.resizable(False, False)
        self.theme_window.attributes('-topmost', True)
        
        theme = self.get_theme()
        self.theme_window.configure(bg=theme['card_bg'])
        
        ttk.Label(self.theme_window, text="选择主色调:", 
                  font=('Microsoft YaHei UI', 11, 'bold'),
                  background=theme['card_bg'],
                  foreground=theme['text']).pack(pady=(15, 5))
        
        colors = [
            {'name': '科技蓝', 'color': '#6366F1'},
            {'name': '活力橙', 'color': '#F97316'},
            {'name': '清新绿', 'color': '#10B981'},
            {'name': '优雅紫', 'color': '#8B5CF6'},
            {'name': '沉稳灰', 'color': '#64748B'},
            {'name': '经典红', 'color': '#DC2626'},
            {'name': '天空蓝', 'color': '#3B82F6'},
            {'name': '玫瑰红', 'color': '#EC4899'},
            {'name': '柠檬黄', 'color': '#EAB308'}
        ]
        
        color_var = tk.StringVar(value=theme['primary'])
        
        color_frame = ttk.Frame(self.theme_window)
        color_frame.pack(pady=10)
        
        for i, color_info in enumerate(colors):
            btn = tk.Button(color_frame, 
                           text="", 
                           width=6,
                           height=3,
                           bg=color_info['color'],
                           activebackground=self.lighten_color(color_info['color'], 30),
                           relief='solid',
                           bd=2,
                           command=lambda c=color_info: [color_var.set(c['color']), 
                                                         self.apply_custom_theme(c['color']),
                                                         self.theme_window.destroy()])
            btn.grid(row=i//3, column=i%3, padx=8, pady=8)
            
            label = ttk.Label(color_frame, text=color_info['name'],
                            font=('Microsoft YaHei UI', 9))
            label.grid(row=i//3 + 1, column=i%3, padx=8, pady=(0, 5))
        
        ttk.Button(self.theme_window, text="重置为默认", 
                   command=lambda: [self.reset_theme(), self.theme_window.destroy()],
                   style='Secondary.TButton').pack(pady=15)
    
    def apply_custom_theme(self, primary_color):
        theme = self.get_theme()
        theme['primary'] = primary_color
        theme['primary_light'] = self.lighten_color(primary_color, 20)
        theme['primary_dark'] = self.darken_color(primary_color, 20)
        self.apply_theme()
        self.save_settings()
    
    def lighten_color(self, color, percent):
        r = min(255, int(color[1:3], 16) + percent)
        g = min(255, int(color[3:5], 16) + percent)
        b = min(255, int(color[5:7], 16) + percent)
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def darken_color(self, color, percent):
        r = max(0, int(color[1:3], 16) - percent)
        g = max(0, int(color[3:5], 16) - percent)
        b = max(0, int(color[5:7], 16) - percent)
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def reset_theme(self):
        if self.current_theme.get() == 'light':
            LIGHT_THEME['primary'] = '#6366F1'
            LIGHT_THEME['primary_light'] = '#818CF8'
            LIGHT_THEME['primary_dark'] = '#4F46E5'
        else:
            DARK_THEME['primary'] = '#818CF8'
            DARK_THEME['primary_light'] = '#A5B4FC'
            DARK_THEME['primary_dark'] = '#6366F1'
        self.apply_theme()
        self.save_settings()
    
    def setup_ui(self):
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=0, minsize=60)
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_rowconfigure(3, weight=0, minsize=200)
        self.root.grid_rowconfigure(4, weight=0)
        self.root.grid_columnconfigure(0, weight=1)
        
        self.header_frame = ttk.Frame(self.root, style='Header.TFrame')
        self.header_frame.grid(row=0, column=0, sticky='ew')
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        theme = self.get_theme()
        
        header_left = ttk.Frame(self.header_frame)
        header_left.grid(row=0, column=0, sticky='w', padx=20, pady=15)
        
        ttk.Label(header_left, text="📁 批量文件重命名工具", 
                  font=('Microsoft YaHei UI', 16, 'bold'),
                  foreground=theme['header_text'],
                  style='Header.TLabel').pack(side=tk.LEFT)
        
        header_right = ttk.Frame(self.header_frame)
        header_right.grid(row=0, column=1, sticky='e', padx=20, pady=15)
        
        self.btn_always_on_top = ttk.Button(header_right, text="🖥️ 置顶", 
                                             command=self.toggle_always_on_top,
                                             style='Secondary.TButton')
        self.btn_always_on_top.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.btn_toggle_theme = ttk.Button(header_right, text="🌙 深色", 
                                           command=self.toggle_theme,
                                           style='Secondary.TButton')
        self.btn_toggle_theme.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.btn_theme_config = ttk.Button(header_right, text="🎨 主题", 
                                           command=self.show_theme_config,
                                           style='Secondary.TButton')
        self.btn_theme_config.pack(side=tk.RIGHT)
        
        top_frame = ttk.Frame(self.root)
        top_frame.grid(row=1, column=0, sticky='ew', padx=15, pady=(10, 5))
        
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(side=tk.LEFT)
        
        self.btn_select_folder = ttk.Button(btn_frame, text="选择文件夹", 
                                            command=self.select_folder, 
                                            style='Secondary.TButton')
        self.btn_select_folder.pack(side=tk.LEFT)
        
        self.recent_folder_combobox = ttk.Combobox(btn_frame, 
                                                    width=50,
                                                    values=self.get_recent_folder_names(),
                                                    state='readonly')
        self.recent_folder_combobox.pack(side=tk.LEFT, padx=(10, 0))
        self.recent_folder_combobox.bind('<<ComboboxSelected>>', self.on_recent_folder_select)
        
        self.btn_quick_number = ttk.Button(btn_frame, text="快速编号", 
                                           command=self.quick_number, 
                                           style='Primary.TButton')
        self.btn_quick_number.pack(side=tk.LEFT, padx=(10, 0))
        
        self.btn_clear = ttk.Button(btn_frame, text="清空列表", 
                                    command=self.clear_list, 
                                    style='Secondary.TButton')
        self.btn_clear.pack(side=tk.LEFT, padx=(10, 0))
        
        self.btn_export = ttk.Button(btn_frame, text="导出清单 (Ctrl+E)", 
                                     command=self.export_list, 
                                     style='Secondary.TButton')
        self.btn_export.pack(side=tk.LEFT, padx=(10, 0))
        
        self.btn_delete = ttk.Button(btn_frame, text="🗑️ 删除文件", 
                                     command=self.delete_files, 
                                     style='Danger.TButton')
        self.btn_delete.pack(side=tk.LEFT, padx=(10, 0))
        
        self.btn_history = ttk.Button(btn_frame, text="命名历史", 
                                      command=self.show_history, 
                                      style='Secondary.TButton')
        self.btn_history.pack(side=tk.LEFT, padx=(10, 0))
        
        self.btn_help = ttk.Button(btn_frame, text="帮助", 
                                   command=self.show_help, 
                                   style='Secondary.TButton')
        self.btn_help.pack(side=tk.LEFT, padx=(10, 0))
        
        middle_frame = ttk.Frame(self.root)
        middle_frame.grid(row=2, column=0, sticky='nsew', padx=15, pady=(0, 5))
        middle_frame.grid_rowconfigure(0, weight=1)
        middle_frame.grid_columnconfigure(0, weight=1)
        
        self.paned_window = ttk.PanedWindow(middle_frame, orient=tk.HORIZONTAL)
        self.paned_window.grid(row=0, column=0, sticky='nsew')
        
        left_panel = ttk.Frame(self.paned_window, style='Card.TFrame')
        right_panel = ttk.Frame(self.paned_window, style='Card.TFrame')
        
        self.paned_window.add(left_panel, weight=3)
        self.paned_window.add(right_panel, weight=1)
        
        left_panel.grid_rowconfigure(0, weight=1)
        left_panel.grid_columnconfigure(0, weight=1)
        
        card_frame = ttk.Frame(left_panel)
        card_frame.grid(row=0, column=0, sticky='nsew')
        
        self.tree = ttk.Treeview(card_frame, columns=('current', 'preview'), 
                                 show='headings', height=12)
        self.tree.heading('current', text='当前文件名')
        self.tree.heading('preview', text='重命名预览')
        self.tree.column('current', width=300, anchor='w', minwidth=150)
        self.tree.column('preview', width=300, anchor='w', minwidth=150)
        
        scrollbar = ttk.Scrollbar(card_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<Double-1>', self.on_tree_double_click)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        
        right_panel.grid_rowconfigure(0, weight=0)
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_rowconfigure(2, weight=0)
        right_panel.grid_columnconfigure(0, weight=1)
        
        ttk.Label(right_panel, text="🖼️ 图片预览", 
                  font=('Microsoft YaHei UI', 11, 'bold')).grid(row=0, column=0, sticky='w', pady=(10, 5), padx=10)
        
        self.preview_canvas = tk.Canvas(right_panel, bg=self.get_theme()['card_bg'],
                                         highlightthickness=1,
                                         highlightbackground=self.get_theme()['border'],
                                         cursor='hand2')
        self.preview_canvas.grid(row=1, column=0, sticky='nsew', padx=10, pady=(0, 5))
        self.preview_canvas.bind('<Configure>', self.on_preview_canvas_resize)
        self.preview_canvas.bind('<Double-1>', self.on_preview_double_click)
        
        self.preview_label = ttk.Label(right_panel, text="选择图片文件查看预览", 
                                       font=('Microsoft YaHei UI', 9),
                                       foreground=self.get_theme()['text_light'],
                                       wraplength=200)
        self.preview_label.grid(row=2, column=0, sticky='n', pady=(0, 10), padx=10)
        
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.grid(row=3, column=0, sticky='ew', padx=15, pady=(0, 5))
        
        bottom_frame.grid_columnconfigure(0, weight=1)
        
        stats_frame = ttk.Frame(bottom_frame)
        stats_frame.grid(row=0, column=0, sticky='ew', pady=(0, 6))
        
        self.stats_label = ttk.Label(stats_frame, text="", 
                                      font=('Microsoft YaHei UI', 9),
                                      foreground=self.get_theme()['text_light'])
        self.stats_label.pack(side=tk.LEFT)
        
        filter_sort_frame = ttk.LabelFrame(bottom_frame, text="文件筛选与排序", 
                                           style='Card.TLabelframe')
        filter_sort_frame.grid(row=1, column=0, sticky='ew', pady=(0, 6))
        
        for col in range(6):
            filter_sort_frame.grid_columnconfigure(col, weight=1)
        
        ttk.Label(filter_sort_frame, text="过滤后缀：", 
                  font=('Microsoft YaHei UI', 10, 'bold')).grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.filter_entry = ttk.Entry(filter_sort_frame, textvariable=self.filter_text)
        self.filter_entry.grid(row=0, column=1, sticky='ew', padx=(0, 15))
        self.filter_text.trace('w', self.on_filter_change)
        
        ttk.Label(filter_sort_frame, text="排序规则：", 
                  font=('Microsoft YaHei UI', 10, 'bold')).grid(row=0, column=2, sticky='w', padx=(0, 10))
        self.sort_combobox = ttk.Combobox(filter_sort_frame, textvariable=self.sort_mode,
                                           values=['文件名 (A-Z)', '文件名 (Z-A)',
                                                   '修改时间（从旧到新）', '修改时间（从新到旧）',
                                                   '创建时间（从旧到新）', '创建时间（从新到旧）',
                                                   '文件大小（从小到大）', '文件大小（从大到小）',
                                                   '扩展名（A-Z）', '扩展名（Z-A）'],
                                           width=22, state='readonly')
        self.sort_combobox.grid(row=0, column=3, sticky='w')
        self.sort_combobox.current(0)
        self.sort_combobox.bind('<<ComboboxSelected>>', self.on_sort_change)
        
        self.recursive_check = CustomCheckbutton(filter_sort_frame, text="递归子文件夹", 
                                             variable=self.recursive_mode,
                                             command=self.on_recursive_change,
                                             theme=self.get_theme())
        self.recursive_check.grid(row=0, column=4, sticky='w')
        
        self.test_check = CustomCheckbutton(filter_sort_frame, text="测试模式（仅预览）", 
                                            variable=self.test_mode,
                                            theme=self.get_theme())
        self.test_check.grid(row=0, column=5, sticky='w')
        
        target_mode_frame = ttk.LabelFrame(bottom_frame, text="目标文件夹与重命名方式", 
                                         style='Card.TLabelframe')
        target_mode_frame.grid(row=2, column=0, sticky='ew', pady=(0, 6))
        
        for col in range(6):
            target_mode_frame.grid_columnconfigure(col, weight=1)
        
        ttk.Label(target_mode_frame, text="目标：", font=('Microsoft YaHei UI', 10, 'bold')).grid(row=0, column=0, sticky='w', padx=(0, 5))
        ttk.Radiobutton(target_mode_frame, text="覆盖当前文件夹", variable=self.target_mode,
                        value="overwrite", command=self.on_target_mode_change).grid(row=0, column=1, sticky='w', padx=(0, 10))
        ttk.Radiobutton(target_mode_frame, text="复制到新文件夹", variable=self.target_mode,
                        value="copy", command=self.on_target_mode_change).grid(row=0, column=2, sticky='w', padx=(0, 10))
        
        self.target_folder_btn = ttk.Button(target_mode_frame, text="选择目标文件夹", 
                                            command=self.select_target_folder, 
                                            state='disabled',
                                            style='Secondary.TButton')
        self.target_folder_btn.grid(row=0, column=3, sticky='w')
        
        self.target_folder_label = ttk.Label(target_mode_frame, text="", 
                                             foreground='#999999', 
                                             font=('Microsoft YaHei UI', 10),
                                             wraplength=180)
        self.target_folder_label.grid(row=0, column=4, sticky='w')
        
        ttk.Label(target_mode_frame, text="方式：", font=('Microsoft YaHei UI', 10, 'bold')).grid(row=1, column=0, sticky='w', padx=(0, 5))
        ttk.Radiobutton(target_mode_frame, text="前缀/后缀", variable=self.mode, 
                        value="prefix_suffix", command=self.update_mode_ui).grid(row=1, column=1, sticky='w', padx=(0, 10))
        ttk.Radiobutton(target_mode_frame, text="替换文本", variable=self.mode, 
                        value="replace", command=self.update_mode_ui).grid(row=1, column=2, sticky='w')
        ttk.Radiobutton(target_mode_frame, text="修改扩展名", variable=self.mode, 
                        value="change_ext", command=self.update_mode_ui).grid(row=1, column=3, sticky='w')
        
        ttk.Label(target_mode_frame, text="模板预设：", font=('Microsoft YaHei UI', 10, 'bold')).grid(row=2, column=0, sticky='w', padx=(0, 5))
        self.template_combobox = ttk.Combobox(target_mode_frame, 
                                               values=[t['name'] for t in PRESET_TEMPLATES],
                                               width=15, state='readonly')
        self.template_combobox.grid(row=2, column=1, sticky='w')
        self.template_combobox.bind('<<ComboboxSelected>>', self.on_template_select)
        
        self.mode_a_frame = ttk.LabelFrame(bottom_frame, text="前缀/后缀设置", 
                                            style='Card.TLabelframe')
        self.mode_a_frame.grid(row=3, column=0, sticky='ew', pady=(0, 6))
        
        for col in range(6):
            self.mode_a_frame.grid_columnconfigure(col, weight=1)
        
        ttk.Label(self.mode_a_frame, text="前缀：", 
                  font=('Microsoft YaHei UI', 10, 'bold')).grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.prefix_entry = ttk.Entry(self.mode_a_frame)
        self.prefix_entry.grid(row=0, column=1, sticky='ew', padx=(0, 15))
        
        ttk.Label(self.mode_a_frame, text="后缀：", 
                  font=('Microsoft YaHei UI', 10, 'bold')).grid(row=0, column=2, sticky='w', padx=(0, 10))
        self.suffix_entry = ttk.Entry(self.mode_a_frame)
        self.suffix_entry.grid(row=0, column=3, sticky='ew', padx=(0, 15))
        
        ttk.Label(self.mode_a_frame, text="编号位数：", 
                  font=('Microsoft YaHei UI', 10, 'bold')).grid(row=0, column=4, sticky='w', padx=(0, 10))
        self.digit_combobox = ttk.Combobox(self.mode_a_frame, 
                                            values=['自动', '2位', '3位', '4位', '5位'], 
                                            width=8, state='readonly')
        self.digit_combobox.grid(row=0, column=5, sticky='w')
        self.digit_combobox.current(0)
        self.digit_combobox.bind('<<ComboboxSelected>>', self.on_digit_mode_change)
        
        ttk.Label(self.mode_a_frame, text="支持模板：{date} {time} {year} {month} {day} {hour} {minute} {second}", 
                  font=('Microsoft YaHei UI', 9), 
                  foreground='#999999').grid(row=1, column=0, columnspan=6, sticky='w', pady=(5, 0))
        
        self.mode_b_frame = ttk.LabelFrame(bottom_frame, text="替换设置", 
                                            style='Card.TLabelframe')
        self.mode_b_frame.grid(row=3, column=0, sticky='ew', pady=(0, 6))
        self.mode_b_frame.grid_remove()
        
        for col in range(5):
            self.mode_b_frame.grid_columnconfigure(col, weight=1)
        
        ttk.Label(self.mode_b_frame, text="查找文本：", 
                  font=('Microsoft YaHei UI', 10, 'bold')).grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.find_entry = ttk.Entry(self.mode_b_frame)
        self.find_entry.grid(row=0, column=1, sticky='ew', padx=(0, 15))
        
        ttk.Label(self.mode_b_frame, text="替换为：", 
                  font=('Microsoft YaHei UI', 10, 'bold')).grid(row=0, column=2, sticky='w', padx=(0, 10))
        self.replace_entry = ttk.Entry(self.mode_b_frame)
        self.replace_entry.grid(row=0, column=3, sticky='ew')
        
        self.regex_check = CustomCheckbutton(self.mode_b_frame, text="正则表达式", 
                                         variable=self.use_regex,
                                         theme=self.get_theme())
        self.regex_check.grid(row=0, column=4, sticky='w')
        
        self.mode_c_frame = ttk.LabelFrame(bottom_frame, text="扩展名设置", 
                                            style='Card.TLabelframe')
        self.mode_c_frame.grid(row=3, column=0, sticky='ew', pady=(0, 6))
        self.mode_c_frame.grid_remove()
        
        for col in range(4):
            self.mode_c_frame.grid_columnconfigure(col, weight=1)
        
        ttk.Label(self.mode_c_frame, text="新扩展名：", 
                  font=('Microsoft YaHei UI', 10, 'bold')).grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.new_ext_entry = ttk.Entry(self.mode_c_frame)
        self.new_ext_entry.grid(row=0, column=1, sticky='ew', padx=(0, 15))
        
        ttk.Label(self.mode_c_frame, text="示例：输入 jpg 或 .jpg", 
                  font=('Microsoft YaHei UI', 9), 
                  foreground='#999999').grid(row=0, column=2, columnspan=2, sticky='w')
        
        btn_action_frame = ttk.Frame(bottom_frame)
        btn_action_frame.grid(row=4, column=0, sticky='ew', pady=(0, 5))
        
        self.btn_move = ttk.Button(btn_action_frame, text="批量移动", 
                                    command=self.batch_move, 
                                    state='disabled',
                                    style='Secondary.TButton')
        self.btn_move.pack(side=tk.LEFT)
        
        self.btn_undo = ttk.Button(btn_action_frame, text="撤销 (Ctrl+Z)", 
                                   command=self.undo_rename, 
                                   state='disabled',
                                   style='Secondary.TButton')
        self.btn_undo.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.btn_preview = ttk.Button(btn_action_frame, text="预览 (Ctrl+P)", 
                                      command=self.generate_preview,
                                      style='Secondary.TButton')
        self.btn_preview.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.btn_rename = ttk.Button(btn_action_frame, text="开始重命名 (Ctrl+R)", 
                                      command=self.apply_rename,
                                      style='Primary.TButton')
        self.btn_rename.pack(side=tk.RIGHT)
        
        status_frame = ttk.Frame(self.root)
        status_frame.grid(row=4, column=0, sticky='ew', padx=15, pady=(0, 15))
        
        self.status_label = ttk.Label(status_frame, text="就绪", 
                                       font=('Microsoft YaHei UI', 10),
                                       foreground='#666666')
        self.status_label.pack(side=tk.LEFT)
        
        progress_frame = ttk.Frame(status_frame)
        progress_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(20, 0))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', 
                                             length=300)
        self.progress_bar.pack(side=tk.RIGHT)
        
        if HAS_DND:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self.on_drop)
    
    def update_mode_ui(self):
        self.mode_a_frame.grid_remove()
        self.mode_b_frame.grid_remove()
        self.mode_c_frame.grid_remove()
        
        if self.mode.get() == 'prefix_suffix':
            self.mode_a_frame.grid(row=3, column=0, sticky='ew', pady=(0, 6))
        elif self.mode.get() == 'replace':
            self.mode_b_frame.grid(row=3, column=0, sticky='ew', pady=(0, 6))
        elif self.mode.get() == 'change_ext':
            self.mode_c_frame.grid(row=3, column=0, sticky='ew', pady=(0, 6))
    
    def on_target_mode_change(self):
        if self.target_mode.get() == 'copy':
            self.target_folder_btn.config(state='normal')
            if not self.target_folder_path:
                self.select_target_folder()
        else:
            self.target_folder_btn.config(state='disabled')
            self.target_folder_path = ""
            self.target_folder_label.config(text="")
    
    def on_recursive_change(self):
        if self.folder_path:
            self.refresh_file_list()
    
    def on_template_select(self, event):
        idx = self.template_combobox.current()
        if idx >= 0:
            template = PRESET_TEMPLATES[idx]
            self.mode.set('prefix_suffix')
            self.update_mode_ui()
            self.prefix_entry.delete(0, tk.END)
            self.prefix_entry.insert(0, template['prefix'])
            self.suffix_entry.delete(0, tk.END)
            self.suffix_entry.insert(0, template['suffix'])
            self.digit_combobox.set(template['digit_mode'])
            if self.files:
                self.generate_preview()
    
    def bind_shortcuts(self):
        self.root.bind('<Control-a>', self.select_all_files)
        self.root.bind('<Control-z>', self.undo_rename_shortcut)
        self.root.bind('<Control-r>', self.apply_rename_shortcut)
        self.root.bind('<Control-p>', self.generate_preview_shortcut)
        self.root.bind('<Control-e>', self.export_list_shortcut)
    
    def select_all_files(self, event=None):
        for item in self.tree.get_children():
            self.tree.selection_add(item)
    
    def undo_rename_shortcut(self, event=None):
        if self.btn_undo['state'] != 'disabled':
            self.undo_rename()
    
    def apply_rename_shortcut(self, event=None):
        self.apply_rename()
    
    def generate_preview_shortcut(self, event=None):
        self.generate_preview()
    
    def export_list_shortcut(self, event=None):
        self.export_list()
    
    def load_history(self):
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return []
    
    def load_recent_folders(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get('recent_folders', [])
        except:
            pass
        return []
    
    def save_recent_folders(self):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except:
            settings = {}
        
        settings['recent_folders'] = self.recent_folders
        
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    
    def add_recent_folder(self, folder_path):
        if folder_path in self.recent_folders:
            self.recent_folders.remove(folder_path)
        self.recent_folders.insert(0, folder_path)
        self.recent_folders = self.recent_folders[:5]
        self.save_recent_folders()
        self.recent_folder_combobox['values'] = self.get_recent_folder_names()
    
    def get_recent_folder_names(self):
        names = []
        for path in self.recent_folders:
            if os.path.exists(path):
                name = os.path.basename(path)
                names.append(f"{name} ({path})")
        return names
    
    def on_recent_folder_select(self, event):
        idx = self.recent_folder_combobox.current()
        if idx >= 0 and idx < len(self.recent_folders):
            folder_path = self.recent_folders[idx]
            if os.path.exists(folder_path):
                self.folder_path = folder_path
                self.load_files()
            else:
                messagebox.showwarning("提示", "文件夹不存在")
                self.recent_folders.pop(idx)
                self.save_recent_folders()
                self.recent_folder_combobox['values'] = self.get_recent_folder_names()
    
    def save_history(self):
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.rename_history, f, indent=2)
        except:
            pass
    
    def load_settings(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    if 'theme' in settings:
                        self.current_theme.set(settings['theme'])
                    if 'always_on_top' in settings:
                        self.always_on_top.set(settings['always_on_top'])
                        self.root.attributes('-topmost', settings['always_on_top'])
                    if 'sort_mode' in settings:
                        self.sort_mode.set(settings['sort_mode'])
                        self.sort_combobox.set(settings['sort_mode'])
        except:
            pass
    
    def save_settings(self):
        try:
            settings = {
                'theme': self.current_theme.get(),
                'always_on_top': self.always_on_top.get(),
                'sort_mode': self.sort_mode.get()
            }
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except:
            pass
    
    def add_to_history(self):
        rule = {
            'mode': self.mode.get(),
            'prefix': self.prefix_entry.get(),
            'suffix': self.suffix_entry.get(),
            'digit_mode': self.digit_combobox.get(),
            'find_text': self.find_entry.get(),
            'replace_text': self.replace_entry.get(),
            'use_regex': self.use_regex.get(),
            'new_ext': self.new_ext_entry.get() if hasattr(self, 'new_ext_entry') else '',
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        self.rename_history.insert(0, rule)
        if len(self.rename_history) > MAX_HISTORY:
            self.rename_history = self.rename_history[:MAX_HISTORY]
        self.save_history()
    
    def select_folder(self):
        folder_path = filedialog.askdirectory(title="选择文件夹")
        if folder_path:
            self.folder_path = folder_path
            self.add_recent_folder(folder_path)
            self.recent_folder_combobox.set(os.path.basename(folder_path))
            self.refresh_file_list()
    
    def select_target_folder(self):
        folder_path = filedialog.askdirectory(title="选择目标文件夹")
        if folder_path:
            self.target_folder_path = folder_path
            self.target_folder_label.config(text=folder_path)
    
    def on_drop(self, event):
        if event.data:
            folder_path = event.data.strip('{}')
            if os.path.isdir(folder_path):
                self.folder_path = folder_path
                self.add_recent_folder(folder_path)
                self.recent_folder_combobox.set(os.path.basename(folder_path))
                self.refresh_file_list()
    
    def apply_filter_and_sort(self):
        filtered = self.all_files[:]
        
        ext_filter = self.filter_text.get().strip().lower()
        if ext_filter:
            if not ext_filter.startswith('.'):
                ext_filter = '.' + ext_filter
            filtered = [f for f in filtered if f.lower().endswith(ext_filter)]
        
        sort_mode = self.sort_mode.get()
        if sort_mode == '文件名 (A-Z)':
            filtered.sort(key=lambda x: x.lower())
        elif sort_mode == '文件名 (Z-A)':
            filtered.sort(key=lambda x: x.lower(), reverse=True)
        elif sort_mode == '修改时间（从旧到新）':
            filtered.sort(key=lambda x: os.path.getmtime(os.path.join(self.folder_path, x)))
        elif sort_mode == '修改时间（从新到旧）':
            filtered.sort(key=lambda x: os.path.getmtime(os.path.join(self.folder_path, x)), reverse=True)
        elif sort_mode == '创建时间（从旧到新）':
            filtered.sort(key=lambda x: os.path.getctime(os.path.join(self.folder_path, x)))
        elif sort_mode == '创建时间（从新到旧）':
            filtered.sort(key=lambda x: os.path.getctime(os.path.join(self.folder_path, x)), reverse=True)
        elif sort_mode == '文件大小（从小到大）':
            filtered.sort(key=lambda x: os.path.getsize(os.path.join(self.folder_path, x)))
        elif sort_mode == '文件大小（从大到小）':
            filtered.sort(key=lambda x: os.path.getsize(os.path.join(self.folder_path, x)), reverse=True)
        elif sort_mode == '扩展名（A-Z）':
            filtered.sort(key=lambda x: os.path.splitext(x)[1].lower())
        elif sort_mode == '扩展名（Z-A）':
            filtered.sort(key=lambda x: os.path.splitext(x)[1].lower(), reverse=True)
        
        return filtered
    
    def get_all_files_recursive(self, folder):
        all_files = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), folder)
                all_files.append(rel_path)
        return all_files
    
    def update_stats(self):
        if not self.files:
            self.stats_label.config(text="")
            return
        
        total_size = sum(os.path.getsize(os.path.join(self.folder_path, f)) for f in self.files)
        ext_counts = {}
        for f in self.files:
            ext = os.path.splitext(f)[1].lower()
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
        
        size_str = self.format_size(total_size)
        ext_str = ", ".join([f"{k}:{v}" for k, v in ext_counts.items()])
        
        self.stats_label.config(text=f"📊 共 {len(self.files)} 个文件，总大小 {size_str}，类型：{ext_str}")
    
    def format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def delete_files(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先选择要删除的文件")
            return
        
        filenames = []
        for item in selected_items:
            values = self.tree.item(item, 'values')
            if values:
                filenames.append(values[0])
        
        if len(filenames) == 1:
            msg = f"确定要删除文件 \"{filenames[0]}\" 吗？\n删除后无法恢复！"
        else:
            msg = f"确定要删除选中的 {len(filenames)} 个文件吗？\n删除后无法恢复！"
        
        if not messagebox.askyesno("确认删除", msg):
            return
        
        deleted_count = 0
        failed_count = 0
        
        for filename in filenames:
            file_path = os.path.join(self.folder_path, filename)
            try:
                os.remove(file_path)
                deleted_count += 1
            except Exception as e:
                failed_count += 1
        
        for item in selected_items:
            self.tree.delete(item)
            idx = self.tree.index(item)
            if idx < len(self.files):
                self.files.pop(idx)
        
        self.refresh_file_list()
        self.update_stats()
        
        if failed_count > 0:
            messagebox.showinfo("删除完成", f"成功删除 {deleted_count} 个文件，{failed_count} 个文件删除失败")
        else:
            messagebox.showinfo("删除完成", f"成功删除 {deleted_count} 个文件")
    
    def refresh_file_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not self.folder_path:
            return
        
        try:
            if self.recursive_mode.get():
                self.all_files = self.get_all_files_recursive(self.folder_path)
            else:
                all_items = os.listdir(self.folder_path)
                self.all_files = [f for f in all_items if os.path.isfile(os.path.join(self.folder_path, f))]
            
            self.files = self.apply_filter_and_sort()
            
            if not self.files:
                if self.filter_text.get().strip():
                    self.tree.insert('', tk.END, values=('没有匹配的文件', ''))
                else:
                    self.tree.insert('', tk.END, values=('文件夹为空', ''))
                return
            
            for filename in self.files:
                self.tree.insert('', tk.END, values=(filename, ''))
            
            if self.all_files:
                self.generate_preview()
            
            self.btn_move.config(state='normal' if self.files else 'disabled')
            self.update_stats()
        
        except Exception as e:
            messagebox.showerror("错误", f"读取文件夹失败：{str(e)}")
    
    def on_filter_change(self, *args):
        if self.folder_path:
            self.refresh_file_list()
    
    def on_sort_change(self, *args):
        if self.folder_path:
            self.refresh_file_list()
    
    def on_digit_mode_change(self, *args):
        if self.files:
            self.generate_preview()
    
    def quick_number(self):
        self.prefix_entry.delete(0, tk.END)
        self.prefix_entry.insert(0, '{date}_')
        self.suffix_entry.delete(0, tk.END)
        self.suffix_entry.insert(0, '')
        self.digit_combobox.current(0)
        self.mode.set('prefix_suffix')
        self.update_mode_ui()
        if self.files:
            self.generate_preview()
    
    def clear_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.folder_path = ""
        self.all_files = []
        self.files = []
        self.recent_folder_combobox.set("")
        self.update_status("列表已清空", '#666666')
        self.update_stats()
        self.preview_canvas.delete('all')
        self.preview_label.config(text="选择图片文件查看预览")
    
    def get_params(self, index):
        if self.mode.get() == 'prefix_suffix':
            return {
                'prefix': self.prefix_entry.get(),
                'suffix': self.suffix_entry.get(),
                'index': index,
                'total': len(self.files),
                'digit_mode': self.digit_combobox.get()
            }
        elif self.mode.get() == 'replace':
            return {
                'find_text': self.find_entry.get(),
                'replace_text': self.replace_entry.get(),
                'use_regex': self.use_regex.get()
            }
        elif self.mode.get() == 'change_ext':
            return {
                'new_ext': self.new_ext_entry.get()
            }
        return {}
    
    def generate_preview(self):
        if not self.files:
            messagebox.showwarning("提示", "请先选择文件夹")
            return
        
        preview_names = []
        for i, filename in enumerate(self.files):
            new_name = generate_new_name(filename, self.mode.get(), self.get_params(i))
            preview_names.append(new_name)
        
        name_counts = {}
        for name in preview_names:
            name_counts[name] = name_counts.get(name, 0) + 1
        
        conflict_count = sum(1 for count in name_counts.values() if count > 1)
        
        for i, item in enumerate(self.tree.get_children()):
            if i < len(preview_names):
                new_name = preview_names[i]
                if name_counts[new_name] > 1:
                    self.tree.item(item, values=(self.files[i], f"⚠️ {new_name} (重复)"))
                else:
                    self.tree.item(item, values=(self.files[i], new_name))
        
        self._preview_names = preview_names
        
        if conflict_count > 0:
            self.update_status(f"预览完成，发现 {conflict_count} 个文件名冲突！", '#EF4444')
            messagebox.warning("文件名冲突", f"检测到 {conflict_count} 个文件名冲突，请检查并重命名规则！")
        else:
            self.update_status(f"预览完成，共 {len(self.files)} 个文件", '#666666')
    
    def apply_rename(self):
        if not self.files:
            messagebox.showwarning("提示", "请先选择文件夹")
            return
        
        if self.test_mode.get():
            self.generate_preview()
            messagebox.showinfo("测试模式", "已生成预览，未执行实际重命名操作")
            return
        
        if self.mode.get() == 'change_ext' and not self.new_ext_entry.get().strip():
            messagebox.showwarning("提示", "请输入新扩展名")
            return
        
        if self.mode.get() == 'replace' and not self.find_entry.get().strip():
            messagebox.showwarning("提示", "请输入要查找的文本")
            return
        
        self.is_running = True
        self.btn_rename.config(state='disabled')
        self.btn_preview.config(state='disabled')
        
        preview_names = []
        for i, filename in enumerate(self.files):
            new_name = generate_new_name(filename, self.mode.get(), self.get_params(i))
            preview_names.append(new_name)
        
        self.update_status("正在重命名...", '#007AFF')
        self.update_progress(0)
        
        thread = threading.Thread(target=self.rename_thread, 
                                args=(preview_names,),
                                daemon=True)
        thread.start()
    
    def rename_thread(self, preview_names):
        start_time = time.time()
        
        if self.target_mode.get() == 'copy':
            if not os.path.exists(self.target_folder_path):
                try:
                    os.makedirs(self.target_folder_path)
                except Exception as e:
                    self.root.after(0, self.rename_complete, 0, 1, [f"创建目标文件夹失败：{str(e)}"], 0)
                    return
        
        current_undo = []
        success_count = 0
        fail_count = 0
        fail_messages = []
        is_copy = self.target_mode.get() == 'copy'
        total_files = len(self.files)
        
        for i, filename in enumerate(self.files):
            if not self.is_running:
                break
            
            old_path = os.path.join(self.folder_path, filename)
            new_name = preview_names[i]
            
            if self.recursive_mode.get():
                dir_name = os.path.dirname(filename)
                target_dir = os.path.join(self.target_folder_path if is_copy else self.folder_path, dir_name)
                if is_copy and not os.path.exists(target_dir):
                    os.makedirs(target_dir)
            
            new_path = os.path.join(self.target_folder_path if is_copy else self.folder_path, new_name)
            
            progress = int((i + 1) / total_files * 100)
            self.root.after(0, self.update_progress, progress)
            self.root.after(0, self.update_status, 
                           f"正在处理 {i + 1}/{total_files} ({progress}%)...", '#007AFF')
            
            if old_path == new_path:
                success_count += 1
                continue
            
            if os.path.exists(new_path):
                fail_count += 1
                fail_messages.append(f"文件 {new_name} 已存在")
                continue
            
            try:
                if is_copy:
                    shutil.copy2(old_path, new_path)
                else:
                    os.rename(old_path, new_path)
                current_undo.append((new_name, filename))
                success_count += 1
            except Exception as e:
                fail_count += 1
                fail_messages.append(f"{filename} -> {new_name}：{str(e)}")
        
        if current_undo and not is_copy:
            self.undo_stack.append(current_undo)
            if len(self.undo_stack) > MAX_UNDO:
                self.undo_stack = self.undo_stack[-MAX_UNDO:]
        
        elapsed_time = time.time() - start_time
        self.root.after(0, self.rename_complete, success_count, fail_count, fail_messages, elapsed_time)
    
    def rename_complete(self, success_count, fail_count, fail_messages, elapsed_time=0):
        self.is_running = False
        self.btn_rename.config(state='normal')
        self.btn_preview.config(state='normal')
        
        if self.undo_stack:
            self.btn_undo.config(state='normal')
            undo_count = len(self.undo_stack)
            self.btn_undo.config(text=f"撤销 ({undo_count}次)")
        
        if success_count > 0:
            self.add_to_history()
        
        self.refresh_file_list()
        
        if fail_count == 0:
            self.update_status(f"✓ 重命名完成！成功 {success_count} 个", '#00C853')
        else:
            self.update_status(f"✓ 重命名完成！成功 {success_count} 个，失败 {fail_count} 个", '#FF9800')
        
        for i in range(100, -1, -5):
            self.update_progress(i)
        
        self.root.after(100, self.update_progress, 0)
        
        self.show_rename_report(success_count, fail_count, fail_messages, elapsed_time)
    
    def show_rename_report(self, success_count, fail_count, fail_messages, elapsed_time):
        report_window = tk.Toplevel(self.root)
        report_window.title("重命名统计报告")
        report_window.geometry("500x400")
        report_window.resizable(False, False)
        report_window.attributes('-topmost', True)
        
        theme = self.get_theme()
        
        title_label = ttk.Label(report_window, text="📊 重命名统计报告", 
                               font=('Microsoft YaHei UI', 14, 'bold'),
                               foreground=theme['primary'])
        title_label.pack(pady=(15, 10))
        
        stats_frame = ttk.Frame(report_window)
        stats_frame.pack(pady=10, padx=20, fill=tk.X)
        
        total = success_count + fail_count
        
        ttk.Label(stats_frame, text=f"📁 总文件数：{total}", 
                 font=('Microsoft YaHei UI', 11)).pack(anchor='w', pady=3)
        
        ttk.Label(stats_frame, text=f"✓ 成功：{success_count}", 
                 font=('Microsoft YaHei UI', 11),
                 foreground=theme['success']).pack(anchor='w', pady=3)
        
        ttk.Label(stats_frame, text=f"✗ 失败：{fail_count}", 
                 font=('Microsoft YaHei UI', 11),
                 foreground=theme['danger']).pack(anchor='w', pady=3)
        
        if total > 0:
            success_rate = f"{success_count / total * 100:.1f}"
            ttk.Label(stats_frame, text=f"📈 成功率：{success_rate}%", 
                     font=('Microsoft YaHei UI', 11)).pack(anchor='w', pady=3)
        
        ttk.Label(stats_frame, text=f"⏱️ 耗时：{elapsed_time:.2f} 秒", 
                 font=('Microsoft YaHei UI', 11)).pack(anchor='w', pady=3)
        
        if elapsed_time > 0 and success_count > 0:
            speed = success_count / elapsed_time
            ttk.Label(stats_frame, text=f"⚡ 速度：{speed:.1f} 文件/秒", 
                     font=('Microsoft YaHei UI', 11)).pack(anchor='w', pady=3)
        
        if fail_messages:
            ttk.Label(report_window, text="❌ 失败详情：", 
                     font=('Microsoft YaHei UI', 11, 'bold')).pack(anchor='w', padx=20, pady=(10, 5))
            
            scroll_frame = ttk.Frame(report_window)
            scroll_frame.pack(pady=5, padx=20, fill=tk.BOTH, expand=True)
            
            scrollbar = ttk.Scrollbar(scroll_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            text_widget = tk.Text(scroll_frame, 
                                 height=5,
                                 font=('Microsoft YaHei UI', 9),
                                 bg=theme['card_bg'],
                                 fg=theme['text'],
                                 yscrollcommand=scrollbar.set)
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            scrollbar.config(command=text_widget.yview)
            
            for msg in fail_messages:
                text_widget.insert(tk.END, f"• {msg}\n")
            
            text_widget.config(state='disabled')
        
        ttk.Button(report_window, text="关闭", 
                   command=report_window.destroy,
                   style='Primary.TButton').pack(pady=15)
    
    def undo_rename(self):
        if not self.undo_stack:
            return
        
        self.is_running = True
        self.btn_undo.config(state='disabled')
        
        undo_data = self.undo_stack.pop()
        
        success_count = 0
        fail_count = 0
        
        for new_name, old_name in undo_data:
            old_path = os.path.join(self.folder_path, old_name)
            new_path = os.path.join(self.folder_path, new_name)
            
            if os.path.exists(new_path):
                try:
                    os.rename(new_path, old_path)
                    success_count += 1
                except Exception as e:
                    fail_count += 1
        
        self.is_running = False
        
        if self.undo_stack:
            undo_count = len(self.undo_stack)
            self.btn_undo.config(state='normal', text=f"撤销 ({undo_count}次)")
        
        self.refresh_file_list()
        
        if fail_count == 0:
            self.update_status(f"✓ 撤销完成！成功恢复 {success_count} 个文件", '#00C853')
        else:
            self.update_status(f"✓ 撤销完成！成功恢复 {success_count} 个，失败 {fail_count} 个", '#FF9800')
    
    def undo_rename_shortcut(self, event=None):
        if self.btn_undo['state'] != 'disabled':
            self.undo_rename()
    
    def update_status(self, text, color):
        self.status_label.config(text=text, foreground=color)
    
    def update_progress(self, value):
        self.progress_bar['value'] = value
    
    def export_list(self):
        if not self.files:
            messagebox.showwarning("提示", "请先选择文件夹")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV文件', '*.csv'), ('所有文件', '*.*')],
            title='导出重命名清单'
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(['原始文件名', '重命名预览'])
                    for i, filename in enumerate(self.files):
                        preview_name = generate_new_name(filename, self.mode.get(), self.get_params(i))
                        writer.writerow([filename, preview_name])
                self.update_status(f"✓ 清单已导出到 {file_path}", '#00C853')
            except Exception as e:
                messagebox.showerror("错误", f"导出失败：{str(e)}")
    
    def on_tree_double_click(self, event):
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            values = self.tree.item(item, 'values')
            if values:
                filename = values[0]
                self.show_image_preview(filename)
    
    def on_tree_select(self, event):
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            values = self.tree.item(item, 'values')
            if values:
                filename = values[0]
                self.show_image_preview(filename)
        else:
            self.preview_canvas.delete('all')
            self.preview_label.config(text="选择图片文件查看预览")
    
    def show_image_preview(self, filename):
        if not HAS_PIL:
            self.preview_label.config(text="需要安装 Pillow\npip install pillow")
            return
        
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
            self.preview_label.config(text="不支持的文件格式")
            self.preview_canvas.delete('all')
            self._preview_image = None
            return
        
        file_path = os.path.join(self.folder_path, filename)
        
        try:
            self._preview_image = Image.open(file_path)
            self._preview_filename = filename
            
            self.render_preview_image()
            
        except Exception as e:
            self.preview_label.config(text=f"预览失败：{str(e)}")
            self.preview_canvas.delete('all')
            self._preview_image = None
    
    def render_preview_image(self):
        if self._preview_image is None:
            return
        
        self.preview_canvas.update_idletasks()
        
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 200
            canvas_height = 200
        
        max_width = canvas_width - 20
        max_height = canvas_height - 20
        
        img_width, img_height = self._preview_image.size
        aspect_ratio = img_width / img_height
        
        if img_width > max_width or img_height > max_height:
            if max_width / aspect_ratio <= max_height:
                new_width = max_width
                new_height = max_width / aspect_ratio
            else:
                new_height = max_height
                new_width = max_height * aspect_ratio
            resized_image = self._preview_image.resize((int(new_width), int(new_height)), Image.LANCZOS)
        else:
            resized_image = self._preview_image
        
        photo = ImageTk.PhotoImage(resized_image)
        
        self.preview_canvas.delete('all')
        
        x = (canvas_width - photo.width()) // 2
        y = (canvas_height - photo.height()) // 2
        
        self.preview_canvas.create_image(x, y, image=photo, anchor='nw')
        self.preview_canvas.image = photo
        
        if hasattr(self, '_preview_filename'):
            self.preview_label.config(text=self._preview_filename)
    
    def on_preview_canvas_resize(self, event):
        self.render_preview_image()
    
    def on_preview_double_click(self, event):
        if self._preview_image is None:
            return
        
        if hasattr(self, 'zoom_dialog') and self.zoom_dialog.winfo_exists():
            self.zoom_dialog.lift()
            return
        
        theme = self.get_theme()
        self.zoom_dialog = tk.Toplevel(self.root)
        self.zoom_dialog.title(f"图片预览 - {self._preview_filename}")
        self.zoom_dialog.geometry("900x700")
        self.zoom_dialog.transient(self.root)
        self.zoom_dialog.configure(bg=theme['card_bg'])
        
        canvas = tk.Canvas(self.zoom_dialog, bg=theme['card_bg'],
                          highlightthickness=1,
                          highlightbackground=theme['border'])
        canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        image = self._preview_image
        
        def render_zoom_image():
            canvas.update_idletasks()
            
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                canvas_width = 900
                canvas_height = 700
            
            max_width = canvas_width - 40
            max_height = canvas_height - 40
            
            img_width, img_height = image.size
            aspect_ratio = img_width / img_height
            
            if img_width > max_width or img_height > max_height:
                if max_width / aspect_ratio <= max_height:
                    new_width = max_width
                    new_height = max_width / aspect_ratio
                else:
                    new_height = max_height
                    new_width = max_height * aspect_ratio
                resized_image = image.resize((int(new_width), int(new_height)), Image.LANCZOS)
            else:
                resized_image = image
            
            photo = ImageTk.PhotoImage(resized_image)
            
            canvas.delete('all')
            
            x = (canvas_width - photo.width()) // 2
            y = (canvas_height - photo.height()) // 2
            
            canvas.create_image(x, y, image=photo, anchor='nw')
            canvas.image = photo
        
        canvas.bind('<Configure>', lambda e: render_zoom_image())
        zoom_dialog.after(50, render_zoom_image)
    
    def batch_move(self):
        if not self.files:
            messagebox.showwarning("提示", "请先选择文件夹")
            return
        
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要移动的文件（可使用 Ctrl+A 全选）")
            return
        
        target_path = filedialog.askdirectory(title="选择目标文件夹")
        if not target_path:
            return
        
        if target_path == self.folder_path:
            messagebox.showwarning("提示", "目标文件夹不能与源文件夹相同")
            return
        
        selected_files = []
        for item in selection:
            values = self.tree.item(item, 'values')
            if values:
                selected_files.append(values[0])
        
        self.is_running = True
        self.btn_move.config(state='disabled')
        self.update_status("正在移动文件...", '#007AFF')
        self.update_progress(0)
        
        thread = threading.Thread(target=self.move_thread, args=(target_path, selected_files), daemon=True)
        thread.start()
    
    def move_thread(self, target_path, selected_files):
        success_count = 0
        fail_count = 0
        total_files = len(selected_files)
        
        for i, filename in enumerate(selected_files):
            if not self.is_running:
                break
            
            old_path = os.path.join(self.folder_path, filename)
            new_path = os.path.join(target_path, filename)
            
            if not os.path.exists(old_path):
                fail_count += 1
                continue
            
            progress = int((i + 1) / total_files * 100)
            self.root.after(0, self.update_progress, progress)
            self.root.after(0, self.update_status, 
                           f"正在移动 {i + 1}/{total_files} ({progress}%)...", '#007AFF')
            
            if os.path.exists(new_path):
                fail_count += 1
                continue
            
            try:
                shutil.move(old_path, new_path)
                success_count += 1
            except Exception as e:
                fail_count += 1
        
        self.root.after(0, self.move_complete, success_count, fail_count)
    
    def move_complete(self, success_count, fail_count):
        self.is_running = False
        self.btn_move.config(state='normal')
        self.refresh_file_list()
        
        if fail_count == 0:
            self.update_status(f"✓ 移动完成！成功 {success_count} 个", '#00C853')
        else:
            self.update_status(f"✓ 移动完成！成功 {success_count} 个，失败 {fail_count} 个", '#FF9800')
        
        for i in range(100, -1, -5):
            self.update_progress(i)
        self.root.after(100, self.update_progress, 0)
    
    def show_help(self):
        if hasattr(self, 'help_dialog') and self.help_dialog.winfo_exists():
            self.help_dialog.lift()
            return
        
        theme = self.get_theme()
        
        self.help_dialog = tk.Toplevel(self.root)
        self.help_dialog.title("使用帮助")
        self.help_dialog.geometry("700x600")
        self.help_dialog.transient(self.root)
        self.help_dialog.grab_set()
        self.help_dialog.configure(bg=theme['card_bg'])
        
        notebook = ttk.Notebook(self.help_dialog)
        
        basic_frame = ttk.Frame(notebook)
        regex_frame = ttk.Frame(notebook)
        recursive_frame = ttk.Frame(notebook)
        
        notebook.add(basic_frame, text='基本操作')
        notebook.add(regex_frame, text='正则表达式')
        notebook.add(recursive_frame, text='递归子文件夹')
        
        notebook.pack(fill=tk.BOTH, expand=True)
        
        basic_text = tk.Text(basic_frame, wrap='word', padx=15, pady=15, 
                             font=('Microsoft YaHei UI', 10),
                             bg=theme['card_bg'], fg=theme['text'])
        basic_text.insert(tk.END, """批量文件重命名工具 - 使用帮助

=== 基本操作 ===

1. 选择文件夹
   - 点击"选择文件夹"按钮选择要重命名的文件夹
   - 或者直接拖拽文件夹到软件窗口
   - 选择后会在旁边的下拉框中显示当前文件夹名称
   - 通过下拉框可快速切换到最近访问过的文件夹

2. 筛选文件
   - 在"过滤后缀"输入框中输入后缀（如 .jpg），只显示匹配的文件
   - 清空输入框可恢复显示所有文件

3. 排序文件
   - 文件名 (A-Z)/(Z-A)：按文件名排序
   - 修改时间（从旧到新/从新到旧）：按文件修改时间排序
   - 创建时间（从旧到新/从新到旧）：按文件创建时间排序
   - 文件大小（从小到大/从大到小）：按文件大小排序
   - 扩展名（A-Z)/(Z-A)：按文件扩展名排序

4. 重命名模式
   - 方式 A（前缀/后缀）：在文件名前后添加内容，中间自动编号
   - 方式 B（替换文本）：替换文件名中的指定文本，支持正则表达式
   - 方式 C（修改扩展名）：批量修改文件扩展名
   
   ● 修改扩展名使用说明：
     1. 选择"修改扩展名"模式
     2. 在"新扩展名"输入框中输入目标扩展名（如 jpg 或 .jpg）
     3. 点击"预览"查看效果，或直接点击"开始重命名"执行
     4. 示例：
        - 输入 "jpg" → 将所有文件扩展名改为 .jpg
        - 输入 ".png" → 将所有文件扩展名改为 .png
     5. 注意事项：
        - 修改扩展名不会改变文件内容，仅更改文件名后缀
        - 建议在修改前备份文件，或使用"复制到新文件夹"模式
        - 如果目标扩展名文件已存在，会跳过该文件

5. 日期模板（支持在前缀/后缀中使用）
   - {date} → 20260716
   - {time} → 153045
   - {year} → 2026
   - {month} → 07
   - {day} → 16
   - {hour} → 15
   - {minute} → 30
   - {second} → 45

6. 模板预设
   - 日期_序号：自动使用日期作为前缀
   - IMG_日期_序号：相机风格命名（如 IMG_20260716_001）
   - 视频_{time}：按时间命名
   - 文档_{year}{month}：按年月命名
   - 扫描件_序号：简单编号（如 扫描件_001）
   - {date}_{time}_序号：完整日期时间命名

7. 快捷键
   - Ctrl+A：全选文件列表中的所有文件
   - Ctrl+Z：一键撤销上一次重命名操作
   - Ctrl+R：开始执行重命名
   - Ctrl+P：生成重命名预览
   - Ctrl+E：导出重命名清单

8. 批量移动
   - 选中要移动的文件（可按住 Ctrl 多选，或 Ctrl+A 全选）
   - 点击"批量移动"按钮
   - 选择目标文件夹，文件将移动到新位置

9. 删除文件
   - 选中要删除的文件（可按住 Ctrl 多选）
   - 点击"🗑️ 删除文件"按钮
   - 删除前会弹出确认对话框
   - 删除后无法恢复，请谨慎操作

10. 导出清单
    - 将重命名前后的文件名导出为 CSV 文件
    - 方便记录、存档和分享

11. 测试模式
    - 勾选"测试模式（仅预览）"
    - 点击重命名时只生成预览效果，不执行实际重命名操作
    - 适合在执行大批量重命名前确认效果

12. 命名历史
    - 自动保存最近10次重命名规则
    - 双击历史记录可快速应用到当前设置
    - 记录包括：前缀、后缀、编号位数、查找/替换文本等

13. 窗口置顶
    - 点击右上角"🖥️ 置顶"按钮
    - 窗口会始终显示在其他窗口上方
    - 置顶后按钮变为"🖥️ 已置顶"并高亮显示

14. 主题切换
    - 点击右上角"🌙 深色"按钮切换主题
    - 支持浅色/深色两种现代化主题
    - 主题设置会自动保存，下次启动时恢复
    - 点击"🎨 主题"按钮可自定义主色调

15. 自定义主题
    - 点击"🎨 主题"按钮打开主题设置窗口
    - 提供9种预设主色调：科技蓝、活力橙、清新绿、优雅紫、沉稳灰、经典红、天空蓝、玫瑰红、柠檬黄
    - 点击颜色按钮即可应用该主题
    - 点击"重置为默认"恢复默认主题

16. 图片预览
    - 点击图片文件（.jpg, .png, .gif, .bmp, .tiff）在右侧预览
    - 支持拖动分隔条调整预览区域大小
    - 图片会自动缩放并居中显示
    - 预览区域大小变化时，图片会实时自适应调整
    - 双击预览区域的图片可打开放大窗口查看原图
    - 放大窗口支持调整大小，图片会实时自适应

17. 递归子文件夹
    - 勾选"递归子文件夹"
    - 程序会扫描所选文件夹及其所有子文件夹中的文件
    - 列表中显示文件相对路径，重命名时保留原文件夹结构

18. 目标文件夹选择
    - 覆盖当前文件夹：直接在原位置重命名文件
    - 复制到新文件夹：将文件复制并重命名到指定文件夹
    - 适合需要保留原文件的场景

19. 设置保存
    - 程序会自动保存以下设置：
      * 当前主题（浅色/深色）
      * 窗口置顶状态
      * 默认排序方式
      * 最近访问的文件夹
    - 下次启动时自动恢复上次的设置

20. 文件名冲突检测
    - 在预览时自动检测重命名后是否有重复的文件名
    - 冲突文件名显示为红色并带有 ⚠️ 标记
    - 状态栏显示冲突数量，弹出警告提示

21. 重命名统计报告
    - 执行重命名后自动弹出统计报告窗口
    - 显示：总文件数、成功数、失败数、成功率、耗时、处理速度
    - 失败详情列表，支持滚动查看

=== 功能说明 ===

● 智能编号位数
  - 选择"自动"时，系统根据文件总数自动计算位数（最少2位）
  - 手动选择（2位/3位/4位/5位）则强制使用指定位数进行补零

● 一键撤销
  - 支持最多5次撤销操作
  - 按钮显示可撤销次数（如"撤销 (3次)"）
  - 每次撤销会恢复上一次重命名的所有文件

● 文件统计
  - 底部显示文件总数、总大小、各类型文件数量
  - 方便了解当前文件夹的文件情况

● 正则表达式替换
  - 在"替换文本"模式下勾选"正则表达式"
  - 支持复杂的文本匹配和替换操作
  - 支持分组捕获和引用（详见正则表达式标签页）

● 异步处理
  - 重命名和移动操作在后台线程执行
  - 界面不会卡死，可以随时取消操作
  - 显示实时进度条和状态信息

● 最近文件夹
  - 自动记录最近访问的5个文件夹
  - 在选择文件夹按钮旁的下拉框中显示
  - 一键快速访问历史文件夹
""")
        basic_text.config(state='disabled')
        basic_text.pack(fill=tk.BOTH, expand=True)
        
        regex_text = tk.Text(regex_frame, wrap='word', padx=15, pady=15, 
                           font=('Microsoft YaHei UI', 10),
                           bg=theme['card_bg'], fg=theme['text'])
        regex_text.insert(tk.END, """=== 正则表达式使用指南 ===

正则表达式是一种强大的文本匹配工具，可以实现复杂的文件名替换。

--- 基础语法 ---

1. 匹配单个字符
   - . : 匹配任意单个字符（除换行符）
   - \\d : 匹配任意数字（0-9）
   - \\w : 匹配字母、数字或下划线
   - \\s : 匹配空白字符（空格、制表符等）

2. 匹配数量
   - * : 匹配前面的元素零次或多次
   - + : 匹配前面的元素一次或多次
   - ? : 匹配前面的元素零次或一次
   - {n} : 精确匹配 n 次
   - {n,m} : 匹配 n 到 m 次

3. 匹配位置
   - ^ : 匹配字符串开头
   - $ : 匹配字符串结尾

4. 字符类
   - [abc] : 匹配 a、b 或 c
   - [^abc] : 匹配除 a、b、c 以外的字符
   - [a-z] : 匹配 a 到 z 之间的任意字母

5. 分组和捕获
   - () : 创建分组，可以被引用
   - \\1, \\2 : 引用第1、第2个分组

--- 常用示例 ---

示例1：提取数字
原始文件名：photo_001.jpg
查找：^.*?(\\d+)$
替换：image_\\1
结果：image_001.jpg

示例2：移除特定前缀
原始文件名：DSC_0001.jpg
查找：^DSC_
替换：（留空）
结果：0001.jpg

示例3：替换日期格式
原始文件名：IMG_2023-12-25.jpg
查找：(\\d{4})-(\\d{2})-(\\d{2})
替换：\\1\\2\\3
结果：IMG_20231225.jpg

示例4：匹配多个模式
原始文件名：VID_001.mp4, PHOTO_002.jpg
查找：^(VID|PHOTO)_
替换：media_
结果：media_001.mp4, media_002.jpg

示例5：保留扩展名前的内容
原始文件名：Document2026_v1.pdf
查找：(\\d{4}).*?\\.(.*)$
替换：\\1_version.\\2
结果：2026_version.pdf

--- 注意事项 ---

1. 正则表达式区分大小写，如需忽略大小写，可使用 (?i) 前缀
   示例：(?i)photo → 匹配 Photo, PHOTO, photo 等

2. 特殊字符需要转义（使用 \\）：
   . * + ? ^ $ [ ] ( ) { } | \\

3. 在"替换为"中可以使用分组引用：
   \\1 表示第一个分组，\\2 表示第二个分组

4. 如果正则表达式有误，程序会自动回退到普通文本替换

5. 建议先使用"预览"功能确认替换效果再执行重命名
""")
        regex_text.config(state='disabled')
        regex_text.pack(fill=tk.BOTH, expand=True)
        
        recursive_text = tk.Text(recursive_frame, wrap='word', padx=15, pady=15, 
                             font=('Microsoft YaHei UI', 10),
                             bg=theme['card_bg'], fg=theme['text'])
        recursive_text.insert(tk.END, """=== 递归子文件夹使用指南 ===

启用"递归子文件夹"功能后，程序会扫描所选文件夹及其所有子文件夹中的文件。

--- 使用场景 ---

1. 批量处理整个项目中的图片
   - 项目文件夹下有多个子文件夹（如 photos/、images/、assets/）
   - 需要统一重命名所有图片

2. 整理多层级的文档
   - 文档按年份/月份分文件夹存放
   - 需要统一添加日期前缀

--- 注意事项 ---

1. 文件路径显示
   - 列表中会显示文件的相对路径（如 subfolder/file.jpg）
   - 这有助于识别文件所在位置

2. 重命名时的路径处理
   - 重命名操作会保留原有的文件夹结构
   - 例如：subfolder/photo.jpg → subfolder/IMG_001.jpg

3. 复制模式
   - 在"复制到新文件夹"模式下，会自动创建对应的子文件夹结构
   - 确保目标文件夹为空或不存在同名文件

4. 性能提示
   - 如果文件夹层级很深或文件数量很大，扫描可能需要一些时间
   - 建议先在测试模式下预览效果

--- 示例 ---

原始结构：
project/
  ├── 2023/
  │   ├── img001.jpg
  │   └── img002.jpg
  └── 2024/
      └── img003.jpg

启用递归后，文件列表显示：
- 2023/img001.jpg
- 2023/img002.jpg
- 2024/img003.jpg

使用前缀"photo_"重命名后：
project/
  ├── 2023/
  │   ├── photo_001.jpg
  │   └── photo_002.jpg
  └── 2024/
      └── photo_003.jpg
""")
        recursive_text.config(state='disabled')
        recursive_text.pack(fill=tk.BOTH, expand=True)
    
    def show_history(self):
        if not self.rename_history:
            messagebox.showinfo("提示", "暂无命名历史记录")
            return
        
        if hasattr(self, 'history_dialog') and self.history_dialog.winfo_exists():
            self.history_dialog.lift()
            return
        
        theme = self.get_theme()
        
        self.history_dialog = tk.Toplevel(self.root)
        self.history_dialog.title("命名历史")
        self.history_dialog.geometry("600x500")
        self.history_dialog.transient(self.root)
        self.history_dialog.grab_set()
        self.history_dialog.configure(bg=theme['card_bg'])
        
        tree = ttk.Treeview(self.history_dialog, columns=('index', 'mode', 'rule', 'time'), 
                            show='headings', height=15)
        tree.heading('index', text='序号')
        tree.heading('mode', text='模式')
        tree.heading('rule', text='规则')
        tree.heading('time', text='时间')
        
        tree.column('index', width=60)
        tree.column('mode', width=100)
        tree.column('rule', width=300)
        tree.column('time', width=140)
        
        scrollbar = ttk.Scrollbar(history_dialog, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        for i, rule in enumerate(self.rename_history):
            mode_name = '前缀/后缀' if rule['mode'] == 'prefix_suffix' else '替换文本'
            if rule['mode'] == 'change_ext':
                mode_name = '修改扩展名'
            
            if rule['mode'] == 'prefix_suffix':
                rule_str = f"前缀='{rule['prefix']}', 后缀='{rule['suffix']}', {rule['digit_mode']}"
            elif rule['mode'] == 'replace':
                rule_str = f"查找='{rule['find_text']}', 替换='{rule['replace_text']}'"
            else:
                rule_str = f"新扩展名='{rule['new_ext']}'"
            
            timestamp = rule.get('timestamp', '')
            if timestamp:
                dt = datetime.datetime.fromisoformat(timestamp)
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            else:
                time_str = ''
            
            tree.insert('', tk.END, values=(i + 1, mode_name, rule_str, time_str))
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def on_double_click(event):
            selection = tree.selection()
            if selection:
                item = selection[0]
                idx = int(tree.item(item, 'values')[0]) - 1
                rule = self.rename_history[idx]
                
                self.mode.set(rule['mode'])
                self.update_mode_ui()
                
                if rule['mode'] == 'prefix_suffix':
                    self.prefix_entry.delete(0, tk.END)
                    self.prefix_entry.insert(0, rule.get('prefix', ''))
                    self.suffix_entry.delete(0, tk.END)
                    self.suffix_entry.insert(0, rule.get('suffix', ''))
                    self.digit_combobox.set(rule.get('digit_mode', '自动'))
                elif rule['mode'] == 'replace':
                    self.find_entry.delete(0, tk.END)
                    self.find_entry.insert(0, rule.get('find_text', ''))
                    self.replace_entry.delete(0, tk.END)
                    self.replace_entry.insert(0, rule.get('replace_text', ''))
                    self.use_regex.set(rule.get('use_regex', False))
                elif rule['mode'] == 'change_ext':
                    self.new_ext_entry.delete(0, tk.END)
                    self.new_ext_entry.insert(0, rule.get('new_ext', ''))
                
                if self.files:
                    self.generate_preview()
                history_dialog.destroy()
        
        tree.bind('<Double-1>', on_double_click)
        
        ttk.Label(history_dialog, text="双击历史记录可快速应用", 
                  font=('Microsoft YaHei UI', 9), foreground='#999999').pack(side=tk.BOTTOM, pady=10)


def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    app = BatchRenameTool(root)
    root.mainloop()


if __name__ == "__main__":
    main()