#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于图像识别的自动答题脚本 - 图形化界面版本
支持屏幕截图、OCR 识别、题目解析、答案匹配和自动点击
"""

import os
import re
import time
import threading
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum

# GUI 相关导入
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from PIL import Image, ImageTk


class RegionSelector:
    """屏幕区域选择器 - 支持鼠标拖拽选区"""
    
    def __init__(self, callback=None):
        self.callback = callback
        self.start_x = None
        self.start_y = None
        self.current_x = None
        self.current_y = None
        self.rect_id = None
        self.selection = None
        
    def start_selection(self):
        """启动区域选择"""
        # 创建全屏透明窗口
        self.top = tk.Toplevel()
        self.top.attributes('-fullscreen', True)
        self.top.attributes('-alpha', 0.3)  # 半透明
        self.top.attributes('-topmost', True)
        self.top.configure(bg='black')
        
        # 获取屏幕尺寸
        screen_width = self.top.winfo_screenwidth()
        screen_height = self.top.winfo_screenheight()
        
        # 创建画布用于绘制选区
        self.canvas = tk.Canvas(self.top, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 绑定事件
        self.canvas.bind('<Button-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        
        # 按 ESC 取消
        self.top.bind('<Escape>', lambda e: self.cancel_selection())
        
        # 显示提示
        self.canvas.create_text(
            screen_width // 2, 50,
            text="按住鼠标左键拖动选择区域，松开完成选择 | 按 ESC 取消",
            fill='white', font=('Arial', 16, 'bold')
        )
        
    def on_press(self, event):
        """鼠标按下"""
        self.start_x = event.x
        self.start_y = event.y
        self.current_x = event.x
        self.current_y = event.y
        
    def on_drag(self, event):
        """鼠标拖动"""
        self.current_x = event.x
        self.current_y = event.y
        
        # 清除之前的矩形
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        
        # 计算矩形坐标
        x1 = min(self.start_x, self.current_x)
        y1 = min(self.start_y, self.current_y)
        x2 = max(self.start_x, self.current_x)
        y2 = max(self.start_y, self.current_y)
        
        # 绘制绿色边框
        self.rect_id = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline='#00ff00', width=3
        )
        
        # 显示坐标和尺寸
        width = x2 - x1
        height = y2 - y1
        info_text = f"坐标：({x1}, {y1})  尺寸：{width} x {height}"
        
        # 更新或创建信息文本
        if hasattr(self, 'info_text_id'):
            self.canvas.delete(self.info_text_id)
        self.info_text_id = self.canvas.create_text(
            x1 + 10, y1 - 20,
            text=info_text,
            fill='#00ff00', font=('Arial', 12, 'bold'),
            anchor='sw'
        )
        
    def on_release(self, event):
        """鼠标释放"""
        self.current_x = event.x
        self.current_y = event.y
        
        # 计算最终选区
        x1 = min(self.start_x, self.current_x)
        y1 = min(self.start_y, self.current_y)
        x2 = max(self.start_x, self.current_x)
        y2 = max(self.start_y, self.current_y)
        
        # 确保选区有效
        if x2 - x1 > 10 and y2 - y1 > 10:
            self.selection = (x1, y1, x2 - x1, y2 - y1)
            self.close_and_callback()
        else:
            # 选区太小，忽略
            if self.rect_id:
                self.canvas.delete(self.rect_id)
            
    def cancel_selection(self):
        """取消选择"""
        self.selection = None
        try:
            self.top.destroy()
        except:
            pass
            
    def close_and_callback(self):
        """关闭窗口并回调"""
        try:
            self.top.destroy()
        except:
            pass
        
        if self.callback and self.selection:
            self.callback(self.selection)


class QuestionType(Enum):
    """题目类型枚举"""
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"
    UNKNOWN = "unknown"


@dataclass
class Question:
    """题目数据类"""
    question_text: str
    options: List[str]
    question_type: QuestionType
    image_path: Optional[str] = None


class ImageCapture:
    """图像捕获模块"""
    
    @staticmethod
    def capture_screen(region: Optional[tuple] = None, save_path: str = "screenshot.png") -> str:
        """截取屏幕图像"""
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab(bbox=region)
            screenshot.save(save_path)
            return save_path
        except ImportError:
            raise ImportError("请安装 Pillow 库 (pip install Pillow)")
        except Exception as e:
            raise Exception(f"截图失败：{e}")


class OCRRecognizer:
    """OCR 文字识别模块"""
    
    def __init__(self, engine: str = "paddleocr"):
        self.engine = engine
        self.ocr = None
        self._init_engine()
    
    def _init_engine(self):
        """初始化选定的 OCR 引擎"""
        if self.engine == "paddleocr":
            try:
                from paddleocr import PaddleOCR
                self.ocr = PaddleOCR(use_angle_cls=True, lang="ch")
            except ImportError:
                raise ImportError("PaddleOCR 未安装，请运行：pip install paddlepaddle paddleocr")
        
        elif self.engine == "tesseract":
            try:
                import pytesseract
                self.ocr = pytesseract
            except ImportError:
                raise ImportError("请安装 pytesseract (pip install pytesseract)")
        
        elif self.engine == "easyocr":
            try:
                import easyocr
                self.ocr = easyocr.Reader(['ch_sim', 'en'])
            except ImportError:
                raise ImportError("请安装 easyocr (pip install easyocr)")
    
    def recognize(self, image_path: str) -> List[Dict]:
        """识别图像中的文字"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图像文件不存在：{image_path}")
        
        if self.engine == "paddleocr":
            result = self.ocr.ocr(image_path, cls=True)
            texts = []
            if result and result[0]:
                for line in result[0]:
                    if line:
                        texts.append({
                            'text': line[1][0],
                            'confidence': line[1][1],
                            'box': line[0]
                        })
            return texts
        
        elif self.engine == "tesseract":
            img = Image.open(image_path)
            text = self.ocr.image_to_string(img, lang='chi_sim+eng')
            return [{'text': text, 'confidence': 1.0, 'box': None}]
        
        elif self.engine == "easyocr":
            result = self.ocr.readtext(image_path)
            texts = []
            for bbox, text, confidence in result:
                texts.append({
                    'text': text,
                    'confidence': confidence,
                    'box': bbox
                })
            return texts
        
        return []


