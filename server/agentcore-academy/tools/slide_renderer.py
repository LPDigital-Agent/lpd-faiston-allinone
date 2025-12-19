# =============================================================================
# Slide Renderer Tool - Pillow-based PNG Generation
# =============================================================================
# Generates educational slide images from structured data using Pillow.
#
# Design System:
# - Background: Gradient (brand colors)
# - Font: Poppins (fallback to DejaVu Sans)
# - Colors: Brand orange (#FF4D00), cyan (#06B6D4), purple (#A855F7)
# - Resolution: 1920x1080 (16:9)
#
# Slide Types:
# - title: Logo + title + subtitle
# - bullets: Title + bullet points
# - diagram: Title + flow elements
# - summary: Title + key takeaways
# =============================================================================

from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, List, Optional, Tuple
import io
import os

# =============================================================================
# Configuration
# =============================================================================

# Canvas size (16:9 Full HD)
CANVAS_WIDTH = 1920
CANVAS_HEIGHT = 1080

# Brand colors
COLOR_ORANGE = "#FF4D00"
COLOR_CYAN = "#06B6D4"
COLOR_PURPLE = "#A855F7"
COLOR_WHITE = "#FFFFFF"
COLOR_LIGHT_GRAY = "#F5F5F7"
COLOR_DARK = "#0D0E12"

# Gradient presets (start_color, end_color)
GRADIENTS = {
    "orange_purple": ("#FF4D00", "#A855F7"),
    "cyan_purple": ("#06B6D4", "#A855F7"),
    "dark_purple": ("#1A1B20", "#2D1F3D"),
    "dark_cyan": ("#1A1B20", "#1F2D3D"),
}

# Default gradient
DEFAULT_GRADIENT = "dark_purple"

# Font configuration (with fallbacks)
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",  # macOS
    "/var/task/fonts/Poppins-Bold.ttf",  # Lambda layer
    "/var/task/fonts/Poppins-Regular.ttf",
]

# =============================================================================
# Utility Functions
# =============================================================================


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def interpolate_color(
    color1: Tuple[int, int, int],
    color2: Tuple[int, int, int],
    factor: float,
) -> Tuple[int, int, int]:
    """Interpolate between two colors."""
    return tuple(
        int(c1 + (c2 - c1) * factor)
        for c1, c2 in zip(color1, color2)
    )


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """
    Get a font with fallback support.

    Args:
        size: Font size in pixels
        bold: Whether to use bold variant

    Returns:
        PIL FreeTypeFont object
    """
    # Try each font path
    for font_path in FONT_PATHS:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except (IOError, OSError):
                continue

    # Final fallback: default PIL font (very basic)
    print("[SlideRenderer] Warning: Using default PIL font (no TrueType found)")
    return ImageFont.load_default()


def draw_gradient_background(
    draw: ImageDraw.ImageDraw,
    width: int,
    height: int,
    gradient_name: str = DEFAULT_GRADIENT,
) -> None:
    """
    Draw a vertical gradient background.

    Args:
        draw: PIL ImageDraw object
        width: Canvas width
        height: Canvas height
        gradient_name: Name of gradient preset
    """
    start_hex, end_hex = GRADIENTS.get(gradient_name, GRADIENTS[DEFAULT_GRADIENT])
    start_rgb = hex_to_rgb(start_hex)
    end_rgb = hex_to_rgb(end_hex)

    for y in range(height):
        factor = y / height
        color = interpolate_color(start_rgb, end_rgb, factor)
        draw.line([(0, y), (width, y)], fill=color)


def draw_glass_card(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    height: int,
    radius: int = 20,
) -> None:
    """
    Draw a glass-effect card (semi-transparent rounded rectangle).

    Args:
        draw: PIL ImageDraw object
        x, y: Top-left corner
        width, height: Card dimensions
        radius: Corner radius
    """
    # Semi-transparent white overlay
    card_color = (255, 255, 255, 25)  # RGBA with low alpha

    # Draw rounded rectangle (simplified - using rectangle for now)
    # Note: For proper rounded corners, use PIL.ImageDraw.rounded_rectangle (Pillow 8.2+)
    try:
        draw.rounded_rectangle(
            [x, y, x + width, y + height],
            radius=radius,
            fill=card_color,
            outline=(255, 255, 255, 50),
            width=1,
        )
    except AttributeError:
        # Fallback for older Pillow versions
        draw.rectangle([x, y, x + width, y + height], fill=card_color)


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """
    Wrap text to fit within a maximum width.

    Args:
        text: Text to wrap
        font: PIL font object
        max_width: Maximum width in pixels

    Returns:
        List of text lines
    """
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = font.getbbox(test_line)
        line_width = bbox[2] - bbox[0]

        if line_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))

    return lines


