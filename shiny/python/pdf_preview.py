"""The text of a PDF for the app's file preview, read as the FAIRe mapper tools read it.

Usage: python pdf_preview.py TOOL_DIR PDF OUT_JSON [MAX_CHARS]

TOOL_DIR is tools/faire_mapper, which holds faire_mapper_text.py. Writes {"pages": n, "text": "..."}
with the text cut at MAX_CHARS (6000 by default), or {"error": "..."} if the PDF cannot be read.
"""
import json
import sys


def main(tool_dir, pdf, out, max_chars=6000):
    sys.path.insert(0, tool_dir)
    result = {}
    try:
        from faire_mapper_text import pdf_pages, pdf_text
        text = pdf_text(pdf)
        result = {'pages': pdf_pages(pdf), 'text': text[:max_chars], 'cut': len(text) > max_chars}
    except SystemExit as e:
        result = {'error': str(e)}
    except Exception as e:  # a damaged or encrypted PDF
        result = {'error': 'the PDF could not be read: %s' % e}
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 6000)
