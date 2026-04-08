# 基于图像识别的自动答题脚本（增强版）

## 功能特点
- ✅ 屏幕截图捕获（支持全屏和指定区域）
- ✅ OCR 文字识别（支持 PaddleOCR/Tesseract/EasyOCR 三种引擎）
- ✅ 题目类型自动识别（单选/多选/判断/填空）
- ✅ 答案精确匹配和关键词模糊匹配
- ✅ **自动点击答案**（基于选项位置识别）
- ✅ 连续答题模式
- ✅ 交互式命令行界面

## 新增核心功能

### 1. 自动点击答案
脚本现在可以自动识别选项的位置坐标，并在找到答案后自动点击对应选项：
- 通过 OCR 识别结果获取每个选项的边界框坐标
- 计算选项中心点作为点击位置
- 支持根据答案文本或指定字母（A/B/C/D）进行点击

### 2. 连续答题模式
支持循环执行答题任务，适用于多题目连续场景：
```bash
python auto_answer_bot.py --continuous --interval 3
```

### 3. 指定区域截图
可以只截取屏幕特定区域进行识别，提高准确率和速度：
```bash
python auto_answer_bot.py --region 100 100 800 600
```

### 4. 手动指定答案
如果自动匹配失败，可以手动指定答案选项：
```bash
python auto_answer_bot.py --answer B
```

## 安装依赖
```bash
# 基础依赖
pip install Pillow pyautogui

# OCR 引擎（三选一或全部安装）
pip install paddlepaddle paddleocr  # 推荐：PaddleOCR（中文识别效果好）
# 或
pip install pytesseract tesseract  # Tesseract OCR
# 或
pip install easyocr  # EasyOCR
```

## 使用方法

### 快速开始（自动答题并点击）
```bash
# 直接运行，自动截图、识别、匹配答案并点击
python auto_answer_bot.py

# 指定 OCR 引擎
python auto_answer_bot.py --ocr paddleocr

# 指定截图区域 (left, top, width, height)
python auto_answer_bot.py --region 100 100 800 600

# 手动指定答案选项
python auto_answer_bot.py --answer B
```

### 交互模式
```bash
python auto_answer_bot.py --interactive
```

可用命令：
- `screen` - 截取全屏并自动答题点击
- `screen <left> <top> <width> <height>` - 指定区域截图答题
- `click A/B/C/D` - 手动指定答案选项并点击
- `image <path>` - 从图片文件答题
- `add <题目> <答案>` - 添加答案到数据库
- `continuous [间隔秒数]` - 连续答题模式
- `quit` - 退出

### 连续答题模式
```bash
# 每 2 秒自动答一题（默认间隔）
python auto_answer_bot.py --continuous

# 每 3 秒自动答一题，限定截图区域
python auto_answer_bot.py --continuous --interval 3 --region 100 100 800 600
```

### 从图片答题
```bash
python auto_answer_bot.py --image screenshot.png
```

## 答案数据库格式

在 `answer_database.txt` 中按以下格式添加答案：

```
题目内容：答案
另一道题目：B
判断题内容：正确
```

支持模糊匹配，系统会自动提取关键词进行匹配。

## 安全提示

⚠️ **故障保护机制**：脚本启用了 pyautogui 的故障保护功能，将鼠标移动到屏幕左上角可以紧急停止脚本。

⚠️ **使用建议**：
- 首次使用建议先在测试环境验证
- 确保截图区域准确包含题目和选项
- 答案数据库越完善，准确率越高

## 技术架构

```
AutoAnswerBot
├── ImageCapture      # 屏幕截图模块
├── OCRRecognizer     # OCR 文字识别（支持多种引擎）
├── QuestionParser    # 题目解析（提取题干、选项及位置）
├── AnswerMatcher     # 答案匹配（精确 + 模糊）
└── AutoClicker       # 自动点击模块（新增）
```

## 常见问题

**Q: 点击位置不准确？**
A: 确保截图区域与题目显示区域一致，检查 OCR 识别的选项位置是否正确。

**Q: 无法识别中文？**
A: 推荐使用 PaddleOCR，对中文支持最好。

**Q: 如何添加新题目答案？**
A: 使用交互模式的 `add` 命令，或直接编辑 `answer_database.txt` 文件。