# =============================================================================
# Slide Renderers
# =============================================================================


def render_title_slide(
    title: str,
    subtitle: str = "",
    gradient: str = DEFAULT_GRADIENT,
) -> bytes:
    """
    Render a title slide.

    Args:
        title: Main title text
        subtitle: Optional subtitle
        gradient: Gradient preset name

    Returns:
        PNG image as bytes
    """
    # Create image with RGBA for transparency support
    img = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    # Draw gradient background
    draw_gradient_background(draw, CANVAS_WIDTH, CANVAS_HEIGHT, gradient)

    # Fonts
    title_font = get_font(72, bold=True)
    subtitle_font = get_font(36)

    # Calculate positions (centered)
    title_bbox = title_font.getbbox(title)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (CANVAS_WIDTH - title_width) // 2
    title_y = CANVAS_HEIGHT // 2 - 80

    # Draw title
    draw.text((title_x, title_y), title, font=title_font, fill=COLOR_WHITE)

    # Draw subtitle if provided
    if subtitle:
        subtitle_bbox = subtitle_font.getbbox(subtitle)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        subtitle_x = (CANVAS_WIDTH - subtitle_width) // 2
        subtitle_y = title_y + 100

        draw.text((subtitle_x, subtitle_y), subtitle, font=subtitle_font, fill=COLOR_LIGHT_GRAY)

    # Draw accent line under title
    line_y = title_y + 85
    line_width = 200
    line_x = (CANVAS_WIDTH - line_width) // 2
    draw.rectangle(
        [line_x, line_y, line_x + line_width, line_y + 4],
        fill=hex_to_rgb(COLOR_ORANGE),
    )

    # Convert to bytes
    output = io.BytesIO()
    img.convert("RGB").save(output, format="PNG", quality=95)
    return output.getvalue()


def render_bullets_slide(
    title: str,
    bullets: List[str],
    gradient: str = DEFAULT_GRADIENT,
) -> bytes:
    """
    Render a bullets slide.

    Args:
        title: Slide title
        bullets: List of bullet point texts
        gradient: Gradient preset name

    Returns:
        PNG image as bytes
    """
    img = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    # Draw gradient background
    draw_gradient_background(draw, CANVAS_WIDTH, CANVAS_HEIGHT, gradient)

    # Fonts
    title_font = get_font(56, bold=True)
    bullet_font = get_font(32)

    # Draw title (left-aligned with padding)
    padding_x = 120
    title_y = 100

    draw.text((padding_x, title_y), title, font=title_font, fill=COLOR_WHITE)

    # Draw accent line under title
    draw.rectangle(
        [padding_x, title_y + 80, padding_x + 100, title_y + 84],
        fill=hex_to_rgb(COLOR_CYAN),
    )

    # Draw glass card for bullets
    card_x = padding_x
    card_y = title_y + 120
    card_width = CANVAS_WIDTH - (padding_x * 2)
    card_height = CANVAS_HEIGHT - card_y - 80

    draw_glass_card(draw, card_x, card_y, card_width, card_height)

    # Draw bullets
    bullet_x = card_x + 60
    bullet_y = card_y + 50
    bullet_spacing = 100
    max_text_width = card_width - 140

    for i, bullet_text in enumerate(bullets[:5]):  # Max 5 bullets
        # Bullet point circle
        bullet_radius = 8
        bullet_center_y = bullet_y + 20
        draw.ellipse(
            [
                bullet_x - bullet_radius,
                bullet_center_y - bullet_radius,
                bullet_x + bullet_radius,
                bullet_center_y + bullet_radius,
            ],
            fill=hex_to_rgb(COLOR_ORANGE),
        )

        # Bullet text (with wrapping)
        lines = wrap_text(bullet_text, bullet_font, max_text_width)
        text_y = bullet_y
        for line in lines[:2]:  # Max 2 lines per bullet
            draw.text((bullet_x + 30, text_y), line, font=bullet_font, fill=COLOR_WHITE)
            text_y += 45

        bullet_y += bullet_spacing

    # Convert to bytes
    output = io.BytesIO()
    img.convert("RGB").save(output, format="PNG", quality=95)
    return output.getvalue()


