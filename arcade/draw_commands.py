"""
This module contains commands for basic graphics drawing commands.
(Drawing primitives.)

Many of these commands are slow, because they load everything to the
graphics card each time a shape is drawn. For faster drawing, see the
Buffered Draw Commands.
"""
from __future__ import annotations

import array
import math
from typing import Optional, Tuple, List

import PIL.Image
import PIL.ImageOps
import PIL.ImageDraw

import pyglet.gl as gl

from arcade.color import WHITE
from arcade.types import AsFloat, Color, RGBA255, PointList, Point, Point2List, Point2
from arcade.earclip import earclip
from arcade.types.rect import Rect, LBWH, LRBT, XYWH
from .math import rotate_point
from arcade import (
    Texture,
    get_window,
)

__all__ = [
    "draw_arc_filled",
    "draw_arc_outline",
    "draw_parabola_filled",
    "draw_parabola_outline",
    "draw_circle_filled",
    "draw_circle_outline",
    "draw_ellipse_filled",
    "draw_ellipse_outline",
    "draw_line_strip",
    "draw_line",
    "draw_lines",
    "draw_point",
    "draw_points",
    "draw_polygon_filled",
    "draw_polygon_outline",
    "draw_triangle_filled",
    "draw_triangle_outline",
    "draw_lrbt_rectangle_outline",
    "draw_lbwh_rectangle_outline",
    "draw_rect_outline",
    "draw_lrbt_rectangle_filled",
    "draw_lbwh_rectangle_filled",
    "draw_rect_filled",
    "draw_rect_outline_kwargs",
    "draw_rect_filled_kwargs",
    "draw_scaled_texture_rectangle",
    "draw_texture_rectangle",
    "draw_lbwh_rectangle_textured",
    "get_points_for_thick_line",
    "get_pixel",
    "get_image"
]


def get_points_for_thick_line(start_x: float, start_y: float,
                              end_x: float, end_y: float,
                              line_width: float) -> Tuple[Point2, Point2,
                                                          Point2, Point2]:
    """
    Function used internally for Arcade. OpenGL draws triangles only, so a thick
    line must be two triangles that make up a rectangle. This calculates and returns
    those points.
    """
    vector_x = start_x - end_x
    vector_y = start_y - end_y
    perpendicular_x = vector_y
    perpendicular_y = -vector_x
    length = math.sqrt(vector_x * vector_x + vector_y * vector_y)
    if length == 0:
        normal_x = 1.0
        normal_y = 1.0
    else:
        normal_x = perpendicular_x / length
        normal_y = perpendicular_y / length

    half_width = line_width / 2
    shift_x = normal_x * half_width
    shift_y = normal_y * half_width

    r1_x = start_x + shift_x
    r1_y = start_y + shift_y
    r2_x = start_x - shift_x
    r2_y = start_y - shift_y
    r3_x = end_x + shift_x
    r3_y = end_y + shift_y
    r4_x = end_x - shift_x
    r4_y = end_y - shift_y

    return (r1_x, r1_y), (r2_x, r2_y), (r4_x, r4_y), (r3_x, r3_y)


# --- BEGIN ARC FUNCTIONS # # #


def draw_arc_filled(center_x: float, center_y: float,
                    width: float, height: float,
                    color: RGBA255,
                    start_angle: float, end_angle: float,
                    tilt_angle: float = 0,
                    num_segments: int = 128):
    """
    Draw a filled in arc. Useful for drawing pie-wedges, or Pac-Man.

    :param center_x: x position that is the center of the arc.
    :param center_y: y position that is the center of the arc.
    :param width: width of the arc.
    :param height: height of the arc.
    :param color: A 3 or 4 length tuple of 0-255 channel values
        or a :py:class:`~arcade.types.Color` instance.
    :param start_angle: start angle of the arc in degrees.
    :param end_angle: end angle of the arc in degrees.
    :param tilt_angle: angle the arc is tilted (clockwise).
    :param num_segments: Number of line segments used to draw arc.
    """
    unrotated_point_list = [(0.0, 0.0)]

    start_segment = int(start_angle / 360 * num_segments)
    end_segment = int(end_angle / 360 * num_segments)

    for segment in range(start_segment, end_segment + 1):
        theta = 2.0 * 3.1415926 * segment / num_segments

        x = width * math.cos(theta) / 2
        y = height * math.sin(theta) / 2

        unrotated_point_list.append((x, y))

    if tilt_angle == 0:
        uncentered_point_list = unrotated_point_list
    else:
        uncentered_point_list = [rotate_point(point[0], point[1], 0, 0, tilt_angle) for point in unrotated_point_list]

    point_list = [(point[0] + center_x, point[1] + center_y) for point in uncentered_point_list]

    _generic_draw_line_strip(point_list, color, gl.GL_TRIANGLE_FAN)