class QuestionParser:
    """题目解析模块"""
    
    def parse(self, ocr_results: List[Dict]) -> Question:
        """从 OCR 结果中解析题目"""
        full_text = "\n".join([item['text'] for item in ocr_results if item.get('text')])
        question_text = self._extract_question_text(full_text)
        options = self._extract_options(full_text)
        question_type = self._determine_type(question_text, options)
        
        return Question(
            question_text=question_text,
            options=options,
            question_type=question_type
        )
    
    def _extract_question_text(self, text: str) -> str:
        """提取题目正文"""
        lines = text.strip().split('\n')
        question_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if re.match(r'^[A-D]\.|^[A-D]、|^(\d+)\.', line):
                break
            question_lines.append(line)
        
        return ' '.join(question_lines)
    
    def _extract_options(self, text: str) -> List[str]:
        """提取选项"""
        options = []
        pattern = r'([A-D])[.、]\s*([^\n]+)'
        matches = re.findall(pattern, text)
        
        if matches:
            options = [match[1].strip() for match in matches]
        
        return options
    
    def _determine_type(self, question_text: str, options: List[str]) -> QuestionType:
        """判断题目类型"""
        if len(options) == 2:
            if any(kw in question_text for kw in ['正确', '错误', '对', '错']):
                return QuestionType.TRUE_FALSE
        
        if len(options) == 4:
            return QuestionType.SINGLE_CHOICE
        
        if len(options) > 4:
            return QuestionType.MULTIPLE_CHOICE
        
        if not options and ('_' in question_text or '填空' in question_text):
            return QuestionType.FILL_BLANK
        
        return QuestionType.UNKNOWN


