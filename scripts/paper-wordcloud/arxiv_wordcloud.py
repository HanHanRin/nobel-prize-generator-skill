#!/usr/bin/env python3
"""
ArXiv WordCloud Generator
A simple tool to generate masked word clouds from ArXiv papers

Usage:
    python arxiv_wordcloud.py --ids arxiv_ids.txt --mask mask.jpg --output result.png
    python arxiv_wordcloud.py --pdfs ./papers/ --mask mask.jpg --output result.png

Author: 
License: MIT
"""

import os
import sys
import argparse
import requests
import fitz  # PyMuPDF
import numpy as np
from PIL import Image
from wordcloud import WordCloud
from collections import Counter
import matplotlib.pyplot as plt
from typing import List, Dict, Union
from pathlib import Path


def download_arxiv_pdf(arxiv_id: str, output_dir: str = "papers") -> str:
    """Download PDF from ArXiv by ID
    
    Args:
        arxiv_id: ArXiv paper ID (e.g., "2211.02002")
        output_dir: Directory to save PDFs
        
    Returns:
        Path to downloaded PDF file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if file already exists
    pdf_path = os.path.join(output_dir, f"{arxiv_id}.pdf")
    if os.path.exists(pdf_path):
        print(f"✓ PDF already exists: {arxiv_id}")
        return pdf_path
    
    # Download from ArXiv
    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    print(f"📥 Downloading {arxiv_id}...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(pdf_path, 'wb') as f:
            f.write(response.content)
            
        print(f"✅ Downloaded: {arxiv_id} ({len(response.content)//1024}KB)")
        return pdf_path
        
    except Exception as e:
        print(f"❌ Failed to download {arxiv_id}: {e}")
        return None


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from PDF file
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Extracted text content
    """
    try:
        doc = fitz.open(pdf_path)
        text = ""
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text += page.get_text()
            
        doc.close()
        return text
        
    except Exception as e:
        print(f"❌ Failed to extract text from {pdf_path}: {e}")
        return ""