def draw_arc_outline(center_x: float, center_y: float, width: float,
                     height: float, color: RGBA255,
                     start_angle: float, end_angle: float,
                     border_width: float = 1, tilt_angle: float = 0,
                     num_segments: int = 128):
    """
    Draw the outside edge of an arc. Useful for drawing curved lines.

    :param center_x: x position that is the center of the arc.
    :param center_y: y position that is the center of the arc.
    :param width: width of the arc.
    :param height: height of the arc.
    :param color: A 3 or 4 length tuple of 0-255 channel values
        or a :py:class:`~arcade.types.Color` instance.
    :param start_angle: start angle of the arc in degrees.
    :param end_angle: end angle of the arc in degrees.
    :param border_width: width of line in pixels.
    :param tilt_angle: angle the arc is tilted (clockwise).
    :param num_segments: float of triangle segments that make up this
         circle. Higher is better quality, but slower render time.
    """
    unrotated_point_list = []

    start_segment = int(start_angle / 360 * num_segments)
    end_segment = int(end_angle / 360 * num_segments)

    inside_width = (width - border_width / 2) / 2
    outside_width = (width + border_width / 2) / 2
    inside_height = (height - border_width / 2) / 2
    outside_height = (height + border_width / 2) / 2

    for segment in range(start_segment, end_segment + 1):
        theta = 2.0 * math.pi * segment / num_segments

        x1 = inside_width * math.cos(theta)
        y1 = inside_height * math.sin(theta)

        x2 = outside_width * math.cos(theta)
        y2 = outside_height * math.sin(theta)

        unrotated_point_list.append((x1, y1))
        unrotated_point_list.append((x2, y2))

    if tilt_angle == 0:
        uncentered_point_list = unrotated_point_list
    else:
        uncentered_point_list = [rotate_point(point[0], point[1], 0, 0, tilt_angle) for point in unrotated_point_list]

    point_list = [(point[0] + center_x, point[1] + center_y) for point in uncentered_point_list]

    _generic_draw_line_strip(point_list, color, gl.GL_TRIANGLE_STRIP)


# --- END ARC FUNCTIONS # # #


# --- BEGIN PARABOLA FUNCTIONS # # #

def draw_parabola_filled(start_x: float, start_y: float, end_x: float,
                         height: float, color: RGBA255,
                         tilt_angle: float = 0):
    """
    Draws a filled in parabola.

    :param start_x: The starting x position of the parabola
    :param start_y: The starting y position of the parabola
    :param end_x: The ending x position of the parabola
    :param height: The height of the parabola
    :param color: A 3 or 4 length tuple of 0-255 channel values
        or a :py:class:`~arcade.types.Color` instance.
    :param tilt_angle: The angle of the tilt of the parabola (clockwise)
    """
    center_x = (start_x + end_x) / 2
    center_y = start_y + height
    start_angle = 0
    end_angle = 180
    width = start_x - end_x
    draw_arc_filled(center_x, center_y, width, height, color,
                    start_angle, end_angle, tilt_angle)


def draw_parabola_outline(start_x: float, start_y: float, end_x: float,
                          height: float, color: RGBA255,
                          border_width: float = 1, tilt_angle: float = 0):
    """
    Draws the outline of a parabola.

    :param start_x: The starting x position of the parabola
    :param start_y: The starting y position of the parabola
    :param end_x: The ending x position of the parabola
    :param height: The height of the parabola
    :param color: A 3 or 4 length tuple of 0-255 channel values
        or a :py:class:`~arcade.types.Color` instance.
    :param border_width: The width of the parabola
    :param tilt_angle: The angle of the tilt of the parabola (clockwise)
    """
    center_x = (start_x + end_x) / 2
    center_y = start_y + height
    start_angle = 0
    end_angle = 180
    width = start_x - end_x
    draw_arc_outline(center_x, center_y, width, height, color,
                     start_angle, end_angle, border_width, tilt_angle)


# --- END PARABOLA FUNCTIONS # # #


# --- BEGIN CIRCLE FUNCTIONS # # #

