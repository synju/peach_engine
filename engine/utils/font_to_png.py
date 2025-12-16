#!/usr/bin/env python3
"""
Font to PNG Grid Generator
Renders TTF/OTF fonts to a high-res anti-aliased PNG grid.
"""

from PIL import Image, ImageDraw, ImageFont
import argparse
import string
import json
import os

def generate_font_grid(
	font_path: str,
	output_path: str = "font_grid.png",
	font_size: int = 64,
	chars: str = None,
	columns: int = 16,
	padding: int = 4,
	bg_color: tuple = (0, 0, 0, 0),  # Transparent
	text_color: tuple = (255, 255, 255, 255),  # White
):
	# Default character set
	if chars is None:
		chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + string.punctuation + " "

	# Load font
	font = ImageFont.truetype(font_path, font_size)

	# Calculate cell size using font metrics for proper baseline alignment
	ascent, descent = font.getmetrics()

	max_width = 0
	for char in chars:
		bbox = font.getbbox(char)
		w = bbox[2] - bbox[0]
		max_width = max(max_width, w)

	cell_width = max_width + padding * 2
	cell_height = ascent + descent + padding * 2

	# Calculate grid dimensions
	rows = (len(chars) + columns - 1) // columns
	img_width = columns * cell_width
	img_height = rows * cell_height

	# Create image
	img = Image.new("RGBA", (img_width, img_height), bg_color)
	draw = ImageDraw.Draw(img)

	# Draw characters
	for i, char in enumerate(chars):
		col = i % columns
		row = i // columns

		x = col * cell_width + padding
		y = row * cell_height + padding

		# Center character horizontally only, use baseline for vertical
		bbox = font.getbbox(char)
		char_w = bbox[2] - bbox[0]
		offset_x = (cell_width - padding * 2 - char_w) // 2

		# Draw at baseline position (ascent from top of cell)
		draw.text(
			(x + offset_x - bbox[0], y),
			char,
			font=font,
			fill=text_color,
		)

	# Save PNG
	img.save(output_path, "PNG")

	# Build JSON data
	rows_data = []
	for row in range(rows):
		start = row * columns
		end = min(start + columns, len(chars))
		rows_data.append(list(chars[start:end]))

	json_data = {
		"image": os.path.basename(output_path),
		"cell_width": cell_width,
		"cell_height": cell_height,
		"columns": columns,
		"rows": rows,
		"padding": padding,
		"font_size": font_size,
		"ascent": ascent,
		"descent": descent,
		"characters_per_row": rows_data,
		"characters": list(chars),
	}

	# Save JSON
	json_path = os.path.splitext(output_path)[0] + ".json"
	with open(json_path, "w") as f:
		json.dump(json_data, f, indent=2)

	print(f"Saved: {output_path}")
	print(f"Saved: {json_path}")
	print(f"Grid: {columns}x{rows} cells, {cell_width}x{cell_height}px each")
	print(f"Image: {img_width}x{img_height}px")
	print(f"Characters: {len(chars)}")

# ============== CONFIGURE THIS ==============
DEFAULT_FONT = "font_path.ttf"

# ============================================

def main():
	parser = argparse.ArgumentParser(description="Convert font to PNG grid")
	parser.add_argument("font", nargs="?", default=DEFAULT_FONT, help="Path to TTF/OTF font file")
	parser.add_argument("-o", "--output", default="font_grid.png", help="Output PNG path")
	parser.add_argument("-s", "--size", type=int, default=64, help="Font size in pixels (default: 64)")
	parser.add_argument("-c", "--columns", type=int, default=16, help="Grid columns (default: 16)")
	parser.add_argument("-p", "--padding", type=int, default=4, help="Cell padding (default: 4)")
	parser.add_argument("--chars", help="Custom character set (default: A-Z, a-z, 0-9, punctuation)")
	parser.add_argument("--bg", default="transparent", help="Background: 'transparent', 'black', 'white', or hex (#RRGGBB)")
	parser.add_argument("--fg", default="white", help="Text color: 'black', 'white', or hex (#RRGGBB)")

	args = parser.parse_args()

	# Parse colors
	def parse_color(c):
		if c == "transparent":
			return (0, 0, 0, 0)
		elif c == "black":
			return (0, 0, 0, 255)
		elif c == "white":
			return (255, 255, 255, 255)
		elif c.startswith("#"):
			c = c.lstrip("#")
			return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
		return (255, 255, 255, 255)

	generate_font_grid(
		font_path=args.font,
		output_path=args.output,
		font_size=args.size,
		chars=args.chars,
		columns=args.columns,
		padding=args.padding,
		bg_color=parse_color(args.bg),
		text_color=parse_color(args.fg),
	)

if __name__ == "__main__":
	main()