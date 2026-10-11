# Paper WordCloud Generator

A simple, fast tool to generate beautiful masked word clouds from scientific papers.

<p align="center">
  <img src="examples/gallery.jpg" alt="Physical WordCloud Art Piece" width="600"/>
  <br>
  <em>WordCloud turned into a framed desktop art piece - from code to reality!</em>
</p>

## Features

- **Simple**: Single Python file, minimal dependencies
- **Fast**: Direct ArXiv PDF download and text extraction  
- **Flexible**: Support ArXiv IDs or local PDF directories
- **Beautiful**: Custom mask shapes with professional typography
- **Academic**: Smart stopword filtering for scientific content

## Quick Start

### Installation

```bash
git clone https://github.com/YinkaiYu/paper-wordcloud.git
cd paper-wordcloud
pip install -r requirements.txt
```

### Basic Usage

#### From ArXiv IDs
```bash
# Create a text file with ArXiv IDs (one per line)
echo -e "2211.02002\n2302.10115\n2409.18050" > my_papers.txt

# Generate wordcloud
python arxiv_wordcloud.py --ids my_papers.txt --mask examples/mask.jpg --output my_wordcloud.png
```

#### From Local PDFs
```bash
# If you have PDFs in a directory
python arxiv_wordcloud.py --pdfs ./pdf_directory/ --mask examples/mask.jpg --output my_wordcloud.png
```

#### With Custom Font
```bash
python arxiv_wordcloud.py --ids my_papers.txt --mask examples/mask.jpg --output result.png --font fonts/HardingTextRegular.ttf
```

#### With Theme Words (Highlighted Terms)
```bash
# Create theme words file with your key terms
echo -e "QUANTUM MONTE CARLO\nSUPERCONDUCTIVITY\nDIRAC FERMIONS" > my_themes.txt

# Generate wordcloud with boosted theme words
python arxiv_wordcloud.py --ids my_papers.txt --mask examples/mask.jpg --output result.png --theme-words my_themes.txt
```

### Python API

```python
import arxiv_wordcloud

# Simple function call
success = arxiv_wordcloud.create_wordcloud_from_arxiv(
    arxiv_ids=['2211.02002', '2302.10115', '2409.18050'],
    mask_image='examples/mask.jpg',
    output_file='my_wordcloud.png'
)

# With theme words for emphasis
success = arxiv_wordcloud.create_wordcloud_from_arxiv(
    arxiv_ids=['2211.02002', '2302.10115', '2409.18050'],
    mask_image='examples/mask.jpg',
    output_file='my_wordcloud.png',
    theme_words_file='examples/theme_words.txt',
    font_path='fonts/HardingTextRegular.ttf'
)
```

## Command Line Options

```
python arxiv_wordcloud.py --help

Required:
  --ids FILE          Text file with ArXiv IDs (one per line)
  --pdfs DIRECTORY    Directory containing PDF files
  --mask IMAGE        Path to mask image file
  --output IMAGE      Output wordcloud image path

Optional:
  --font FONT           Path to custom font file
  --theme-words FILE    Text file with theme words (highest priority first)
  --max-words N         Maximum number of words (default: 500)
```

## How It Works

1. **Download**: Fetch PDFs from ArXiv using paper IDs
2. **Extract**: Convert PDF content to plain text
3. **Process**: Calculate word frequencies with smart filtering
4. **Generate**: Create masked wordcloud with custom styling

## File Structure

```
paper-wordcloud/
├── arxiv_wordcloud.py      # Main program (single file!)
├── requirements.txt        # Python dependencies
├── fonts/
│   └── HardingTextRegular.ttf  # Professional font
└── examples/
    ├── arxiv_ids.txt       # Example paper IDs
    ├── mask.jpg            # Example mask image
    ├── theme_words.txt     # Example theme words
    └── demo.py             # Demo script
```

## Creating Your Own Masks

The mask image determines the shape of your wordcloud:

- **White areas** (255) = no words placed
- **Dark areas** (0-127) = words will be placed here
- **Format**: Any image format (PNG, JPG, etc.)
- **Tip**: Use high contrast silhouettes for best results

## Dependencies

Minimal and focused:
- `PyMuPDF` - PDF text extraction
- `requests` - ArXiv downloads  
- `wordcloud` - Word cloud generation
- `matplotlib` - Image saving
- `Pillow` - Image processing
- `numpy` - Array operations

## Examples

### Quick Demo
```bash
cd examples/
python demo.py
```

### Academic Papers
Works great with:
- Physics papers (quantum, condensed matter, etc.)
- Computer science papers 
- Mathematics papers
- Any ArXiv content

### Advanced Parameter Tuning

For custom WordCloud appearance, you can modify parameters in `create_masked_wordcloud()`:

```python
from arxiv_wordcloud import create_masked_wordcloud, get_word_frequencies

# Get frequencies from your own text
word_freq = get_word_frequencies(["your text here"])

# Create highly customized wordcloud
create_masked_wordcloud(
    word_freq=word_freq,
    mask_path="your_mask.png", 
    output_path="custom_cloud.png",
    font_path="fonts/YourFont.ttf",
    max_words=1000,              # More words = denser cloud
    background_color='black'     # 'black', 'white', or custom color
)
```

#### Key Parameters to Adjust

**Resolution & Quality:**
- **4x upscaling**: Images are rendered at 4x resolution for crisp output
- **800 DPI**: High-quality printing/display ready
- **LANCZOS resampling**: Professional image scaling

**Text Layout:**
- `max_words=500`: Maximum number of words (50-2000 recommended)
- `relative_scaling=0.3`: How much importance to give to frequency (0.1-1.0)
- `prefer_horizontal=0.7`: Ratio of horizontal vs vertical text (0.0-1.0)
- `min_font_size=12`: Smallest readable text (8-20 for high-res)
- `max_font_size=400`: Largest text size (100-800 for high-res)

**Appearance:**
- `margin=5`: Space between words (0-20)
- `font_step=1`: Fine-grained font size control (1-5)
- `background_color='black'`: Background color
- `collocations=False`: Prevent word pairs (always recommended)

**Quick Recipes:**

```python
# Dense academic poster style
create_masked_wordcloud(..., max_words=800, relative_scaling=0.2, prefer_horizontal=0.8)

# Clean presentation style  
create_masked_wordcloud(..., max_words=300, relative_scaling=0.4, margin=10)

# Artistic style
create_masked_wordcloud(..., max_words=1000, prefer_horizontal=0.5, background_color='white')
```

## Troubleshooting

**PDF download fails**: Check internet connection and ArXiv ID format
**No words in output**: Try reducing `min_word_length` or check if PDFs contain text
**Font errors**: Font path issue - use default font or check path
**Memory issues**: Reduce `max_words` parameter for large datasets

## Contributing

This is designed to be simple and focused. Contributions welcome for:
- Bug fixes
- Performance improvements  
- Better stopword lists
- Documentation improvements

Keep it simple - this should remain a single-file tool.

## License

MIT License - feel free to use for academic or commercial projects.

## Citation

If you use this tool in academic work, please cite:

```bibtex
@software{paper_wordcloud,
  title={Paper WordCloud Generator},
  author={Yin-Kai Yu},
  year={2025},
  url={https://github.com/YinkaiYu/paper-wordcloud}
}
```

---

**English** | [简体中文](README.zh-CN.md)