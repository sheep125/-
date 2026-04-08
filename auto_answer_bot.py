#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于图像识别的自动答题脚本
支持屏幕截图、OCR识别、题目解析和答案匹配
"""

import os
import re
import time
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum


class QuestionType(Enum):
    """题目类型枚举"""
    SINGLE_CHOICE = "single_choice"  # 单选题
    MULTIPLE_CHOICE = "multiple_choice"  # 多选题
    TRUE_FALSE = "true_false"  # 判断题
    FILL_BLANK = "fill_blank"  # 填空题
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
        """
        截取屏幕图像
        
        Args:
            region: 截取区域 (left, top, width, height)，None表示全屏
            save_path: 保存路径
            
        Returns:
            保存的文件路径
        """
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab(bbox=region)
            screenshot.save(save_path)
            print(f"截图已保存至: {save_path}")
            return save_path
        except ImportError:
            print("错误: 请安装 Pillow 库 (pip install Pillow)")
            raise
        except Exception as e:
            print(f"截图失败: {e}")
            raise


class OCRRecognizer:
    """OCR文字识别模块"""
    
    def __init__(self, engine: str = "paddleocr"):
        """
        初始化OCR识别器
        
        Args:
            engine: OCR引擎，支持 'paddleocr', 'tesseract', 'easyocr'
        """
        self.engine = engine
        self._init_engine()
    
    def _init_engine(self):
        """初始化选定的OCR引擎"""
        if self.engine == "paddleocr":
            try:
                from paddleocr import PaddleOCR
                self.ocr = PaddleOCR(use_angle_cls=True, lang="ch")
                print("PaddleOCR 初始化成功")
            except ImportError:
                print("警告: PaddleOCR 未安装，尝试使用 Tesseract")
                self.engine = "tesseract"
                self._init_engine()
        
        elif self.engine == "tesseract":
            try:
                import pytesseract
                self.ocr = pytesseract
                print("Tesseract OCR 初始化成功")
            except ImportError:
                print("错误: 请安装 pytesseract (pip install pytesseract)")
                raise
        
        elif self.engine == "easyocr":
            try:
                import easyocr
                self.ocr = easyocr.Reader(['ch_sim', 'en'])
                print("EasyOCR 初始化成功")
            except ImportError:
                print("错误: 请安装 easyocr (pip install easyocr)")
                raise
    
    def recognize(self, image_path: str) -> List[Dict]:
        """
        识别图像中的文字
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            识别结果列表，每项包含文字内容和位置信息
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图像文件不存在: {image_path}")
        
        if self.engine == "paddleocr":
            result = self.ocr.ocr(image_path, cls=True)
            # 整理PaddleOCR的输出格式
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
            from PIL import Image
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
        """
        从OCR结果中解析题目
        
        Args:
            ocr_results: OCR识别结果列表
            
        Returns:
            Question对象
        """
        # 合并所有识别的文字
        full_text = "\n".join([item['text'] for item in ocr_results if item.get('text')])
        
        # 提取题目正文（通常在选项之前）
        question_text = self._extract_question_text(full_text)
        
        # 提取选项
        options = self._extract_options(full_text)
        
        # 判断题目类型
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
            # 如果遇到选项标识，停止提取
            if re.match(r'^[A-D]\.|^[A-D]、|^(\d+)\.', line):
                break
            question_lines.append(line)
        
        return ' '.join(question_lines)
    
    def _extract_options(self, text: str) -> List[str]:
        """提取选项"""
        options = []
        # 匹配常见选项格式：A. xxx 或 A、xxx
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
        """
        初始化答案匹配器
        
        Args:
            answer_db_path: 答案数据库文件路径
        """
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
                            question_key = parts[0].strip()
                            answer = parts[1].strip()
                            database[question_key] = answer
        return database
    
    def find_answer(self, question: Question) -> Optional[str]:
        """
        查找题目答案
        
        Args:
            question: Question对象
            
        Returns:
            答案，如果未找到则返回None
        """
        # 精确匹配
        if question.question_text in self.answer_database:
            return self.answer_database[question.question_text]
        
        # 模糊匹配（关键词匹配）
        keywords = self._extract_keywords(question.question_text)
        for db_question, answer in self.answer_database.items():
            if any(kw in db_question for kw in keywords if len(kw) > 2):
                return answer
        
        return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 去除常见停用词
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