class AnswerMatcher:
    """答案匹配模块"""
    
    def __init__(self, answer_db_path: str = "answer_database.txt"):
        self.answer_db_path = answer_db_path
        self.answer_database = self._load_answer_database()
    
    def _load_answer_database(self) -> Dict[str, str]:
        """加载答案数据库"""
        database = {}
        if os.path.exists(self.answer_db_path):
            with open(self.answer_db_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            database[parts[0].strip()] = parts[1].strip()
        return database
    
    def find_answer(self, question: Question) -> Optional[str]:
        """查找题目答案"""
        # 精确匹配
        if question.question_text in self.answer_database:
            return self.answer_database[question.question_text]
        
        # 模糊匹配
        keywords = self._extract_keywords(question.question_text)
        for db_question, answer in self.answer_database.items():
            if any(kw in db_question for kw in keywords if len(kw) > 2):
                return answer
        
        return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        stop_words = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        words = re.findall(r'[\u4e00-\u9fa5]{2,}', text)
        return [w for w in words if w not in stop_words]
    
    def add_answer(self, question_text: str, answer: str):
        """添加答案到数据库"""
        self.answer_database[question_text] = answer
        self._save_answer_database()
    
    def _save_answer_database(self):
        """保存答案数据库"""
        with open(self.answer_db_path, 'w', encoding='utf-8') as f:
            for question, answer in self.answer_database.items():
                f.write(f"{question}: {answer}\n")


class AutoClicker:
    """自动点击模块"""
    
    @staticmethod
    def click_option(option_label: str, options: List[str], option_positions: Dict[str, tuple]):
        """点击指定选项"""
        try:
            import pyautogui
            
            if option_label.upper() in option_positions:
                x, y = option_positions[option_label.upper()]
                pyautogui.click(x, y)
                return True
            else:
                # 尝试根据选项文本位置点击
                for i, opt in enumerate(options):
                    label = chr(65 + i)
                    if label == option_label.upper() and label in option_positions:
                        x, y = option_positions[label]
                        pyautogui.click(x, y)
                        return True
            return False
        except ImportError:
            raise ImportError("请安装 pyautogui (pip install pyautogui)")


class AutoAnswerBot:
    """自动答题机器人主类"""
    
    def __init__(self, ocr_engine: str = "paddleocr", answer_db: str = "answer_database.txt"):
        self.image_capture = ImageCapture()
        self.ocr_recognizer = OCRRecognizer(engine=ocr_engine)
        self.question_parser = QuestionParser()
        self.answer_matcher = AnswerMatcher(answer_db_path=answer_db)
        self.last_question = None
        self.last_answer = None
    
    def answer_from_screen(self, region: Optional[tuple] = None, auto_click: bool = False, 
                          answer_label: Optional[str] = None) -> tuple:
        """从屏幕截图自动答题"""
        screenshot_path = self.image_capture.capture_screen(region=region)
        ocr_results = self.ocr_recognizer.recognize(screenshot_path)
        question = self.question_parser.parse(ocr_results)
        self.last_question = question
        
        answer = None
        if answer_label:
            answer = answer_label.upper()
        else:
            answer = self.answer_matcher.find_answer(question)
        
        self.last_answer = answer
        
        if answer and auto_click and question.options:
            try:
                option_positions = self._detect_option_positions(ocr_results)
                AutoClicker.click_option(answer, question.options, option_positions)
            except Exception as e:
                pass
        
        return question, answer
    
    def answer_from_image(self, image_path: str, auto_click: bool = False,
                         answer_label: Optional[str] = None) -> tuple:
        """从图像文件自动答题"""
        ocr_results = self.ocr_recognizer.recognize(image_path)
        question = self.question_parser.parse(ocr_results)
        self.last_question = question
        
        answer = None
        if answer_label:
            answer = answer_label.upper()
        else:
            answer = self.answer_matcher.find_answer(question)
        
        self.last_answer = answer
        return question, answer
    
    def _detect_option_positions(self, ocr_results: List[Dict]) -> Dict[str, tuple]:
        """检测选项位置"""
        positions = {}
        for item in ocr_results:
            text = item.get('text', '').strip()
            box = item.get('box')
            if box and len(text) >= 2:
                match = re.match(r'^([A-D])[.、]', text)
                if match:
                    label = match.group(1)
                    x_coords = [point[0] for point in box]
                    y_coords = [point[1] for point in box]
                    center_x = sum(x_coords) / len(x_coords)
                    center_y = sum(y_coords) / len(y_coords)
                    positions[label] = (center_x, center_y)
        return positions


class AnswerBotGUI:
    """答题机器人图形界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 智能答题助手 - 图形化界面")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # 初始化答题机器人
        self.bot = None
        self.is_processing = False
        self.auto_mode = False
        self.auto_thread = None
        
        # 设置样式
        self._setup_styles()
        
        # 创建界面
        self._create_menu()
        self._create_main_ui()
        
        # 状态栏
        self._create_status_bar()
        
        self.log_message("欢迎使用智能答题助手！请点击【初始化】按钮开始。")
    
    def _setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置颜色
        self.colors = {
            'bg': '#f0f0f0',
            'primary': '#4CAF50',
            'secondary': '#2196F3',
            'danger': '#f44336',
            'warning': '#ff9800',
            'text': '#333333'
        }
        
        self.root.configure(bg=self.colors['bg'])
    
    def _create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开图片...", command=self._load_image)
        file_menu.add_command(label="导入答题库...", command=self._import_answer_database)
        file_menu.add_command(label="保存答案数据库", command=self._save_database)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 设置菜单
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(label="OCR 引擎设置", command=self._show_ocr_settings)
        settings_menu.add_command(label="答案数据库管理", command=self._show_database_manager)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self._show_help)
        help_menu.add_command(label="关于", command=self._show_about)
    
    def _create_main_ui(self):
        """创建主界面"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部控制区
        self._create_control_panel(main_frame)
        
        # 中间显示区
        self._create_display_area(main_frame)
        
        # 底部操作区
        self._create_action_panel(main_frame)
    
    def _create_control_panel(self, parent):
        """创建控制面板"""
        control_frame = ttk.LabelFrame(parent, text="控制面板", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 第一行：初始化和截图区域
        row1 = ttk.Frame(control_frame)
        row1.pack(fill=tk.X, pady=5)
        
        ttk.Label(row1, text="OCR 引擎:").pack(side=tk.LEFT, padx=(0, 5))
        self.ocr_var = tk.StringVar(value="paddleocr")
        ocr_combo = ttk.Combobox(row1, textvariable=self.ocr_var, 
                                values=["paddleocr", "tesseract", "easyocr"], width=15)
        ocr_combo.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Button(row1, text="🚀 初始化", command=self._initialize_bot,
                  style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(row1, text="📸 截取屏幕", command=self._capture_screen).pack(side=tk.LEFT, padx=5)
        
        # 截图区域设置
        ttk.Label(row1, text="区域:").pack(side=tk.LEFT, padx=(20, 5))
        self.region_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row1, text="使用自定义区域", variable=self.region_var,
                       command=self._toggle_region_input).pack(side=tk.LEFT)
        
        # 框选按钮
        ttk.Button(row1, text="🖱️ 点击框选屏幕区域", command=self._open_region_selector,
                  style="Accent.TButton").pack(side=tk.LEFT, padx=10)
        
        self.region_inputs = []
        for label, var_name in [("X:", "x"), ("Y:", "y"), ("宽:", "w"), ("高:", "h")]:
            ttk.Label(row1, text=label).pack(side=tk.LEFT, padx=(10, 2))
            var = tk.StringVar(value="0")
            entry = ttk.Entry(row1, textvariable=var, width=6)
            entry.pack(side=tk.LEFT)
            entry.config(state=tk.DISABLED)
            self.region_inputs.append((var_name, var, entry))
        
        # 第二行：自动点击和连续模式
        row2 = ttk.Frame(control_frame)
        row2.pack(fill=tk.X, pady=5)
        
        self.auto_click_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row2, text="✅ 自动点击答案", variable=self.auto_click_var).pack(side=tk.LEFT, padx=5)
        
        self.continuous_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="🔄 连续答题模式", variable=self.continuous_var,
                       command=self._toggle_continuous).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row2, text="间隔 (秒):").pack(side=tk.LEFT, padx=(10, 5))
        self.interval_var = tk.StringVar(value="2.0")
        interval_spin = ttk.Spinbox(row2, textvariable=self.interval_var, from_=0.5, to=10.0,
                                   increment=0.5, width=5)
        interval_spin.pack(side=tk.LEFT)
        
        # 手动指定答案
        ttk.Label(row2, text="手动答案:").pack(side=tk.LEFT, padx=(20, 5))
        self.manual_answer_var = tk.StringVar()
        answer_combo = ttk.Combobox(row2, textvariable=self.manual_answer_var,
                                   values=["", "A", "B", "C", "D"], width=3)
        answer_combo.pack(side=tk.LEFT)
    
    def _create_display_area(self, parent):
        """创建显示区域"""
        display_frame = ttk.LabelFrame(parent, text="识别结果", padding="10")
        display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建 Notebook 用于多标签页
        notebook = ttk.Notebook(display_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 题目信息标签页
        question_frame = ttk.Frame(notebook, padding="10")
        notebook.add(question_frame, text="📝 题目信息")
        
        ttk.Label(question_frame, text="题目内容:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        self.question_text = scrolledtext.ScrolledText(question_frame, height=6, wrap=tk.WORD)
        self.question_text.pack(fill=tk.X, pady=5)
        
        ttk.Label(question_frame, text="题目类型:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        self.type_var = tk.StringVar(value="未识别")
        ttk.Label(question_frame, textvariable=self.type_var, 
                 foreground=self.colors['secondary']).pack(anchor=tk.W, pady=5)
        
        ttk.Label(question_frame, text="选项列表:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        self.options_text = scrolledtext.ScrolledText(question_frame, height=4, wrap=tk.WORD)
        self.options_text.pack(fill=tk.X, pady=5)
        
        # 答案信息标签页
        answer_frame = ttk.Frame(notebook, padding="10")
        notebook.add(answer_frame, text="💡 答案信息")
        
        ttk.Label(answer_frame, text="匹配答案:", font=('Arial', 12, 'bold')).pack(anchor=tk.W)
        self.answer_var = tk.StringVar(value="等待识别...")
        answer_label = ttk.Label(answer_frame, textvariable=self.answer_var,
                                font=('Arial', 14, 'bold'), foreground=self.colors['primary'])
        answer_label.pack(anchor=tk.W, pady=10)
        
        # 日志标签页
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="📋 运行日志")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置日志文本颜色
        self.log_text.tag_config('info', foreground='#2196F3')
        self.log_text.tag_config('success', foreground='#4CAF50')
        self.log_text.tag_config('warning', foreground='#ff9800')
        self.log_text.tag_config('error', foreground='#f44336')
    
    def _create_action_panel(self, parent):
        """创建操作面板"""
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X)
        
        # 主要操作按钮
        btn_frame = ttk.Frame(action_frame)
        btn_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(btn_frame, text="🎯 识别并答题", command=self._answer_question,
                  style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="➕ 添加答案", command=self._add_answer).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="📂 从图片答题", command=self._load_image).pack(side=tk.LEFT, padx=5)
        
        # 连续模式控制
        self.start_auto_btn = ttk.Button(btn_frame, text="▶️ 开始自动", 
                                        command=self._toggle_auto_mode)
        self.start_auto_btn.pack(side=tk.LEFT, padx=5)
        self.start_auto_btn.config(state=tk.DISABLED)
        
        # 清空按钮
        ttk.Button(btn_frame, text="🗑️ 清空", command=self._clear_display).pack(side=tk.RIGHT, padx=5)
    
    def _create_status_bar(self):
        """创建状态栏"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_label.pack(fill=tk.X, padx=5, pady=2)
    
    def _toggle_region_input(self):
        """切换区域输入框状态"""
        state = tk.NORMAL if self.region_var.get() else tk.DISABLED
        for _, var, entry in self.region_inputs:
            entry.config(state=state)
    
    def _open_region_selector(self):
        """打开区域选择器"""
        # 最小化主窗口
        self.root.iconify()
        time.sleep(0.2)  # 等待窗口最小化
        
        def on_region_selected(region):
            """处理选中的区域"""
            # 恢复主窗口
            self.root.after(100, lambda: self.root.deiconify())
            
            # 填充区域值
            x, y, w, h = region
            self.region_var.set(True)
            self._toggle_region_input()
            
            # 更新输入框
            for i, (name, var, entry) in enumerate(self.region_inputs):
                if name == 'x':
                    var.set(str(x))
                elif name == 'y':
                    var.set(str(y))
                elif name == 'w':
                    var.set(str(w))
                elif name == 'h':
                    var.set(str(h))
            
            self.log_message(f"✓ 已选择区域：({x}, {y}) {w}x{h}", 'success')
            
            # 截取预览图
            try:
                preview_path = "region_preview.png"
                from PIL import ImageGrab
                screenshot = ImageGrab.grab(bbox=(x, y, x+w, y+h))
                screenshot.save(preview_path)
                self.log_message(f"✓ 区域预览已保存：{preview_path}", 'info')
            except Exception as e:
                self.log_message(f"预览保存失败：{e}", 'warning')
        
        # 启动区域选择器
        selector = RegionSelector(callback=on_region_selected)
        selector.start_selection()
    
    def _toggle_continuous(self):
        """切换连续模式"""
        if self.continuous_var.get():
            self.start_auto_btn.config(state=tk.NORMAL)
        else:
            self.auto_mode = False
            self.start_auto_btn.config(state=tk.DISABLED)
            self.start_auto_btn.config(text="▶️ 开始自动")
    
    def _initialize_bot(self):
        """初始化答题机器人"""
        def init_thread():
            try:
                self.root.after(0, lambda: self.status_var.set("正在初始化..."))
                ocr_engine = self.ocr_var.get()
                self.bot = AutoAnswerBot(ocr_engine=ocr_engine)
                self.root.after(0, lambda: self.log_message(f"✓ 初始化成功 (OCR: {ocr_engine})", 'success'))
                self.root.after(0, lambda: self.status_var.set("已就绪"))
                self.root.after(0, lambda: self.start_auto_btn.config(state=tk.NORMAL if self.continuous_var.get() else tk.DISABLED))
            except Exception as e:
                self.root.after(0, lambda: self.log_message(f"✗ 初始化失败：{str(e)}", 'error'))
                self.root.after(0, lambda: self.status_var.set("初始化失败"))
                self.root.after(0, lambda: messagebox.showerror("错误", f"初始化失败:\n{str(e)}"))
        
        thread = threading.Thread(target=init_thread, daemon=True)
        thread.start()
    
    def _get_region(self) -> Optional[tuple]:
        """获取截图区域"""
        if not self.region_var.get():
            return None
        
        try:
            values = []
            for _, var, _ in self.region_inputs:
                values.append(int(var.get()))
            if all(v >= 0 for v in values):
                return tuple(values)
        except ValueError:
            pass
        return None
    
    def _capture_screen(self):
        """截取屏幕"""
        if not self.bot:
            messagebox.showwarning("警告", "请先初始化答题机器人")
            return
        
        try:
            region = self._get_region()
            screenshot_path = self.bot.image_capture.capture_screen(region=region)
            self.log_message(f"✓ 截图已保存：{screenshot_path}", 'success')
            
            # 显示截图预览
            self._show_image_preview(screenshot_path)
        except Exception as e:
            self.log_message(f"✗ 截图失败：{str(e)}", 'error')
            messagebox.showerror("错误", f"截图失败:\n{str(e)}")
    
    def _show_image_preview(self, image_path: str):
        """显示图片预览"""
        try:
            img = Image.open(image_path)
            img.thumbnail((300, 200))
            photo = ImageTk.PhotoImage(img)
            
            preview_window = tk.Toplevel(self.root)
            preview_window.title("截图预览")
            preview_window.geometry("400x300")
            
            label = ttk.Label(preview_window, image=photo)
            label.image = photo
            label.pack(expand=True)
            
            ttk.Button(preview_window, text="关闭", command=preview_window.destroy).pack(pady=10)
        except Exception as e:
            self.log_message(f"预览失败：{str(e)}", 'warning')
    
    def _answer_question(self):
        """识别并答题"""
        if not self.bot:
            messagebox.showwarning("警告", "请先初始化答题机器人")
            return
        
        if self.is_processing:
            return
        
        self.is_processing = True
        self.status_var.set("正在识别...")
        
        def process_thread():
            try:
                region = self._get_region()
                manual_answer = self.manual_answer_var.get().strip() or None
                auto_click = self.auto_click_var.get()
                
                question, answer = self.bot.answer_from_screen(
                    region=region,
                    auto_click=auto_click,
                    answer_label=manual_answer
                )
                
                # 更新 UI
                self.root.after(0, lambda: self._update_display(question, answer))
                
                if answer:
                    self.root.after(0, lambda: self.log_message(f"✓ 找到答案：{answer}", 'success'))
                else:
                    self.root.after(0, lambda: self.log_message("✗ 未找到答案", 'warning'))
                    
            except Exception as e:
                self.root.after(0, lambda: self.log_message(f"✗ 识别失败：{str(e)}", 'error'))
                self.root.after(0, lambda: messagebox.showerror("错误", f"识别失败:\n{str(e)}"))
            finally:
                self.root.after(0, lambda: setattr(self, 'is_processing', False))
                self.root.after(0, lambda: self.status_var.set("就绪"))
        
        thread = threading.Thread(target=process_thread, daemon=True)
        thread.start()
    
    def _update_display(self, question: Question, answer: Optional[str]):
        """更新显示区域"""
        self.question_text.delete(1.0, tk.END)
        self.question_text.insert(tk.END, question.question_text)
        
        type_map = {
            QuestionType.SINGLE_CHOICE: "单选题",
            QuestionType.MULTIPLE_CHOICE: "多选题",
            QuestionType.TRUE_FALSE: "判断题",
            QuestionType.FILL_BLANK: "填空题",
            QuestionType.UNKNOWN: "未知类型"
        }
        self.type_var.set(type_map.get(question.question_type, "未知"))
        
        self.options_text.delete(1.0, tk.END)
        if question.options:
            for i, opt in enumerate(question.options):
                self.options_text.insert(tk.END, f"{chr(65+i)}. {opt}\n")
        else:
            self.options_text.insert(tk.END, "无选项")
        
        self.answer_var.set(answer if answer else "未找到答案")
    
    def _load_image(self):
        """从图片文件答题"""
        if not self.bot:
            messagebox.showwarning("警告", "请先初始化答题机器人")
            return
        
        file_path = filedialog.askopenfilename(
            title="选择图片文件",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif"), ("所有文件", "*.*")]
        )
        
        if file_path:
            self._answer_from_image_file(file_path)
    
    def _answer_from_image_file(self, image_path: str):
        """从图片文件答题"""
        if self.is_processing:
            return
        
        self.is_processing = True
        self.status_var.set("正在识别图片...")
        
        def process_thread():
            try:
                manual_answer = self.manual_answer_var.get().strip() or None
                question, answer = self.bot.answer_from_image(
                    image_path=image_path,
                    answer_label=manual_answer
                )
                
                self.root.after(0, lambda: self._update_display(question, answer))
                
                if answer:
                    self.root.after(0, lambda: self.log_message(f"✓ 找到答案：{answer}", 'success'))
                else:
                    self.root.after(0, lambda: self.log_message("✗ 未找到答案", 'warning'))
                    
            except Exception as e:
                self.root.after(0, lambda: self.log_message(f"✗ 识别失败：{str(e)}", 'error'))
                self.root.after(0, lambda: messagebox.showerror("错误", f"识别失败:\n{str(e)}"))
            finally:
                self.root.after(0, lambda: setattr(self, 'is_processing', False))
                self.root.after(0, lambda: self.status_var.set("就绪"))
        
        thread = threading.Thread(target=process_thread, daemon=True)
        thread.start()
    
    def _add_answer(self):
        """添加答案"""
        if not self.bot:
            messagebox.showwarning("警告", "请先初始化答题机器人")
            return
        
        add_window = tk.Toplevel(self.root)
        add_window.title("添加答案")
        add_window.geometry("500x300")
        add_window.transient(self.root)
        
        ttk.Label(add_window, text="题目内容:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, padx=20, pady=(20, 5))
        question_text = scrolledtext.ScrolledText(add_window, height=6, wrap=tk.WORD)
        question_text.pack(fill=tk.X, padx=20, pady=5)
        
        # 预填充当前题目
        if self.bot.last_question:
            question_text.insert(tk.END, self.bot.last_question.question_text)
        
        ttk.Label(add_window, text="答案:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, padx=20, pady=(10, 5))
        answer_entry = ttk.Entry(add_window, width=50)
        answer_entry.pack(padx=20, pady=5)
        
        # 预填充当前答案
        if self.bot.last_answer:
            answer_entry.insert(0, self.bot.last_answer)
        
        def save_answer():
            q_text = question_text.get(1.0, tk.END).strip()
            a_text = answer_entry.get().strip()
            
            if not q_text or not a_text:
                messagebox.showwarning("警告", "题目和答案不能为空")
                return
            
            self.bot.answer_matcher.add_answer(q_text, a_text)
            self.log_message(f"✓ 已添加答案：{q_text[:30]}...", 'success')
            add_window.destroy()
        
        btn_frame = ttk.Frame(add_window)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="保存", command=save_answer).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=add_window.destroy).pack(side=tk.LEFT, padx=10)
    
    def _toggle_auto_mode(self):
        """切换自动模式"""
        if self.auto_mode:
            self.auto_mode = False
            self.start_auto_btn.config(text="▶️ 开始自动")
            self.log_message("⏹️ 自动模式已停止", 'warning')
        else:
            self.auto_mode = True
            self.start_auto_btn.config(text="⏹️ 停止自动")
            self.log_message("▶️ 自动模式已启动", 'info')
            self._start_auto_loop()
    
    def _start_auto_loop(self):
        """启动自动循环"""
        if not self.auto_mode:
            return
        
        def auto_thread_func():
            while self.auto_mode:
                try:
                    self._answer_question()
                    interval = float(self.interval_var.get())
                    time.sleep(interval)
                except Exception as e:
                    self.root.after(0, lambda: self.log_message(f"自动答题错误：{str(e)}", 'error'))
                    break
        
        if self.auto_thread and self.auto_thread.is_alive():
            return
        
        self.auto_thread = threading.Thread(target=auto_thread_func, daemon=True)
        self.auto_thread.start()
    
    def _clear_display(self):
        """清空显示"""
        self.question_text.delete(1.0, tk.END)
        self.options_text.delete(1.0, tk.END)
        self.type_var.set("未识别")
        self.answer_var.set("等待识别...")
    
    def _save_database(self):
        """保存答案数据库"""
        if not self.bot:
            messagebox.showwarning("警告", "请先初始化答题机器人")
            return
        
        try:
            self.bot.answer_matcher._save_answer_database()
            self.log_message("✓ 答案数据库已保存", 'success')
            messagebox.showinfo("成功", "答案数据库已保存")
        except Exception as e:
            self.log_message(f"✗ 保存失败：{str(e)}", 'error')
            messagebox.showerror("错误", f"保存失败:\n{str(e)}")
    
    def _import_answer_database(self):
        """导入答题库"""
        filetypes = [
            ("文本文件", "*.txt"),
            ("JSON 文件", "*.json"),
            ("所有文件", "*.*")
        ]
        
        filepath = filedialog.askopenfilename(
            title="选择要导入的答题库文件",
            filetypes=filetypes
        )
        
        if not filepath:
            return
        
        if not self.bot:
            messagebox.showwarning("警告", "请先初始化答题机器人")
            return
        
        try:
            imported_count = 0
            duplicated_count = 0
            
            if filepath.endswith('.json'):
                import json
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for question, answer in data.items():
                            if question not in self.bot.answer_matcher.answer_database:
                                self.bot.answer_matcher.answer_database[question] = str(answer)
                                imported_count += 1
                            else:
                                duplicated_count += 1
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and 'question' in item and 'answer' in item:
                                q = item['question']
                                a = item['answer']
                                if q not in self.bot.answer_matcher.answer_database:
                                    self.bot.answer_matcher.answer_database[q] = str(a)
                                    imported_count += 1
                                else:
                                    duplicated_count += 1
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and ':' in line:
                            parts = line.split(':', 1)
                            if len(parts) == 2:
                                question = parts[0].strip()
                                answer = parts[1].strip()
                                if question not in self.bot.answer_matcher.answer_database:
                                    self.bot.answer_matcher.answer_database[question] = answer
                                    imported_count += 1
                                else:
                                    duplicated_count += 1
            
            self.bot.answer_matcher._save_answer_database()
            
            msg = f"✓ 成功导入 {imported_count} 条答案"
            if duplicated_count > 0:
                msg += f"\n跳过 {duplicated_count} 条重复题目"
            
            self.log_message(msg, 'success')
            messagebox.showinfo("导入完成", msg)
            
        except Exception as e:
            self.log_message(f"✗ 导入失败：{str(e)}", 'error')
            messagebox.showerror("错误", f"导入失败:\n{str(e)}")
    
    def _show_ocr_settings(self):
        """显示 OCR 设置"""
        messagebox.showinfo("OCR 设置", 
                           "支持的 OCR 引擎:\n\n"
                           "• PaddleOCR - 百度开源，中文识别效果好\n"
                           "• Tesseract - Google 开源，需要安装 tesseract-ocr\n"
                           "• EasyOCR - 支持多语言，易于使用\n\n"
                           "首次使用需要下载模型文件，请耐心等待。")
    
    def _show_database_manager(self):
        """显示数据库管理器"""
        if not self.bot:
            messagebox.showwarning("警告", "请先初始化答题机器人")
            return
        
        db_window = tk.Toplevel(self.root)
        db_window.title("答案数据库管理")
        db_window.geometry("600x400")
        
        # 数据库列表
        list_frame = ttk.LabelFrame(db_window, text="答案列表", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        listbox = tk.Listbox(list_frame, height=15)
        scrollbar = ttk.Scrollbar(listbox, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 填充数据
        for q, a in self.bot.answer_matcher.answer_database.items():
            listbox.insert(tk.END, f"{q[:50]}... => {a}")
        
        # 删除按钮
        def delete_selected():
            selection = listbox.curselection()
            if selection:
                index = selection[0]
                items = list(self.bot.answer_matcher.answer_database.items())
                if index < len(items):
                    q, _ = items[index]
                    del self.bot.answer_matcher.answer_database[q]
                    listbox.delete(index)
                    self.bot.answer_matcher._save_answer_database()
                    self.log_message(f"✓ 已删除答案", 'success')
        
        btn_frame = ttk.Frame(db_window)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="删除选中", command=delete_selected).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="刷新", command=lambda: self._show_database_manager()).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="关闭", command=db_window.destroy).pack(side=tk.LEFT, padx=10)
    
    def _show_help(self):
        """显示帮助"""
        help_text = """
📖 智能答题助手使用指南

1. 初始化
   - 选择 OCR 引擎（推荐 PaddleOCR）
   - 点击【初始化】按钮

2. 答题流程
   - 确保答题界面在屏幕上可见
   - 点击【截取屏幕】预览截图
   - 点击【识别并答题】自动识别并点击答案

3. 自动模式
   - 勾选【连续答题模式】
   - 设置答题间隔时间
   - 点击【开始自动】启动自动答题

4. 答案管理
   - 系统会自动匹配答案数据库
   - 可手动添加新答案
   - 支持模糊匹配
   - 通过菜单【文件】→【导入答题库】批量导入答案

5. 导入答题库
   - 支持 TXT 格式：每行"题目：答案"
   - 支持 JSON 格式：对象或数组格式
   - 自动跳过重复题目

6. 注意事项
   - 首次使用需要下载 OCR 模型
   - 确保屏幕分辨率适中
   - 答题界面应清晰可见
        """
        
        help_window = tk.Toplevel(self.root)
        help_window.title("使用帮助")
        help_window.geometry("500x450")
        
        text = scrolledtext.ScrolledText(help_window, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(tk.END, help_text)
        text.config(state=tk.DISABLED)
    
    def _show_about(self):
        """显示关于"""
        messagebox.showinfo("关于",
                           "🤖 智能答题助手\n\n"
                           "版本：2.0 (GUI 版)\n"
                           "功能：图像识别、自动答题、答案管理\n\n"
                           "支持 OCR 引擎:\n"
                           "• PaddleOCR\n"
                           "• Tesseract\n"
                           "• EasyOCR\n\n"
                           "© 2024 All Rights Reserved")
    
    def log_message(self, message: str, level: str = 'info'):
        """记录日志"""
        self.log_text.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", level)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)


def main():
    """主函数"""
    root = tk.Tk()
    
    # 设置图标（如果有的话）
    try:
        root.iconbitmap('icon.ico')
    except:
        pass
    
    app = AnswerBotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