def render_diagram_slide(
    title: str,
    elements: List[str],
    gradient: str = DEFAULT_GRADIENT,
) -> bytes:
    """
    Render a diagram/flow slide.

    Args:
        title: Slide title
        elements: List of flow elements (e.g., ["Input", "→", "Process", "→", "Output"])
        gradient: Gradient preset name

    Returns:
        PNG image as bytes
    """
    img = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    # Draw gradient background
    draw_gradient_background(draw, CANVAS_WIDTH, CANVAS_HEIGHT, gradient)

    # Fonts
    title_font = get_font(56, bold=True)
    element_font = get_font(28, bold=True)

    # Draw title
    padding_x = 120
    title_y = 100

    draw.text((padding_x, title_y), title, font=title_font, fill=COLOR_WHITE)

    # Draw accent line
    draw.rectangle(
        [padding_x, title_y + 80, padding_x + 100, title_y + 84],
        fill=hex_to_rgb(COLOR_PURPLE),
    )

    # Filter out arrows and get actual elements
    flow_elements = [e for e in elements if e not in ("→", "->", "=>")]

    if not flow_elements:
        flow_elements = elements

    # Calculate positions for flow elements
    num_elements = len(flow_elements)
    if num_elements == 0:
        return render_title_slide(title, "No elements", gradient)

    element_width = 200
    element_height = 120
    spacing = 80

    total_width = (num_elements * element_width) + ((num_elements - 1) * spacing)
    start_x = (CANVAS_WIDTH - total_width) // 2
    element_y = (CANVAS_HEIGHT - element_height) // 2 + 50

    # Draw each element
    for i, element in enumerate(flow_elements):
        elem_x = start_x + i * (element_width + spacing)

        # Draw element box (rounded rectangle with gradient accent)
        box_color = hex_to_rgb(COLOR_CYAN) if i % 2 == 0 else hex_to_rgb(COLOR_PURPLE)
        try:
            draw.rounded_rectangle(
                [elem_x, element_y, elem_x + element_width, element_y + element_height],
                radius=15,
                fill=(*box_color, 180),  # Semi-transparent
                outline=(*box_color, 255),
                width=2,
            )
        except AttributeError:
            draw.rectangle(
                [elem_x, element_y, elem_x + element_width, element_y + element_height],
                fill=(*box_color, 180),
            )

        # Draw element text (centered in box)
        lines = wrap_text(element, element_font, element_width - 20)
        text_height = len(lines) * 35
        text_y = element_y + (element_height - text_height) // 2

        for line in lines[:2]:
            bbox = element_font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            text_x = elem_x + (element_width - line_width) // 2
            draw.text((text_x, text_y), line, font=element_font, fill=COLOR_WHITE)
            text_y += 35

        # Draw arrow to next element
        if i < num_elements - 1:
            arrow_x = elem_x + element_width + 10
            arrow_y = element_y + element_height // 2

            # Arrow line
            draw.line(
                [(arrow_x, arrow_y), (arrow_x + spacing - 20, arrow_y)],
                fill=COLOR_WHITE,
                width=3,
            )

            # Arrow head
            arrow_tip_x = arrow_x + spacing - 20
            draw.polygon(
                [
                    (arrow_tip_x, arrow_y),
                    (arrow_tip_x - 15, arrow_y - 10),
                    (arrow_tip_x - 15, arrow_y + 10),
                ],
                fill=COLOR_WHITE,
            )

    # Convert to bytes
    output = io.BytesIO()
    img.convert("RGB").save(output, format="PNG", quality=95)
    return output.getvalue()