def draw_circle_filled(center_x: float, center_y: float, radius: float,
                       color: RGBA255,
                       tilt_angle: float = 0,
                       num_segments: int = -1):
    """
    Draw a filled-in circle.

    :param center_x: x position that is the center of the circle.
    :param center_y: y position that is the center of the circle.
    :param radius: width of the circle.
    :param color: A 3 or 4 length tuple of 0-255 channel values
        or a :py:class:`~arcade.types.Color` instance.
    :param tilt_angle: Angle in degrees to tilt the circle. Useful for low segment count circles
    :param num_segments: Number of triangle segments that make up this
         circle. Higher is better quality, but slower render time.
         The default value of -1 means arcade will try to calculate a reasonable
         amount of segments based on the size of the circle.
    """
    draw_ellipse_filled(center_x, center_y, radius * 2, radius * 2, color,
                        tilt_angle=tilt_angle,
                        num_segments=num_segments)


def draw_circle_outline(center_x: float, center_y: float, radius: float,
                        color: RGBA255, border_width: float = 1,
                        tilt_angle: float = 0,
                        num_segments: int = -1):
    """
    Draw the outline of a circle.

    :param center_x: x position that is the center of the circle.
    :param center_y: y position that is the center of the circle.
    :param radius: width of the circle.
    :param color: A 3 or 4 length tuple of 0-255 channel values
        or a :py:class:`~arcade.types.Color` instance.
    :param border_width: Width of the circle outline in pixels.
    :param tilt_angle: Angle in degrees to tilt the circle (clockwise).
                             Useful for low segment count circles
    :param num_segments: Number of triangle segments that make up this
         circle. Higher is better quality, but slower render time.
         The default value of -1 means arcade will try to calculate a reasonable
         amount of segments based on the size of the circle.
    """
    draw_ellipse_outline(center_x=center_x, center_y=center_y,
                         width=radius * 2, height=radius * 2,
                         color=color,
                         border_width=border_width,
                         tilt_angle=tilt_angle,
                         num_segments=num_segments)

# --- END CIRCLE FUNCTIONS # # #


# --- BEGIN ELLIPSE FUNCTIONS # # #

def draw_ellipse_filled(center_x: float, center_y: float,
                        width: float, height: float, color: RGBA255,
                        tilt_angle: float = 0, num_segments: int = -1):
    """
    Draw a filled in ellipse.

    :param center_x: x position that is the center of the circle.
    :param center_y: y position that is the center of the circle.
    :param width: width of the ellipse.
    :param height: height of the ellipse.
    :param color: A 3 or 4 length tuple of 0-255 channel values
        or a :py:class:`~arcade.types.Color` instance.
    :param color: Either a :py:class:`~arcade.types.Color` instance
        or an RGBA :py:class:`tuple` of 4 byte values (0 to 255).
    :param tilt_angle: Angle in degrees to tilt the ellipse (clockwise).
         Useful when drawing a circle with a low segment count, to make an octagon for example.
    :param num_segments: Number of triangle segments that make up this
         circle. Higher is better quality, but slower render time.
         The default value of -1 means arcade will try to calculate a reasonable
         amount of segments based on the size of the circle.
    """
    # Fail immediately if we have no window or context
    window = get_window()
    ctx = window.ctx
    program = ctx.shape_ellipse_filled_unbuffered_program
    geometry = ctx.shape_ellipse_unbuffered_geometry
    buffer = ctx.shape_ellipse_unbuffered_buffer

    # Normalize the color because this shader takes a float uniform
    color_normalized = Color.from_iterable(color).normalized

    # Pass data to the shader
    program['color'] = color_normalized
    program['shape'] = width / 2, height / 2, tilt_angle
    program['segments'] = num_segments
    buffer.orphan()
    buffer.write(data=array.array('f', (center_x, center_y)))

    geometry.render(program, mode=gl.GL_POINTS, vertices=1)


def draw_ellipse_outline(center_x: float, center_y: float,
                         width: float,
                         height: float, color: RGBA255,
                         border_width: float = 1,
                         tilt_angle: float = 0,
                         num_segments: int = -1):
    """
    Draw the outline of an ellipse.

    :param center_x: x position that is the center of the circle.
    :param center_y: y position that is the center of the circle.
    :param width: width of the ellipse.
    :param height: height of the ellipse.
    :param color: A 3 or 4 length tuple of 0-255 channel values
        or a :py:class:`~arcade.types.Color` instance.
    :param border_width: Width of the circle outline in pixels.
    :param tilt_angle: Angle in degrees to tilt the ellipse (clockwise).
         Useful when drawing a circle with a low segment count, to make an octagon for example.
    :param num_segments: Number of triangle segments that make up this
         circle. Higher is better quality, but slower render time.
         The default value of -1 means arcade will try to calculate a reasonable
         amount of segments based on the size of the circle.
    """
    # Fail immediately if we have no window or context
    window = get_window()
    ctx = window.ctx
    program = ctx.shape_ellipse_outline_unbuffered_program
    geometry = ctx.shape_ellipse_outline_unbuffered_geometry
    buffer = ctx.shape_ellipse_outline_unbuffered_buffer

    # Normalize the color because this shader takes a float uniform
    color_normalized = Color.from_iterable(color).normalized

    # Pass data to shader
    program['color'] = color_normalized
    program['shape'] = width / 2, height / 2, tilt_angle, border_width
    program['segments'] = num_segments
    buffer.orphan()
    buffer.write(data=array.array('f', (center_x, center_y)))

    geometry.render(program, mode=gl.GL_POINTS, vertices=1)