def get_word_frequencies(texts: List[str], min_word_length: int = 3, theme_words_file: str = None) -> Dict[str, int]:
    """Extract word frequencies from text list with stopword filtering
    
    Args:
        texts: List of text strings
        min_word_length: Minimum word length to include
        
    Returns:
        Dictionary of word frequencies
    """
    
    # Academic and common stopwords
    STOPWORDS = {
        # English common words
        'THE', 'AND', 'OR', 'BUT', 'IN', 'ON', 'AT', 'TO', 'FOR', 'OF', 'WITH', 'BY', 'FROM',
        'UP', 'ABOUT', 'INTO', 'THROUGH', 'DURING', 'BEFORE', 'AFTER', 'ABOVE', 'BELOW',
        'A', 'AN', 'AS', 'ARE', 'WAS', 'WERE', 'BEEN', 'BE', 'HAVE', 'HAS', 'HAD', 'DO',
        'IS', 'IT', 'ITS', 'THIS', 'THAT', 'THESE', 'THOSE', 'THEY', 'THEM', 'THEIR',
        'WE', 'US', 'OUR', 'YOU', 'YOUR', 'HE', 'HIM', 'HIS', 'SHE', 'HER', 'I', 'ME', 'MY',
        'ALL', 'ANY', 'BOTH', 'EACH', 'FEW', 'MORE', 'MOST', 'OTHER', 'SOME', 'SUCH',
        'NO', 'NOR', 'NOT', 'ONLY', 'OWN', 'SAME', 'SO', 'THAN', 'TOO', 'VERY',
        
        # Academic stopwords
        'PAPER', 'STUDY', 'RESEARCH', 'ANALYSIS', 'METHOD', 'APPROACH', 'TECHNIQUE',
        'RESULT', 'RESULTS', 'CONCLUSION', 'CONCLUSIONS', 'DISCUSSION', 'INTRODUCTION',
        'ABSTRACT', 'FIGURE', 'TABLE', 'EQUATION', 'SECTION', 'CHAPTER', 'APPENDIX',
        'REFERENCE', 'REFERENCES', 'SHOW', 'SHOWN', 'FIND', 'FOUND', 'PRESENT',
        'USING', 'USED', 'BASED', 'GIVEN', 'OBTAINED', 'OBSERVED', 'CONSIDERED',
        
        # Other common academic terms
        'ALSO', 'THEREFORE', 'FURTHERMORE', 'HOWEVER', 'MOREOVER', 'THUS', 'HENCE',
        'WHICH', 'WHERE', 'WHEN', 'WHO', 'WHAT', 'WHY', 'HOW', 'CASE', 'CASES',
        'FIRST', 'SECOND', 'THIRD', 'ONE', 'TWO', 'THREE', 'NEW', 'OLD', 'LARGE', 'SMALL',
    }
    
    word_counts = Counter()
    
    for text in texts:
        # Simple tokenization: split by whitespace and punctuation
        words = text.upper().replace(',', ' ').replace('.', ' ').replace(':', ' ').replace(';', ' ')
        words = words.replace('(', ' ').replace(')', ' ').replace('[', ' ').replace(']', ' ')
        words = words.replace('-', ' ').replace('_', ' ').replace('/', ' ').replace('\\', ' ')
        words = words.split()
        
        for word in words:
            # Clean word: remove non-alphabetic characters
            clean_word = ''.join(c for c in word if c.isalpha())
            
            # Filter by length and stopwords
            if (len(clean_word) >= min_word_length and 
                clean_word not in STOPWORDS and
                not clean_word.isdigit()):
                word_counts[clean_word] += 1
    
    # Convert to dictionary
    word_frequencies = dict(word_counts)
    
    # Add theme words with highest weights if provided
    if theme_words_file and os.path.exists(theme_words_file):
        try:
            print(f"📝 Loading theme words from: {theme_words_file}")
            with open(theme_words_file, 'r', encoding='utf-8') as f:
                theme_words = [line.strip().upper() for line in f if line.strip()]
            
            if theme_words:
                # Get current max frequency for boosting
                max_freq = max(word_frequencies.values()) if word_frequencies else 100
                
                # Add theme words with boosted frequencies
                for i, theme_word in enumerate(theme_words):
                    # Give decreasing weights to theme words (highest first)
                    boost_factor = 1.2 - (i * 0.05)  # 1.2, 1.15, 1.1, etc.
                    boosted_freq = max_freq * boost_factor
                    
                    # If word already exists, boost its frequency; otherwise add it
                    if theme_word in word_frequencies:
                        word_frequencies[theme_word] = max(word_frequencies[theme_word], boosted_freq)
                    else:
                        word_frequencies[theme_word] = boosted_freq
                
                print(f"   Added {len(theme_words)} theme words with boosted frequencies")
                print(f"   Theme words: {', '.join(theme_words[:5])}{'...' if len(theme_words) > 5 else ''}")
        
        except Exception as e:
            print(f"⚠️  Failed to load theme words: {e}")
    
    return word_frequencies


