#!/usr/bin/env python3
"""
Paper WordCloud Generator - Complete Demo
Shows all features: basic wordcloud, theme words, and command line usage
"""

import sys
import os
import subprocess

# Add parent directory to path to import arxiv_wordcloud
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from arxiv_wordcloud import create_wordcloud_from_arxiv

def check_files():
    """Check if all required example files exist"""
    required_files = {
        'arxiv_ids.txt': 'ArXiv ID list file',
        'theme_words.txt': 'Theme words file', 
        'mask.jpg': 'Mask image file'
    }
    
    missing = []
    for filename, description in required_files.items():
        if not os.path.exists(filename):
            missing.append(f"{filename} ({description})")
    
    if missing:
        print("❌ Missing required files:")
        for item in missing:
            print(f"   - {item}")
        print("\nPlease ensure all example files are present!")
        return False
    
    return True

def demo_basic():
    """Demo 1: Basic wordcloud generation"""
    print("\n" + "="*60)
    print("🚀 DEMO 1: Basic WordCloud Generation")
    print("="*60)
    
    # Demo with physics papers
    arxiv_ids = [
        "2211.02002",  # Quantum spin liquid
        "2302.10115",  # Non-Hermitian Dirac fermions
        "2409.18050",  # Superconductivity
    ]
    
    print(f"📝 Processing {len(arxiv_ids)} papers...")
    print(f"🎭 Using mask: mask.jpg")
    print(f"📸 Output: basic_wordcloud.png")
    
    success = create_wordcloud_from_arxiv(
        arxiv_ids=arxiv_ids,
        mask_image="mask.jpg", 
        output_file="basic_wordcloud.png",
        font_path="../fonts/HardingTextRegular.ttf" if os.path.exists("../fonts/HardingTextRegular.ttf") else None
    )
    
    if success:
        print("✅ Basic demo completed successfully!")
        print(f"   Generated: basic_wordcloud.png")
    else:
        print("❌ Basic demo failed!")
    
    return success

def demo_theme_words():
    """Demo 2: WordCloud with theme words"""
    print("\n" + "="*60)
    print("🎨 DEMO 2: WordCloud with Theme Words")
    print("="*60)
    
    # Read the IDs from file
    with open("arxiv_ids.txt", 'r') as f:
        arxiv_ids = [line.strip() for line in f if line.strip()]
    
    print(f"📝 Processing {len(arxiv_ids)} papers from arxiv_ids.txt")
    print(f"🎭 Using mask: mask.jpg")
    print(f"🏷️  Using theme words: theme_words.txt")
    print(f"📸 Output: themed_wordcloud.png")
    
    success = create_wordcloud_from_arxiv(
        arxiv_ids=arxiv_ids,
        mask_image="mask.jpg", 
        output_file="themed_wordcloud.png",
        theme_words_file="theme_words.txt",
        font_path="../fonts/HardingTextRegular.ttf" if os.path.exists("../fonts/HardingTextRegular.ttf") else None
    )
    
    if success:
        print("✅ Theme words demo completed successfully!")
        print(f"   Generated: themed_wordcloud.png")
        print("   Note: Key terms should be prominently displayed")
    else:
        print("❌ Theme words demo failed!")
    
    return success

def demo_command_line():
    """Demo 3: Command line interface examples"""
    print("\n" + "="*60)
    print("💻 DEMO 3: Command Line Interface")
    print("="*60)
    
    # Go to parent directory to run the main script
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    
    commands = [
        {
            'name': 'Help Command',
            'cmd': ['python', 'arxiv_wordcloud.py', '--help'],
            'description': 'Show all available options'
        },
        {
            'name': 'Basic CLI Usage',
            'cmd': ['python', 'arxiv_wordcloud.py', 
                   '--ids', 'examples/arxiv_ids.txt',
                   '--mask', 'examples/mask.jpg', 
                   '--output', 'examples/cli_basic.png',
                   '--max-words', '200'],
            'description': 'Generate wordcloud from command line'
        },
        {
            'name': 'Full Featured CLI',
            'cmd': ['python', 'arxiv_wordcloud.py',
                   '--ids', 'examples/arxiv_ids.txt',
                   '--mask', 'examples/mask.jpg',
                   '--output', 'examples/cli_themed.png', 
                   '--theme-words', 'examples/theme_words.txt',
                   '--font', 'fonts/HardingTextRegular.ttf',
                   '--max-words', '300'],
            'description': 'Full CLI with all options'
        }
    ]
    
    results = []
    for demo in commands:
        print(f"\n🔧 {demo['name']}: {demo['description']}")
        print(f"Command: {' '.join(demo['cmd'])}")
        
        try:
            result = subprocess.run(
                demo['cmd'], 
                cwd=parent_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                print("✅ Command executed successfully!")
                if demo['name'] != 'Help Command':  # Don't show full help output
                    print(f"Output: {result.stdout[-200:]}")  # Last 200 chars
                results.append(True)
            else:
                print("❌ Command failed!")
                print(f"Error: {result.stderr}")
                results.append(False)
                
        except subprocess.TimeoutExpired:
            print("❌ Command timed out!")
            results.append(False)
        except Exception as e:
            print(f"❌ Command error: {e}")
            results.append(False)
    
    return all(results)

def main():
    """Run all demos"""
    print("🎭 Paper WordCloud Generator - Complete Demo Suite")
    print("="*60)
    print("This demo shows all features of the wordcloud generator:")
    print("1. Basic API usage")
    print("2. Theme words functionality") 
    print("3. Command line interface")
    print("="*60)
    
    # Check if we're in the right directory
    if not check_files():
        return
    
    # Run all demos
    results = []
    
    try:
        results.append(demo_basic())
        results.append(demo_theme_words())
        results.append(demo_command_line())
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
        return
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return
    
    # Final summary
    print("\n" + "="*60)
    print("📊 DEMO SUITE SUMMARY")
    print("="*60)
    
    demo_names = ['Basic WordCloud', 'Theme Words', 'Command Line']
    for i, (name, success) in enumerate(zip(demo_names, results)):
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{i+1}. {name}: {status}")
    
    success_count = sum(results)
    total_count = len(results)
    
    if success_count == total_count:
        print(f"\n🎉 ALL DEMOS PASSED ({success_count}/{total_count})")
        print("🎨 Check the generated wordcloud files:")
        generated_files = [
            'basic_wordcloud.png',
            'themed_wordcloud.png', 
            'cli_basic.png',
            'cli_themed.png'
        ]
        for file in generated_files:
            if os.path.exists(file):
                print(f"   ✓ {file}")
            else:
                print(f"   - {file} (not generated)")
    else:
        print(f"\n⚠️  SOME DEMOS FAILED ({success_count}/{total_count})")
        print("Please check the error messages above.")

if __name__ == "__main__":
    main()