# --- END ELLIPSE FUNCTIONS # # #


# --- BEGIN LINE FUNCTIONS # # #


def _generic_draw_line_strip(point_list: PointList,
                             color: RGBA255,
                             mode: int = gl.GL_LINE_STRIP):
    """
    Draw a line strip. A line strip is a set of continuously connected
    line segments.

    :param point_list: List of points making up the line. Each point is
         in a list. So it is a list of lists.
    :param color: A color, specified as an RGBA tuple or a
        :py:class:`~arcade.types.Color` instance.
    """
    # Fail if we don't have a window, context, or right GL abstractions
    window = get_window()
    ctx = window.ctx
    geometry = ctx.generic_draw_line_strip_geometry
    vertex_buffer = ctx.generic_draw_line_strip_vbo
    color_buffer = ctx.generic_draw_line_strip_color
    program = ctx.line_vertex_shader

    # Validate and alpha-pad color, then expand to multi-vertex form since
    # this shader normalizes internally as if made to draw multicolor lines.
    rgba = Color.from_iterable(color)
    num_vertices = len(point_list)  # Fail if it isn't a sized / sequence object

    # Translate Python objects into types arcade's Buffer objects accept
    color_array = array.array('B', rgba * num_vertices)
    vertex_array = array.array('f', tuple(item for sublist in point_list for item in sublist))
    geometry.num_vertices = num_vertices

    # Double buffer sizes until they can hold all our data
    goal_vertex_buffer_size = len(vertex_array) * 4
    while goal_vertex_buffer_size > vertex_buffer.size:
        vertex_buffer.orphan(color_buffer.size * 2)
        color_buffer.orphan(color_buffer.size * 2)
    else:
        vertex_buffer.orphan()
        color_buffer.orphan()

    # Write data & render
    vertex_buffer.write(vertex_array)
    color_buffer.write(color_array)
    geometry.render(program, mode=mode)


def draw_line_strip(point_list: PointList,
                    color: RGBA255, line_width: float = 1):
    """
    Draw a multi-point line.

    :param point_list: List of x, y points that make up this strip
    :param color: A color, specified as an RGBA tuple or a
        :py:class:`~arcade.types.Color` instance.
    :param line_width: Width of the line
    """
    if line_width == 1:
        _generic_draw_line_strip(point_list, color, gl.GL_LINE_STRIP)
    else:
        triangle_point_list: List[Point] = []
        # This needs a lot of improvement
        last_point = None
        for point in point_list:
            if last_point is not None:
                points = get_points_for_thick_line(last_point[0], last_point[1], point[0], point[1], line_width)
                reordered_points = points[1], points[0], points[2], points[3]
                triangle_point_list.extend(reordered_points)
            last_point = point
        _generic_draw_line_strip(triangle_point_list, color, gl.GL_TRIANGLE_STRIP)


def draw_line(start_x: float, start_y: float, end_x: float, end_y: float,
              color: RGBA255, line_width: float = 1):
    """
    Draw a line.

    :param start_x: x position of line starting point.
    :param start_y: y position of line starting point.
    :param end_x: x position of line ending point.
    :param end_y: y position of line ending point.
    :param color: A color, specified as an RGBA tuple or a
        :py:class:`~arcade.types.Color` instance.
    :param line_width: Width of the line in pixels.
    """
    # Fail if we don't have a window, context, or right GL abstractions
    window = get_window()
    ctx = window.ctx
    program = ctx.shape_line_program
    geometry = ctx.shape_line_geometry
    line_pos_buffer = ctx.shape_line_buffer_pos

    # Validate & normalize to a pass the shader an RGBA float uniform
    color_normalized = Color.from_iterable(color).normalized

    # Pass data to the shader
    program['color'] = color_normalized
    program['line_width'] = line_width
    line_pos_buffer.orphan()  # Allocate new buffer internally
    line_pos_buffer.write(
        data=array.array('f', (start_x, start_y, end_x, end_y)))

    geometry.render(program, mode=gl.GL_LINES, vertices=2)


