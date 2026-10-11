# PDF Directory Example

This directory demonstrates how to use the `--pdfs` option to process local PDF files.

## Usage

1. Place your PDF files in this directory
2. Run the command:
   ```bash
   python ../../arxiv_wordcloud.py --pdfs examples/papers/ --mask examples/mask.jpg --output local_papers_wordcloud.png
   ```

## Example PDFs

You can download some example papers:

```bash
# Download some physics papers as examples
wget https://arxiv.org/pdf/2211.02002.pdf -O examples/papers/paper1.pdf
wget https://arxiv.org/pdf/2302.10115.pdf -O examples/papers/paper2.pdf
wget https://arxiv.org/pdf/2409.18050.pdf -O examples/papers/paper3.pdf
```

Then run:
```bash
python ../../arxiv_wordcloud.py --pdfs examples/papers/ --mask examples/mask.jpg --output papers_wordcloud.png --theme-words examples/theme_words.txt
```

**Note**: PDF files are not included in the repository to keep it lightweight. Users should provide their own PDFs or use the ArXiv ID method instead.