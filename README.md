# 基于图像识别的自动答题脚本

这是一个支持屏幕截图、OCR 文字识别、题目解析和答案匹配的自动答题工具。

## 功能特性

- 📸 **屏幕截图**: 支持全屏或指定区域截图
- 🔍 **OCR 识别**: 支持多种 OCR 引擎 (PaddleOCR, Tesseract, EasyOCR)
- 📝 **题目解析**: 自动识别题目类型（单选、多选、判断、填空）
- 💾 **答案匹配**: 支持精确匹配和关键词模糊匹配
- 🎮 **交互模式**: 命令行交互式操作

## 安装依赖

```bash
# 基础依赖
pip install Pillow

# 推荐使用 PaddleOCR（中文识别效果好）
pip install paddlepaddle paddleocr

# 或使用 Tesseract
pip install pytesseract
# 需要系统安装 tesseract-ocr

# 或使用 EasyOCR
pip install easyocr
```

## 使用方法

### 1. 交互模式（推荐）

```bash
python auto_answer_bot.py --interactive
```

支持的命令：
- `screen` - 截取当前屏幕并答题
- `image <路径>` - 从图片文件答题
- `add <题目> <答案>` - 添加答案到数据库
- `quit` - 退出程序

### 2. 直接处理图片

```bash
python auto_answer_bot.py --image screenshot.png
```

### 3. 指定 OCR 引擎

```bash
# 使用 PaddleOCR
python auto_answer_bot.py --ocr paddleocr --interactive

# 使用 Tesseract
python auto_answer_bot.py --ocr tesseract --interactive

# 使用 EasyOCR
python auto_answer_bot.py --ocr easyocr --interactive
```

### 4. 指定答案数据库

```bash
python auto_answer_bot.py --db my_answers.txt --interactive
```

## 答案数据库格式

答案数据库是简单的文本文件，每行格式为：

```
题目内容：答案
```

示例 (`answer_database.txt`):

```
中国的首都是哪里？: 北京
Python 是一种什么语言？: 编程语言
1+1 等于多少？: 2
```

## 代码结构

```
auto_answer_bot.py
├── ImageCapture      # 图像捕获模块
├── OCRRecognizer     # OCR 识别模块
├── QuestionParser    # 题目解析模块
├── AnswerMatcher     # 答案匹配模块
└── AutoAnswerBot     # 主控制类
```

## 扩展功能

### 添加自动点击功能

在 `_click_answer` 方法中集成 pyautogui：

```bash
pip install pyautogui
```

然后修改代码实现自动点击逻辑。

### 自定义题目解析规则

继承 `QuestionParser` 类并重写相关方法以适应特定格式的题目。

## 注意事项

1. 首次使用 PaddleOCR 会自动下载模型文件
2. 确保截图区域清晰，文字可辨识
3. 答案数据库需要手动积累和维护
4. 请合理使用，遵守相关平台规则

## License

MIT License