def draw_lines(point_list: PointList,
               color: RGBA255,
               line_width: float = 1):
    """
    Draw a set of lines.

    Draw a line between each pair of points specified.

    :param point_list: List of points making up the lines. Each point is
         in a list. So it is a list of lists.
    :param color: A color, specified as an RGBA tuple or a
        :py:class:`~arcade.types.Color` instance.
    :param line_width: Width of the line in pixels.
    """
    # Fail if we don't have a window, context, or right GL abstractions
    window = get_window()
    ctx = window.ctx
    program = ctx.shape_line_program
    geometry = ctx.shape_line_geometry
    line_buffer_pos = ctx.shape_line_buffer_pos

    # Validate & normalize to a pass the shader an RGBA float uniform
    color_normalized = Color.from_iterable(color).normalized

    line_pos_array = array.array('f', (v for point in point_list for v in point))
    num_points = len(point_list)

    # Grow buffer until large enough to hold all our data
    goal_buffer_size = num_points * 3 * 4
    while goal_buffer_size > line_buffer_pos.size:
        ctx.shape_line_buffer_pos.orphan(line_buffer_pos.size * 2)
    else:
        ctx.shape_line_buffer_pos.orphan()

    # Pass data to shader
    program['line_width'] = line_width
    program['color'] = color_normalized
    line_buffer_pos.write(data=line_pos_array)

    geometry.render(program, mode=gl.GL_LINES, vertices=num_points)


# --- BEGIN POINT FUNCTIONS # # #


def draw_point(x: float, y: float, color: RGBA255, size: float):
    """
    Draw a point.

    :param x: x position of point.
    :param y: y position of point.
    :param color: A color, specified as an RGBA tuple or a
        :py:class:`~arcade.types.Color` instance.
    :param size: Size of the point in pixels.
    """
    draw_rect_filled(XYWH(x, y, size, size), color)