def create_masked_wordcloud(word_freq: Dict[str, int], 
                          mask_path: str, 
                          output_path: str,
                          font_path: str = None,
                          max_words: int = 500,
                          background_color: str = 'black') -> bool:
    """Generate masked wordcloud from word frequencies
    
    Args:
        word_freq: Dictionary of word frequencies
        mask_path: Path to mask image file
        output_path: Path for output wordcloud image
        font_path: Optional custom font path
        max_words: Maximum number of words to display
        background_color: Background color
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load and process mask image
        mask_image = Image.open(mask_path)
        if mask_image.mode != 'L':
            mask_image = mask_image.convert('L')
        
        mask_array = np.array(mask_image)
        
        # Create mask: white areas (255) = no words, dark areas (0) = place words
        processed_mask = np.where(mask_array < 128, 0, 255).astype(np.uint8)
        
        # Color function for pure white text
        def white_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
            return 'rgb(255, 255, 255)'
        
        # Create high-quality WordCloud with optimized parameters
        original_size = mask_image.size
        
        # Scale up for high resolution (4x resolution for crisp output)
        hq_width = original_size[0] * 4
        hq_height = original_size[1] * 4
        
        # Resize mask for high resolution
        mask_hq = mask_image.resize((hq_width, hq_height), Image.LANCZOS)
        mask_hq_array = np.array(mask_hq)
        processed_mask_hq = np.where(mask_hq_array < 128, 0, 255).astype(np.uint8)
        
        wordcloud = WordCloud(
            width=hq_width,
            height=hq_height, 
            background_color=background_color,
            max_words=max_words,
            relative_scaling=0.3,
            min_font_size=12,           # Increased for high-res
            max_font_size=400,          # Much larger for high-res
            prefer_horizontal=0.7,      # Your optimized ratio
            mask=processed_mask_hq,
            color_func=white_color_func,
            collocations=False,
            random_state=42,
            font_step=1,                # Fine-grained font adjustment
            margin=5,                   # Reduced margin
            font_path=font_path
        )
        
        # Generate wordcloud
        wordcloud.generate_from_frequencies(word_freq)
        
        # Save high-quality image with matplotlib for better control
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        # Create high-DPI figure
        dpi = 800  # High quality DPI like in yyktest.py
        fig_width = hq_width / dpi
        fig_height = hq_height / dpi
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        
        # Remove all margins and padding
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
        ax.set_position([0, 0, 1, 1])
        fig.patch.set_facecolor(background_color)
        
        # Save with high quality
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight', pad_inches=0,
                   facecolor=background_color, edgecolor='none')
        plt.close()
        
        print(f"✅ High-quality wordcloud saved: {output_path}")
        print(f"   Resolution: {hq_width}x{hq_height} @ {dpi} DPI")
        print(f"   Words placed: {len(wordcloud.words_)}/{len(word_freq)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create wordcloud: {e}")
        return False


def _get_texts_from_arxiv_ids(arxiv_ids: List[str]) -> List[str]:
    """Download and extract text from ArXiv papers"""
    print(f"🚀 Processing {len(arxiv_ids)} ArXiv papers...")
    texts = []
    for arxiv_id in arxiv_ids:
        pdf_path = download_arxiv_pdf(arxiv_id)
        if pdf_path:
            text = extract_text_from_pdf(pdf_path)
            if text.strip():
                texts.append(text)
                print(f"✓ Extracted text from {arxiv_id} ({len(text)//1000}k chars)")
            else:
                print(f"⚠️  No text extracted from {arxiv_id}")
    return texts

def _get_texts_from_pdf_directory(pdf_dir: str) -> List[str]:
    """Extract text from PDF directory"""
    pdf_files = list(Path(pdf_dir).glob("*.pdf"))
    if not pdf_files:
        print(f"❌ No PDF files found in {pdf_dir}")
        return []
    
    print(f"🚀 Processing {len(pdf_files)} PDF files...")
    texts = []
    for pdf_file in pdf_files:
        text = extract_text_from_pdf(str(pdf_file))
        if text.strip():
            texts.append(text)
            print(f"✓ Extracted text from {pdf_file.name} ({len(text)//1000}k chars)")
        else:
            print(f"⚠️  No text extracted from {pdf_file.name}")
    return texts

def create_wordcloud(texts: List[str],
                    mask_path: str,
                    output_path: str,
                    font_path: str = None,
                    theme_words_file: str = None,
                    max_words: int = 500) -> bool:
    """Create wordcloud from texts - unified processing function"""
    if not texts:
        print("❌ No texts provided!")
        return False
    
    # Get word frequencies
    print(f"📊 Calculating word frequencies...")
    word_freq = get_word_frequencies(texts, theme_words_file=theme_words_file)
    print(f"   Found {len(word_freq)} unique words")
    
    # Show top words
    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    print("   Top words:", [f"{w}({f})" for w, f in top_words])
    
    # Generate wordcloud
    return create_masked_wordcloud(word_freq, mask_path, output_path, font_path, max_words)

# Legacy wrapper functions for backward compatibility
def process_arxiv_ids(arxiv_ids: List[str], 
                     mask_path: str, 
                     output_path: str,
                     font_path: str = None,
                     theme_words_file: str = None,
                     max_words: int = 500) -> bool:
    """Process ArXiv papers and generate wordcloud"""
    texts = _get_texts_from_arxiv_ids(arxiv_ids)
    return create_wordcloud(texts, mask_path, output_path, font_path, theme_words_file, max_words)


def process_pdf_directory(pdf_dir: str, 
                         mask_path: str, 
                         output_path: str,
                         font_path: str = None,
                         theme_words_file: str = None,
                         max_words: int = 500) -> bool:
    """Process PDF directory and generate wordcloud"""
    texts = _get_texts_from_pdf_directory(pdf_dir)
    return create_wordcloud(texts, mask_path, output_path, font_path, theme_words_file, max_words)


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description='Generate masked word clouds from ArXiv papers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From ArXiv IDs file
  python arxiv_wordcloud.py --ids arxiv_ids.txt --mask mask.jpg --output wordcloud.png
  
  # From PDF directory
  python arxiv_wordcloud.py --pdfs ./papers/ --mask mask.jpg --output wordcloud.png
  
  # With custom font
  python arxiv_wordcloud.py --ids arxiv_ids.txt --mask mask.jpg --output result.png --font fonts/custom.ttf
        """
    )
    
    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--ids', type=str, help='Text file containing ArXiv IDs (one per line)')
    input_group.add_argument('--pdfs', type=str, help='Directory containing PDF files')
    
    # Required arguments
    parser.add_argument('--mask', type=str, required=True, help='Path to mask image file')
    parser.add_argument('--output', type=str, required=True, help='Output wordcloud image path')
    
    # Optional arguments
    parser.add_argument('--font', type=str, help='Path to custom font file')
    parser.add_argument('--theme-words', type=str, help='Text file with theme words (one per line, highest priority first)')
    parser.add_argument('--max-words', type=int, default=500, help='Maximum number of words (default: 500)')
    
    args = parser.parse_args()
    
    # Validate inputs
    if args.ids and not os.path.exists(args.ids):
        print(f"❌ ArXiv IDs file not found: {args.ids}")
        return 1
        
    if args.pdfs and not os.path.exists(args.pdfs):
        print(f"❌ PDF directory not found: {args.pdfs}")
        return 1
        
    if not os.path.exists(args.mask):
        print(f"❌ Mask image not found: {args.mask}")
        return 1
    
    # Process papers
    success = False
    
    if args.ids:
        # Read ArXiv IDs from file
        with open(args.ids, 'r') as f:
            arxiv_ids = [line.strip() for line in f if line.strip()]
        success = process_arxiv_ids(arxiv_ids, args.mask, args.output, args.font, args.theme_words, args.max_words)
        
    elif args.pdfs:
        # Process PDF directory
        success = process_pdf_directory(args.pdfs, args.mask, args.output, args.font, args.theme_words, args.max_words)
    
    return 0 if success else 1