def render_summary_slide(
    title: str,
    key_points: List[str],
    gradient: str = DEFAULT_GRADIENT,
) -> bytes:
    """
    Render a summary slide with key takeaways.

    Args:
        title: Slide title (usually "Resumo" or "Key Takeaways")
        key_points: List of key points
        gradient: Gradient preset name

    Returns:
        PNG image as bytes
    """
    img = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    # Draw gradient background
    draw_gradient_background(draw, CANVAS_WIDTH, CANVAS_HEIGHT, gradient)

    # Fonts
    title_font = get_font(56, bold=True)
    point_font = get_font(28)
    number_font = get_font(36, bold=True)

    # Draw title (centered)
    title_bbox = title_font.getbbox(title)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (CANVAS_WIDTH - title_width) // 2
    title_y = 100

    draw.text((title_x, title_y), title, font=title_font, fill=COLOR_WHITE)

    # Draw accent underline
    line_width = 150
    line_x = (CANVAS_WIDTH - line_width) // 2
    draw.rectangle(
        [line_x, title_y + 80, line_x + line_width, title_y + 84],
        fill=hex_to_rgb(COLOR_ORANGE),
    )

    # Draw key points with numbered circles
    padding_x = 200
    point_y = title_y + 150
    point_spacing = 140
    max_text_width = CANVAS_WIDTH - (padding_x * 2) - 80

    for i, point in enumerate(key_points[:4]):  # Max 4 points
        # Number circle
        circle_x = padding_x
        circle_y = point_y + 15
        circle_radius = 25

        # Alternate colors
        circle_color = hex_to_rgb(COLOR_CYAN) if i % 2 == 0 else hex_to_rgb(COLOR_PURPLE)

        draw.ellipse(
            [
                circle_x - circle_radius,
                circle_y - circle_radius,
                circle_x + circle_radius,
                circle_y + circle_radius,
            ],
            fill=circle_color,
        )

        # Number text
        number = str(i + 1)
        number_bbox = number_font.getbbox(number)
        number_width = number_bbox[2] - number_bbox[0]
        number_x = circle_x - number_width // 2
        number_y = circle_y - 22

        draw.text((number_x, number_y), number, font=number_font, fill=COLOR_WHITE)

        # Point text (with wrapping)
        text_x = padding_x + 50
        lines = wrap_text(point, point_font, max_text_width)

        for line in lines[:2]:
            draw.text((text_x, point_y), line, font=point_font, fill=COLOR_WHITE)
            point_y += 40

        point_y += point_spacing - 80

    # Convert to bytes
    output = io.BytesIO()
    img.convert("RGB").save(output, format="PNG", quality=95)
    return output.getvalue()


# =============================================================================
# Main Render Function
# =============================================================================


def render_slide(slide: Dict[str, Any], gradient: str = DEFAULT_GRADIENT) -> bytes:
    """
    Render a slide based on its type.

    Args:
        slide: Slide definition dict with 'type' and content fields
        gradient: Gradient preset name

    Returns:
        PNG image as bytes

    Example slide formats:
        {"type": "title", "title": "Welcome", "subtitle": "Introduction"}
        {"type": "bullets", "title": "Key Points", "bullets": ["Point 1", "Point 2"]}
        {"type": "diagram", "title": "Flow", "elements": ["A", "→", "B"]}
        {"type": "summary", "title": "Summary", "key_points": ["Take 1", "Take 2"]}
    """
    slide_type = slide.get("type", "bullets")

    if slide_type == "title":
        return render_title_slide(
            title=slide.get("title", "Untitled"),
            subtitle=slide.get("subtitle", ""),
            gradient=gradient,
        )

    elif slide_type == "bullets":
        return render_bullets_slide(
            title=slide.get("title", ""),
            bullets=slide.get("bullets", []),
            gradient=gradient,
        )

    elif slide_type == "diagram":
        return render_diagram_slide(
            title=slide.get("title", ""),
            elements=slide.get("elements", []),
            gradient=gradient,
        )

    elif slide_type == "summary":
        return render_summary_slide(
            title=slide.get("title", "Resumo"),
            key_points=slide.get("key_points", slide.get("bullets", [])),
            gradient=gradient,
        )

    else:
        # Default to bullets
        return render_bullets_slide(
            title=slide.get("title", ""),
            bullets=slide.get("bullets", slide.get("content", [""])),
            gradient=gradient,
        )


def render_slides(
    slides: List[Dict[str, Any]],
    gradient: str = DEFAULT_GRADIENT,
) -> List[bytes]:
    """
    Render multiple slides.

    Args:
        slides: List of slide definitions
        gradient: Gradient preset name (applied to all)

    Returns:
        List of PNG images as bytes
    """
    return [render_slide(slide, gradient) for slide in slides]