def draw_points(point_list: PointList, color: RGBA255, size: float = 1):
    """
    Draw a set of points.

    :param point_list: List of points Each point is
         in a list. So it is a list of lists.
    :param color: A color, specified as an RGBA tuple or a
        :py:class:`~arcade.types.Color` instance.
    :param size: Size of the point in pixels.
    """
    # Fails immediately if we don't have a window or context
    window = get_window()
    ctx = window.ctx
    program = ctx.shape_rectangle_filled_unbuffered_program
    geometry = ctx.shape_rectangle_filled_unbuffered_geometry
    buffer = ctx.shape_rectangle_filled_unbuffered_buffer

    # Validate & normalize to a pass the shader an RGBA float uniform
    color_normalized = Color.from_iterable(color).normalized

    # Get # of points and translate Python tuples to a C-style array
    num_points = len(point_list)
    point_array = array.array('f', (v for point in point_list for v in point))

    # Resize buffer
    data_size = num_points * 8
    # if data_size > buffer.size:
    buffer.orphan(size=data_size)

    # Pass data to shader
    program['color'] = color_normalized
    program['shape'] = size, size, 0
    buffer.write(data=point_array)

    # Only render the # of points we have complete data for
    geometry.render(program, mode=ctx.POINTS, vertices=data_size // 8)


# --- END POINT FUNCTIONS # # #

# --- BEGIN POLYGON FUNCTIONS # # #


def draw_polygon_filled(point_list: Point2List,
                        color: RGBA255):
    """
    Draw a polygon that is filled in.

    :param point_list: List of points making up the lines. Each point is
         in a list. So it is a list of lists.
    :param color: The color, specified in RGB or RGBA format.
    """
    triangle_points = earclip(point_list)
    flattened_list = tuple(i for g in triangle_points for i in g)
    _generic_draw_line_strip(flattened_list, color, gl.GL_TRIANGLES)


def draw_polygon_outline(point_list: Point2List,
                         color: RGBA255, line_width: float = 1):
    """
    Draw a polygon outline. Also known as a "line loop."

    :param point_list: List of points making up the lines. Each point is
         in a list. So it is a list of lists.
    :param color: The color of the outline as an RGBA :py:class:`tuple` or
        :py:class:`~arcade.types.Color` instance.
    :param line_width: Width of the line in pixels.
    """
    # Convert to modifiable list & close the loop
    new_point_list = list(point_list)
    new_point_list.append(point_list[0])

    # Create a place to store the triangles we'll use to thicken the line
    triangle_point_list = []

    # This needs a lot of improvement
    last_point = None
    for point in new_point_list:
        if last_point is not None:
            # Calculate triangles, then re-order to link up the quad?
            points = get_points_for_thick_line(*last_point, *point, line_width)
            reordered_points = points[1], points[0], points[2], points[3]

            triangle_point_list.extend(reordered_points)
        last_point = point

    # Use first two points of new list to close the loop
    new_start, new_next = new_point_list[:2]
    s_x, s_y = new_start
    n_x, n_y = new_next
    points = get_points_for_thick_line(s_x, s_y, n_x, n_y, line_width)
    triangle_point_list.append(points[1])

    _generic_draw_line_strip(triangle_point_list, color, gl.GL_TRIANGLE_STRIP)


def draw_triangle_filled(x1: float, y1: float,
                         x2: float, y2: float,
                         x3: float, y3: float, color: RGBA255):
    """
    Draw a filled in triangle.

    :param x1: x value of first coordinate.
    :param y1: y value of first coordinate.
    :param x2: x value of second coordinate.
    :param y2: y value of second coordinate.
    :param x3: x value of third coordinate.
    :param y3: y value of third coordinate.
    :param color: Color of the triangle as an RGBA :py:class:`tuple` or
        :py:class:`~arcade.types.Color` instance.
    """
    point_list = (
        (x1, y1),
        (x2, y2),
        (x3, y3),
    )
    _generic_draw_line_strip(point_list, color, gl.GL_TRIANGLES)


def draw_triangle_outline(x1: float, y1: float,
                          x2: float, y2: float,
                          x3: float, y3: float,
                          color: RGBA255,
                          border_width: float = 1):
    """
    Draw a the outline of a triangle.

    :param x1: x value of first coordinate.
    :param y1: y value of first coordinate.
    :param x2: x value of second coordinate.
    :param y2: y value of second coordinate.
    :param x3: x value of third coordinate.
    :param y3: y value of third coordinate.
    :param color: RGBA255 of triangle as an RGBA
        :py:class:`tuple` or :py:class`~arcade.types.Color` instance.
    :param border_width: Width of the border in pixels. Defaults to 1.
    """
    point_list = (
        (x1, y1),
        (x2, y2),
        (x3, y3),
    )
    draw_polygon_outline(point_list, color, border_width)


# --- END POLYGON FUNCTIONS # # #


# --- BEGIN RECTANGLE FUNCTIONS # # #

def draw_lrbt_rectangle_outline(left: float, right: float, bottom: float, top: float, color: RGBA255,
                                border_width: float = 1):
    """
    Draw a rectangle by specifying left, right, bottom and top edges.

    :param left: The x coordinate of the left edge of the rectangle.
    :param right: The x coordinate of the right edge of the rectangle.
    :param bottom: The y coordinate of the rectangle bottom.
    :param top: The y coordinate of the top of the rectangle.
    :param color: The color of the rectangle.
    :param border_width: The width of the border in pixels. Defaults to one.
    :Raises ValueError: Raised if left > right or top < bottom.

    """
    if left > right:
        raise ValueError("Left coordinate must be less than or equal to "
                         "the right coordinate")

    if bottom > top:
        raise ValueError("Bottom coordinate must be less than or equal to "
                         "the top coordinate")

    draw_rect_outline(LRBT(left, right, bottom, top), color,
                      border_width)


def draw_lbwh_rectangle_outline(left: float, bottom: float,
                                width: float, height: float,
                                color: RGBA255,
                                border_width: float = 1):
    """
    Draw a rectangle extending from bottom left to top right

    :param bottom_left_x: The x coordinate of the left edge of the rectangle.
    :param bottom_left_y: The y coordinate of the bottom of the rectangle.
    :param width: The width of the rectangle.
    :param height: The height of the rectangle.
    :param color: The color of the rectangle as an RGBA
        :py:class:`tuple` or :py:class`~arcade.types.Color` instance.
    :param border_width: The width of the border in pixels. Defaults to one.
    """

    draw_rect_outline(LBWH(left, bottom, width, height), color,
                      border_width)


def draw_lrbt_rectangle_filled(left: float, right: float, bottom: float, top: float, color: RGBA255):
    """
    Draw a rectangle by specifying left, right, bottom and top edges.

    :param left: The x coordinate of the left edge of the rectangle.
    :param right: The x coordinate of the right edge of the rectangle.
    :param bottom: The y coordinate of the rectangle bottom.
    :param top: The y coordinate of the top of the rectangle.
    :param color: The color of the rectangle.
    :Raises ValueError: Raised if left > right or top < bottom.
    """
    if left > right:
        raise ValueError(f"Left coordinate {left} must be less than or equal to the right coordinate {right}")

    if bottom > top:
        raise ValueError(f"Bottom coordinate {bottom} must be less than or equal to the top coordinate {top}")

    draw_rect_filled(LRBT(left, right, bottom, top), color)


def draw_lbwh_rectangle_filled(left: float, bottom: float,
                               width: float, height: float,
                               color: RGBA255):
    """
    Draw a filled rectangle extending from bottom left to top right

    :param left: The x coordinate of the left edge of the rectangle.
    :param bottom: The y coordinate of the bottom of the rectangle.
    :param width: The width of the rectangle.
    :param height: The height of the rectangle.
    :param color: The color of the rectangles an RGBA
        :py:class:`tuple` or :py:class`~arcade.types.Color` instance.
    """

    draw_rect_filled(LBWH(left, bottom, width, height), color)


def draw_scaled_texture_rectangle(center_x: float, center_y: float,
                                  texture: Texture,
                                  scale: float = 1.0,
                                  angle: float = 0,
                                  alpha: int = 255):
    """
    Draw a textured rectangle on-screen.

    .. warning:: This method can be slow!

                 Most users should consider using
                 :py:class:`arcade.Sprite` with
                 :py:class:`arcade.SpriteList` instead of this
                 function.

    OpenGL accelerates drawing by using batches to draw multiple things
    at once. This method doesn't do that.

    If you need finer control or less overhead than arcade allows,
    consider `pyglet's batching features
    <https://pyglet.readthedocs.io/en/master/modules/graphics/index.html#batches-and-groups>`_.

    :param center_x: x coordinate of rectangle center.
    :param center_y: y coordinate of rectangle center.
    :param texture: identifier of texture returned from
                        load_texture() call
    :param scale: scale of texture
    :param angle: rotation of the rectangle (clockwise). Defaults to zero.
    :param alpha: Transparency of image. 0 is fully transparent,
                        255 (default) is fully visible
    """
    texture.draw_scaled(center_x, center_y, scale, angle, alpha)


def draw_texture_rectangle(center_x: float, center_y: float,
                           width: float,
                           height: float,
                           texture: Texture,
                           angle: float = 0,
                           alpha: int = 255):
    """
    Draw a textured rectangle on-screen.

    :param center_x: x coordinate of rectangle center.
    :param center_y: y coordinate of rectangle center.
    :param width: width of texture
    :param height: height of texture
    :param texture: identifier of texture returned from load_texture() call
    :param angle: rotation of the rectangle. Defaults to zero (clockwise).
    :param alpha: Transparency of image. 0 is fully transparent, 255 (default) is visible
    """
    texture.draw_sized(center_x, center_y, width, height, angle, alpha)


def draw_lbwh_rectangle_textured(left: float, bottom: float,
                                 width: float,
                                 height: float,
                                 texture: Texture, angle: float = 0,
                                 alpha: int = 255):
    """
    Draw a texture extending from bottom left to top right.

    :param left: The x coordinate of the left edge of the rectangle.
    :param bottom: The y coordinate of the bottom of the rectangle.
    :param width: The width of the rectangle.
    :param height: The height of the rectangle.
    :param texture: identifier of texture returned from load_texture() call
    :param angle: rotation of the rectangle. Defaults to zero (clockwise).
    :param alpha: Transparency of image. 0 is fully transparent, 255 (default) is visible
    """

    center_x = left + (width / 2)
    center_y = bottom + (height / 2)
    texture.draw_sized(center_x, center_y, width, height, angle=angle, alpha=alpha)


# Reference implementations: drawing of new Rect

def draw_rect_outline(rect: Rect, color: RGBA255, border_width: float = 1, tilt_angle: float = 0):
    """
    Draw a rectangle outline.

    :param rect: The rectangle to draw.
        a :py:class`~arcade.types.Rect` instance.
    :param color: The color of the rectangle.
        :py:class:`tuple` or :py:class`~arcade.types.Color` instance.
    :param border_width: width of the lines, in pixels.
    :param tilt_angle: rotation of the rectangle. Defaults to zero (clockwise).
    """

    HALF_BORDER = border_width / 2

    i_lb = rect.bottom_left.x  + HALF_BORDER, rect.bottom_left.y   + HALF_BORDER
    i_rb = rect.bottom_right.x - HALF_BORDER, rect.bottom_right.y  + HALF_BORDER
    i_rt = rect.top_right.x    - HALF_BORDER, rect.top_right.y     - HALF_BORDER
    i_lt = rect.top_left.x     + HALF_BORDER, rect.top_left.y      - HALF_BORDER
    o_lb = rect.bottom_left.x  - HALF_BORDER, rect.bottom_left.y   - HALF_BORDER
    o_rb = rect.bottom_right.x + HALF_BORDER, rect.bottom_right.y  - HALF_BORDER
    o_rt = rect.top_right.x    + HALF_BORDER, rect.top_right.y     + HALF_BORDER
    o_lt = rect.top_left.x     - HALF_BORDER, rect.top_right.y     + HALF_BORDER

    point_list: PointList = (o_lt, i_lt, o_rt, i_rt, o_rb, i_rb, o_lb, i_lb, o_lt, i_lt)

    if tilt_angle != 0:
        point_list_2 = []
        for point in point_list:
            new_point = rotate_point(point[0], point[1], rect.x, rect.y, tilt_angle)
            point_list_2.append(new_point)
        point_list = point_list_2

    _generic_draw_line_strip(point_list, color, gl.GL_TRIANGLE_STRIP)


def draw_rect_filled(rect: Rect, color: RGBA255, tilt_angle: float = 0):
    """
    Draw a filled-in rectangle.

    :param rect: The rectangle to draw.
        a :py:class`~arcade.types.Rect` instance.
    :param color: The color of the rectangle as an RGBA
        :py:class:`tuple` or :py:class`~arcade.types.Color` instance.
    :param tilt_angle: rotation of the rectangle (clockwise). Defaults to zero.
    """
    # Fail if we don't have a window, context, or right GL abstractions
    window = get_window()
    ctx = window.ctx
    program = ctx.shape_rectangle_filled_unbuffered_program
    geometry = ctx.shape_rectangle_filled_unbuffered_geometry
    buffer = ctx.shape_rectangle_filled_unbuffered_buffer

    # Validate & normalize to a pass the shader an RGBA float uniform
    color_normalized = Color.from_iterable(color).normalized

    # Pass data to the shader
    program['color'] = color_normalized
    program['shape'] = rect.width, rect.height, tilt_angle
    buffer.orphan()
    buffer.write(data=array.array('f', (rect.x, rect.y)))

    geometry.render(program, mode=ctx.POINTS, vertices=1)


def draw_rect_outline_kwargs(color: RGBA255 = WHITE, border_width: int = 1, tilt_angle: float = 0, **kwargs: AsFloat):
    rect = Rect.from_kwargs(**kwargs)
    draw_rect_outline(rect, color, border_width, tilt_angle)


def draw_rect_filled_kwargs(color: RGBA255 = WHITE, tilt_angle: float = 0, **kwargs: AsFloat):
    rect = Rect.from_kwargs(**kwargs)
    draw_rect_filled(rect, color, tilt_angle)


# Get_ functions

def get_pixel(x: int, y: int, components: int = 3) -> Tuple[int, ...]:
    """
    Given an x, y, will return a color value of that point.

    :param x: x location
    :param y: y location
    :param components: Number of components to fetch. By default we fetch 3
        3 components (RGB). 4 components would be RGBA.

    """
    # noinspection PyCallingNonCallable,PyTypeChecker

    # The window may be 'scaled' on hi-res displays. Particularly Macs. OpenGL
    # won't account for this, so we need to.
    window = get_window()

    pixel_ratio = window.get_pixel_ratio()
    x = int(pixel_ratio * x)
    y = int(pixel_ratio * y)

    a = (gl.GLubyte * 4)(0)
    gl.glReadPixels(x, y, 1, 1, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, a)
    return tuple(int(i) for i in a[:components])


def get_image(x: int = 0, y: int = 0, width: Optional[int] = None, height: Optional[int] = None) -> PIL.Image.Image:
    """
    Get an image from the screen.

    Example::

        image = get_image()
        image.save('screenshot.png', 'PNG')

    :param x: Start (left) x location
    :param y: Start (top) y location
    :param width: Width of image. Leave blank for grabbing the 'rest' of the image
    :param height: Height of image. Leave blank for grabbing the 'rest' of the image
    :returns: A Pillow Image
    """
    window = get_window()

    pixel_ratio = window.get_pixel_ratio()
    x = int(pixel_ratio * x)
    y = int(pixel_ratio * y)

    if width is None:
        width = window.width - x
    if height is None:
        height = window.height - y

    width = int(pixel_ratio * width)
    height = int(pixel_ratio * height)

    # Create an image buffer
    # noinspection PyTypeChecker
    image_buffer = (gl.GLubyte * (4 * width * height))(0)

    gl.glReadPixels(x, y, width, height, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, image_buffer)
    image = PIL.Image.frombytes("RGBA", (width, height), image_buffer)
    image = PIL.ImageOps.flip(image)

    return image
