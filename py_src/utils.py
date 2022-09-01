import logging
from typing import List, Union, Tuple, Dict
from pathlib import Path
from PIL import Image, ImageDraw

from GUI_utils import Node

logger = logging.getLogger(__name__)


def convert_bounds(bounds_str: str) -> Tuple[int, ...]:
    return tuple(
        [int(x) for x in
         bounds_str
             .replace('][', ',')
             .replace(']', '')
             .replace('[', '')
             .split(',')])


def dashed_line(draw, bound, width=1, fill=None, scale=5):
    dx = scale if bound[2] > bound[0] else -scale
    dy = scale if bound[3] > bound[1] else -scale
    if bound[0] == bound[2]:
        for y in range(bound[1], bound[3], dy * 2):
            draw.line((bound[0], y, bound[2], y + dy), width=width, fill=fill)
    elif bound[1] == bound[3]:
        for x in range(bound[0], bound[2], dx * 2):
            draw.line((x, bound[1], x + dx, bound[3]), width=width, fill=fill)
    else:
        for x in range(bound[0], bound[2], dx * 2):
            for y in range(bound[1], bound[3], dy * 2):
                draw.line((x, y, x + dx, y + dy), width=width, fill=fill)


def dashed_rectangle(draw, bound, fill=None, outline=None, width=1, scale=5):
    dashed_line(draw, (bound[0], bound[1], bound[0], bound[3]), width=width, fill=outline, scale=scale)
    dashed_line(draw, (bound[0], bound[3], bound[2], bound[3]), width=width, fill=outline, scale=scale)
    dashed_line(draw, (bound[2], bound[3], bound[2], bound[1]), width=width, fill=outline, scale=scale)
    dashed_line(draw, (bound[2], bound[1], bound[0], bound[1]), width=width, fill=outline, scale=scale)


def annotate_rectangle(source_img,
                       target_img,
                       bounds: List[Tuple],
                       outline: Union[List, Tuple] = None,
                       width: Union[List, int] = 10,
                       scale: Union[List, int] = 5) -> Image:
    if isinstance(outline, list):
        if len(outline) != len(bounds):
            logger.error(
                f"The bounds and outline should be the same size. bounds: {len(bounds)}, outline: {len(outline)}")
            return
    else:
        outline = [outline] * len(bounds)

    if isinstance(width, list):
        if len(width) != len(bounds):
            logger.error(f"The bounds and width should be the same size. bounds: {len(width)}, outline: {len(outline)}")
            return
    else:
        width = [width] * len(bounds)

    if isinstance(scale, list):
        if len(scale) != len(bounds):
            logger.error(f"The bounds and scale should be the same size. bounds: {len(scale)}, outline: {len(outline)}")
            return
    else:
        scale = [scale] * len(bounds)

    try:
        im = Image.open(source_img)
        draw = ImageDraw.Draw(im)
        # draw.rectangle(reg_result.bound, fill=(255, 255, 0, 20), outline=(100, 100, 100))
        for bound, o, w, s in zip(bounds, outline, width, scale):
            new_bound = (min(bound[0], bound[2]),
                         min(bound[1], bound[3]),
                         max(bound[0], bound[2]),
                         max(bound[1], bound[3]))
            dashed_rectangle(draw, new_bound, outline=o, width=w, scale=s)
        if target_img is not None:
            im.save(target_img, quality=95)
        return im
    except Exception as e:
        logger.error(f"A problem with image annotation, Exception: {e}")
    return None


def annotate_elements(source_img: Union[str, Path],
                      target_img: Union[str, Path],
                      elements: List[Union[Node, dict]],
                      outline: Tuple = None,
                      width: int = 5,
                      scale: int = 5):
    if isinstance(target_img, str):
        target_img = Path(target_img)
    bounds_list = []
    outlines = []
    widths = []
    scales = []
    for node in elements:
        if node is None:
            logger.debug(f"The bounds of element {node} is empty!")
            continue
        if isinstance(node, dict):
            node = Node.createNodeFromDict(node)
        bounds = node.bounds
        class_name = node.class_name
        # else:
        #     bounds = convert_bounds(node['bounds'])
        #     class_name = node['class_name']
        bounds_list.append(bounds)
        if outline is not None:
            outlines.append(outline)  # sandybrown
            widths.append(width)
            scales.append(scale)
        elif class_name == 'android.widget.ImageView':
            outlines.append((244, 164, 96))  # sandybrown
            widths.append(10)
            scales.append(scale)
        elif class_name == 'android.widget.TextView':
            outlines.append((144, 238, 144))  # lightgreen
            widths.append(10)
            scales.append(scale)
        elif class_name.endswith('Button'):
            outlines.append((220, 20, 60))  # Crimson
            widths.append(10)
            scales.append(scale)
        else:
            outlines.append((0, 139, 139))
            widths.append(width)
            scales.append(scale)

    annotate_rectangle(source_img=source_img,
                       target_img=target_img,
                       bounds=bounds_list,
                       outline=outlines,
                       width=widths,
                       scale=scales)


def create_gif(source_images: List[Union[str, Path]],
               target_gif: Union[str, Path],
               image_to_nodes: Dict[str, List[Union[Node, dict]]],
               outline: Tuple[int, int, int] = (144, 238, 144),
               width: int = 10,
               scale: int = 5):
    images = []
    for src_image in source_images:
        if isinstance(src_image, Path):
            src_image = src_image.resolve()
        if src_image not in image_to_nodes:
            images.append(Image.open(src_image))
        else:
            for node in image_to_nodes[src_image]:
                if node is None:
                    logger.debug(f"The bounds of element {node} is empty!")
                    continue
                if isinstance(node, dict):
                    node = Node.createNodeFromDict(node)
                bounds = node.bounds
                img = annotate_rectangle(source_img=src_image,
                                         target_img=None,
                                         bounds=[bounds],
                                         outline=outline,
                                         width=width,
                                         scale=scale)
                images.append(img)
    images[0].save(target_gif, save_all=True, append_images=images[1:], optimize=False, duration=300, loop=0)