class AutoAnswerBot:
    """自动答题机器人主类"""
    
    def __init__(self, ocr_engine: str = "paddleocr", answer_db: str = "answer_database.txt"):
        """
        初始化答题机器人
        
        Args:
            ocr_engine: OCR引擎类型
            answer_db: 答案数据库路径
        """
        self.image_capture = ImageCapture()
        self.ocr_recognizer = OCRRecognizer(engine=ocr_engine)
        self.question_parser = QuestionParser()
        self.answer_matcher = AnswerMatcher(answer_db_path=answer_db)
    
    def answer_from_screen(self, region: Optional[tuple] = None, auto_click: bool = False) -> Optional[str]:
        """
        从屏幕截图自动答题
        
        Args:
            region: 截图区域
            auto_click: 是否自动点击答案
            
        Returns:
            找到的答案
        """
        print("\n=== 开始答题 ===")
        
        # 1. 截取屏幕
        screenshot_path = self.image_capture.capture_screen(region=region)
        
        # 2. OCR识别
        print("正在进行文字识别...")
        ocr_results = self.ocr_recognizer.recognize(screenshot_path)
        
        # 打印识别结果
        print("\n识别到的文字:")
        for item in ocr_results:
            print(f"  - {item['text']} (置信度: {item.get('confidence', 'N/A')})")
        
        # 3. 解析题目
        print("\n解析题目...")
        question = self.question_parser.parse(ocr_results)
        print(f"题目类型: {question.question_type.value}")
        print(f"题目内容: {question.question_text}")
        if question.options:
            print("选项:")
            for i, opt in enumerate(question.options):
                print(f"  {chr(65+i)}. {opt}")
        
        # 4. 查找答案
        print("\n查找答案...")
        answer = self.answer_matcher.find_answer(question)
        
        if answer:
            print(f"✓ 找到答案: {answer}")
            if auto_click:
                self._click_answer(answer, question.options)
        else:
            print("✗ 未找到答案")
        
        return answer
    
    def answer_from_image(self, image_path: str, auto_click: bool = False) -> Optional[str]:
        """
        从图像文件自动答题
        
        Args:
            image_path: 图像文件路径
            auto_click: 是否自动点击答案
            
        Returns:
            找到的答案
        """
        print("\n=== 开始答题 ===")
        
        # 1. OCR识别
        print("正在进行文字识别...")
        ocr_results = self.ocr_recognizer.recognize(image_path)
        
        # 打印识别结果
        print("\n识别到的文字:")
        for item in ocr_results:
            print(f"  - {item['text']} (置信度: {item.get('confidence', 'N/A')})")
        
        # 2. 解析题目
        print("\n解析题目...")
        question = self.question_parser.parse(ocr_results)
        print(f"题目类型: {question.question_type.value}")
        print(f"题目内容: {question.question_text}")
        if question.options:
            print("选项:")
            for i, opt in enumerate(question.options):
                print(f"  {chr(65+i)}. {opt}")
        
        # 3. 查找答案
        print("\n查找答案...")
        answer = self.answer_matcher.find_answer(question)
        
        if answer:
            print(f"✓ 找到答案: {answer}")
            if auto_click:
                self._click_answer(answer, question.options)
        else:
            print("✗ 未找到答案")
        
        return answer
    
    def _click_answer(self, answer: str, options: List[str]):
        """模拟点击答案（需要实现具体的点击逻辑）"""
        # 这里需要根据实际情况实现鼠标点击
        # 可以使用 pyautogui 库
        print(f"[待实现] 自动点击答案: {answer}")
        pass
    
    def interactive_mode(self):
        """交互模式"""
        print("\n=== 答题助手交互模式 ===")
        print("命令:")
        print("  screen - 截取屏幕并答题")
        print("  image <path> - 从图片文件答题")
        print("  add <question> <answer> - 添加答案")
        print("  quit - 退出")
        
        while True:
            cmd = input("\n请输入命令: ").strip()
            
            if cmd == "quit":
                print("再见!")
                break
            
            elif cmd == "screen":
                self.answer_from_screen()
            
            elif cmd.startswith("image "):
                image_path = cmd[6:].strip()
                if os.path.exists(image_path):
                    self.answer_from_image(image_path)
                else:
                    print(f"文件不存在: {image_path}")
            
            elif cmd.startswith("add "):
                parts = cmd[4:].rsplit(' ', 1)
                if len(parts) == 2:
                    self.answer_matcher.add_answer(parts[0], parts[1])
                    print("答案已添加")
                else:
                    print("格式错误，请使用: add <题目> <答案>")
            
            else:
                print("未知命令")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='基于图像识别的自动答题脚本')
    parser.add_argument('--ocr', choices=['paddleocr', 'tesseract', 'easyocr'], 
                       default='paddleocr', help='OCR引擎')
    parser.add_argument('--db', default='answer_database.txt', help='答案数据库路径')
    parser.add_argument('--image', help='图像文件路径')
    parser.add_argument('--interactive', action='store_true', help='交互模式')
    
    args = parser.parse_args()
    
    bot = AutoAnswerBot(ocr_engine=args.ocr, answer_db=args.db)
    
    if args.interactive:
        bot.interactive_mode()
    elif args.image:
        bot.answer_from_image(args.image)
    else:
        # 默认交互模式
        bot.interactive_mode()


if __name__ == "__main__":
    main()
