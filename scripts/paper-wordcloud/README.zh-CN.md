# Paper WordCloud / 科学文献词云生成器

一个简单、快速的工具，用于从ArXiv科学论文生成美观的遮罩词云图。

<p align="center">
  <img src="examples/gallery.jpg" alt="实体词云艺术作品" width="600"/>
  <br>
  <em>词云变身桌面艺术摆件 - 从代码到现实！</em>
</p>

## 特性

- **简单易用**：单文件实现，依赖最少
- **快速高效**：直接从ArXiv下载PDF并提取文本
- **灵活输入**：支持ArXiv论文ID或本地PDF目录
- **美观输出**：自定义遮罩形状，专业字体排版
- **学术优化**：针对科学文献的智能停用词过滤

## 快速开始

### 安装

```bash
git clone https://github.com/YinkaiYu/paper-wordcloud.git
cd paper-wordcloud
pip install -r requirements.txt
```

### 基本用法

#### 从ArXiv论文ID生成
```bash
# 创建包含ArXiv ID的文本文件（每行一个ID）
echo -e "2211.02002\n2302.10115\n2409.18050" > my_papers.txt

# 生成词云
python arxiv_wordcloud.py --ids my_papers.txt --mask examples/mask.jpg --output my_wordcloud.png
```

#### 从本地PDF生成
```bash
# 如果你有PDF文件目录
python arxiv_wordcloud.py --pdfs ./pdf_directory/ --mask examples/mask.jpg --output my_wordcloud.png
```

#### 使用自定义字体
```bash
python arxiv_wordcloud.py --ids my_papers.txt --mask examples/mask.jpg --output result.png --font fonts/HardingTextRegular.ttf
```

#### 使用主题词（突出重点术语）
```bash
# 创建主题词文件，包含你想突出显示的关键术语
echo -e "QUANTUM MONTE CARLO\nSUPERCONDUCTIVITY\nDIRAC FERMIONS" > my_themes.txt

# 生成带有突出主题词的词云
python arxiv_wordcloud.py --ids my_papers.txt --mask examples/mask.jpg --output result.png --theme-words my_themes.txt
```

### Python API

```python
import arxiv_wordcloud

# 简单调用
success = arxiv_wordcloud.create_wordcloud_from_arxiv(
    arxiv_ids=['2211.02002', '2302.10115', '2409.18050'],
    mask_image='examples/mask.jpg',
    output_file='my_wordcloud.png'
)

# 使用主题词强调
success = arxiv_wordcloud.create_wordcloud_from_arxiv(
    arxiv_ids=['2211.02002', '2302.10115', '2409.18050'],
    mask_image='examples/mask.jpg',
    output_file='my_wordcloud.png',
    theme_words_file='examples/theme_words.txt',
    font_path='fonts/HardingTextRegular.ttf'
)
```

## 命令行选项

```
python arxiv_wordcloud.py --help

必需参数:
  --ids FILE          包含ArXiv ID的文本文件（每行一个ID）
  --pdfs DIRECTORY    包含PDF文件的目录
  --mask IMAGE        遮罩图片文件路径
  --output IMAGE      输出词云图片路径

可选参数:
  --font FONT           自定义字体文件路径
  --theme-words FILE    主题词文件（按优先级排序，每行一个）
  --max-words N         最大词汇数量（默认：500）
```

## 工作原理

1. **下载**：使用论文ID从ArXiv获取PDF文件
2. **提取**：将PDF内容转换为纯文本
3. **处理**：计算词频并进行智能过滤
4. **生成**：创建高质量的遮罩词云图

## 文件结构

```
paper-wordcloud/
├── arxiv_wordcloud.py      # 主程序（单文件解决方案！）
├── requirements.txt        # Python依赖
├── fonts/
│   └── HardingTextRegular.ttf  # 专业字体
└── examples/
    ├── arxiv_ids.txt       # 示例论文ID
    ├── theme_words.txt     # 示例主题词
    ├── mask.jpg            # 示例遮罩图片
    └── demo.py             # 演示脚本
```