# API functions for programmatic use
def create_wordcloud_from_arxiv(arxiv_ids: List[str], 
                               mask_image: str, 
                               output_file: str,
                               font_path: str = None,
                               theme_words_file: str = None,
                               max_words: int = 500) -> bool:
    """Simple API function to create wordcloud from ArXiv papers"""
    texts = _get_texts_from_arxiv_ids(arxiv_ids)
    return create_wordcloud(texts, mask_image, output_file, font_path, theme_words_file, max_words)


def create_wordcloud_from_pdfs(pdf_directory: str,
                              mask_image: str,
                              output_file: str,
                              font_path: str = None,
                              theme_words_file: str = None,
                              max_words: int = 500) -> bool:
    """Simple API function to create wordcloud from PDF directory"""
    texts = _get_texts_from_pdf_directory(pdf_directory)
    return create_wordcloud(texts, mask_image, output_file, font_path, theme_words_file, max_words)


def create_wordcloud_from_texts(texts: List[str],
                               mask_image: str,
                               output_file: str,
                               font_path: str = None,
                               theme_words_file: str = None,
                               max_words: int = 500) -> bool:
    """Simple API function to create wordcloud from text list"""
    return create_wordcloud(texts, mask_image, output_file, font_path, theme_words_file, max_words)


if __name__ == "__main__":
    sys.exit(main())