## 创建自定义遮罩

遮罩图片决定词云的形状：

- **白色区域**（255）= 不放置词汇
- **深色区域**（0-127）= 在此处放置词汇
- **格式**：任何图片格式（PNG、JPG等）
- **提示**：使用高对比度剪影效果最佳

## 系统依赖

最小化且专注：
- `PyMuPDF` - PDF文本提取
- `requests` - ArXiv下载
- `wordcloud` - 词云生成
- `matplotlib` - 图像保存
- `Pillow` - 图像处理
- `numpy` - 数组操作

## 安装镜像源（中国用户）

```bash
# 使用清华镜像源加速安装
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

## 示例

### 快速演示
```bash
cd examples/
python demo.py
```

### 适用领域
适合以下类型的论文：
- 物理学论文（量子、凝聚态物理等）
- 计算机科学论文
- 数学论文
- 任何ArXiv内容

### 高级参数调优

自定义词云外观，可以调整 `create_masked_wordcloud()` 的参数：

```python
from arxiv_wordcloud import create_masked_wordcloud, get_word_frequencies

# 从你自己的文本获取词频
word_freq = get_word_frequencies(["你的文本内容"])

# 创建高度自定义的词云
create_masked_wordcloud(
    word_freq=word_freq,
    mask_path="你的遮罩.png", 
    output_path="自定义词云.png",
    font_path="fonts/你的字体.ttf",
    max_words=1000,              # 更多词汇 = 更密集的词云
    background_color='black'     # 'black', 'white', 或自定义颜色
)
```

#### 关键参数说明

**分辨率和质量：**
- **4倍放大**：图像以4倍分辨率渲染，确保清晰输出
- **800 DPI**：适合高质量印刷/显示
- **LANCZOS重采样**：专业级图像缩放

**文字布局：**
- `max_words=500`：最大词汇数（推荐50-2000）
- `relative_scaling=0.3`：词频重要性权重（0.1-1.0）
- `prefer_horizontal=0.7`：水平vs垂直文字比例（0.0-1.0）
- `min_font_size=12`：最小可读字号（高分辨率推荐8-20）
- `max_font_size=400`：最大字号（高分辨率推荐100-800）

**外观样式：**
- `margin=5`：词汇间距（0-20）
- `font_step=1`：精细字体大小控制（1-5）
- `background_color='black'`：背景色
- `collocations=False`：防止词语配对（始终推荐）

**快速配方：**

```python
# 密集学术海报风格
create_masked_wordcloud(..., max_words=800, relative_scaling=0.2, prefer_horizontal=0.8)

# 简洁演示风格
create_masked_wordcloud(..., max_words=300, relative_scaling=0.4, margin=10)

# 艺术风格
create_masked_wordcloud(..., max_words=1000, prefer_horizontal=0.5, background_color='white')
```

## 故障排除

**PDF下载失败**：检查网络连接和ArXiv ID格式
**输出无词汇**：尝试降低`min_word_length`或检查PDF是否包含文本
**字体错误**：字体路径问题 - 使用默认字体或检查路径
**内存问题**：为大型数据集减少`max_words`参数

## 贡献指南

本项目设计简洁且专注。欢迎以下类型的贡献：
- Bug修复
- 性能改进
- 更好的停用词列表
- 文档改进

保持简单 - 这应该始终是一个单文件工具。

## 许可证

MIT许可证 - 可自由用于学术或商业项目。

## 引用

如果在学术工作中使用此工具，请引用：

```bibtex
@software{paper_wordcloud,
  title={Paper WordCloud Generator},
  author={Yin-Kai Yu},
  year={2025},
  url={https://github.com/YinkaiYu/paper-wordcloud}
}
```

---

[English](README.md) | **简体中文**