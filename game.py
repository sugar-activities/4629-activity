# -*- coding: utf-8 -*-
#Copyright (c) 2011-12 Walter Bender
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, 51 Franklin Street, Suite 500 Boston, MA 02110-1335 USA


from gi.repository import Gtk, GdkPixbuf, GObject, Gdk
import cairo
import os
from random import uniform

from gettext import gettext as _

import logging
_logger = logging.getLogger('reflection-activity')

from sugar3.graphics import style
GRID_CELL_SIZE = style.GRID_CELL_SIZE

from sprites import Sprites, Sprite


ACCELEROMETER_DEVICE = '/sys/devices/platform/lis3lv02d/position'


def read_accelerometer(game):
    if not hasattr(read_accelerometer, 'device_path'):
        if os.path.exists(ACCELEROMETER_DEVICE):
            read_accelerometer.device_path = ACCELEROMETER_DEVICE
        else:
            read_accelerometer.device_path = None
    if read_accelerometer.device_path is None:
        x = int(uniform(-20, 20))
        y = int(uniform(-20, 20))
        z = int(uniform(-20, 20))
    else:
        fh = open(ACCELEROMETER_DEVICE)
        string = fh.read()
        xyz = string[1:-2].split(',')
        x = int(float(xyz[0]) / 18)
        y = int(float(xyz[1]) / 18)
        z = int(float(xyz[2]) / 18)
        fh.close()
    game.motion_cb(x, y, z)


# Grid dimensions must be even
NINE = 9
FIVE = 5
DOT_SIZE = 40
YELLOW = 8
RED = 4
BLUE = 12
WHITE = 2
BLACK = 3
DOT = 0

class Game():

    def __init__(self, canvas, parent=None, colors=['#A0FFA0', '#FF8080']):
        self._activity = parent
        self._colors = [colors[0]]
        self._colors.append(colors[1])
        self._colors.append('#FFFFFF')
        self._colors.append('#000000')

        self._colors.append('#FF0000')
        self._colors.append('#FF8080')
        self._colors.append('#FFa0a0')
        self._colors.append('#FFc0c0')

        self._colors.append('#FFFF00')
        self._colors.append('#FFFF80')
        self._colors.append('#FFFFa0')
        self._colors.append('#FFFFe0')

        self._colors.append('#0000FF')
        self._colors.append('#8080FF')
        self._colors.append('#80a0FF')
        self._colors.append('#c0c0FF')

        self._canvas = canvas
        if parent is not None:
            parent.show_all()
            self._parent = parent

        self._canvas.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self._canvas.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
        self._canvas.connect("draw", self.__draw_cb)
        self._canvas.connect("button-press-event", self._button_press_cb)
        self._canvas.connect("button-release-event", self._button_release_cb)
        self._global_scale = 1
        self._width = Gdk.Screen.width()
        self._height = Gdk.Screen.height() - (GRID_CELL_SIZE * 1.5)
        self._scale = self._width / (10 * DOT_SIZE * 1.2)
        self._dot_size = int(DOT_SIZE * self._scale)
        self._space = int(self._dot_size / 5.)
        self._press = False
        self._release = None
        self._rubbing = False
        self._tapped = None
        self._pausing = False
        self._count = 0
        self._targets = None  # click target
        self._shake = None  # accelerometer target
        self._next = None
        self.last_spr = None
        self._timer = None
        self.roygbiv = False

        # Generate the sprites we'll need...
        self._sprites = Sprites(self._canvas)

        self._svg_width = self._width
        self._svg_height = self._height
        self._lightbg = Sprite(self._sprites, 0, 0,
                            svg_str_to_pixbuf(
                self._header() + \
                self._rect(self._width, self._height, 0, 0) + \
                self._footer()))
        self._lightbg.set_label_attributes(24)
        self._lightbg._vert_align = ["bottom"]

        self._darkbg = Sprite(self._sprites, 0, 0,
                              svg_str_to_pixbuf(
                self._header() + \
                self._rect(self._width, self._height, 0, 0, color='#000000') + \
                self._footer()))
        self._darkbg.set_label_attributes(24)
        self._darkbg._vert_align = ["bottom"]
        self._darkbg.set_label_color('yellow')
        self._darkbg.set_layer(0)

        self._dots = []
        for y in range(FIVE):
            for x in range(NINE):
                xoffset = int((self._width - NINE * self._dot_size - \
                                   (NINE - 1) * self._space) / 2.)
                self._dots.append(
                    Sprite(self._sprites,
                           xoffset + x * (self._dot_size + self._space),
                           y * (self._dot_size + self._space),
                           self._new_dot(self._colors[WHITE])))
                self._dots[-1].type = DOT
                self._dots[-1].set_label_attributes(40)

        n = FIVE / 2.

        # and initialize a few variables we'll need.
        self._yellow_dot()

    def _clear_pause(self):
        self._pausing = False
        if self._rubbing and self._release is not None:
            if self._next is not None:
                self._next()

    def _yellow_dot(self):
        for y in range(FIVE):
            for x in range(NINE):
                xoffset = int((self._width - NINE * self._dot_size - \
                                   (NINE - 1) * self._space) / 2.)
                self._dots[x + y * NINE].move((
                           xoffset + x * (self._dot_size + self._space),
                           y * (self._dot_size + self._space)))
                self._dots[x + y * NINE].set_shape(
                    self._new_dot(self._colors[WHITE]))
                self._dots[x + y * NINE].type = DOT
                self._dots[x + y * NINE].set_layer(100)
        self._lightbg.set_label(_('Tap on the yellow dot.'))
        self._targets = [int(uniform(0, NINE * FIVE))]
        self._next = self._yellow_dot_too
        self._dots[self._targets[0]].set_shape(
            self._new_dot(self._colors[YELLOW]))
        self._dots[self._targets[0]].type = YELLOW
        self._rubbing = False
        self._shake = None

    def _yellow_dot_too(self, append=True):
        ''' Things to reinitialize when starting up a new game. '''
        if append:
            i = self._targets[0]
            while i in self._targets:
                i = int(uniform(0, NINE * FIVE))
            self._targets.append(i)
            self._lightbg.set_label(_('Well done! \
Now tap on the other yellow dot.'))
        self._next = self._yellow_dots_three
        self._dots[self._targets[1]].set_shape(
            self._new_dot(self._colors[YELLOW]))
        self._dots[self._targets[1]].type = YELLOW
        self._rubbing = False

    def _yellow_dots_three(self):
        ''' Things to reinitialize when starting up a new game. '''
        if self._release == self._targets[0]:
            self._yellow_dot_too(append=False)
            self._lightbg.set_label(_('The other yellow dot!'))
            return
        i = self._targets[0]
        while i in self._targets:
            i = int(uniform(0, NINE * FIVE))
        self._targets.append(i)
        self._lightbg.set_label(_('Great! Now rub on one of the yellow dots.'))
        self._next = self._red_dot
        self._dots[self._targets[2]].set_shape(
            self._new_dot(self._colors[YELLOW]))
        self._dots[self._targets[2]].type = YELLOW
        self._rubbing = True

    def _red_dot(self):
        if self._release is None:
            return
        self._lightbg.set_label(_('Good job! \
Now rub on another one of the yellow dots.'))
        self._next = self._blue_dot
        self._dots[self._release].set_shape(self._new_dot(self._colors[RED]))
        self._dots[self._release].type = RED
        self._rubbing = True

    def _blue_dot(self):
        if self._release is None:
            return
        if self._dots[self._release].type != YELLOW:
            return
        self._lightbg.set_label(
            _('Now gently tap on the yellow dot five times.'))
        self._next = self._yellow_tap
        self._dots[self._release].set_shape(self._new_dot(self._colors[BLUE]))
        self._dots[self._release].type = BLUE
        self._rubbing = False
        self._count = 0

    def _yellow_tap(self):
        if self._dots[self._release].type != YELLOW:
            if self._count == 0:
                self._lightbg.set_label(
                    _('Now gently tap on the yellow dot five times.'))
            else:
                self._lightbg.set_label(_('Tap on a yellow dot.'))
            return
        self._count += 1
        if self._count > 4:
            self._count = 0
            self._next = self._red_tap
            self._lightbg.set_label(
                _('Now gently tap on the red dot five times.'))
        else:
            self._lightbg.set_label(_('Keep tapping.'))
        i = self._targets[0]
        while i in self._targets:
            i = int(uniform(0, NINE * FIVE))
        self._targets.append(i)
        self._dots[i].set_shape(self._new_dot(self._colors[YELLOW]))
        self._dots[i].type = YELLOW

    def _red_tap(self):
        if self._dots[self._release].type != RED:
            if self._count == 0:
                self._lightbg.set_label(
                _('Now gently tap on the red dot five times.'))
            else:
                self._lightbg.set_label(_('Tap on a red dot.'))
            return
        self._count += 1
        if self._count > 4:
            self._count = 0
            self._next = self._blue_tap
            self._lightbg.set_label(
                _('Now gently tap on the blue dot five times.'))
        else:
            self._lightbg.set_label(_('Keep tapping.'))
        i = self._targets[0]
        while i in self._targets:
            i = int(uniform(0, NINE * FIVE))
        self._targets.append(i)
        self._dots[i].set_shape(self._new_dot(self._colors[RED]))
        self._dots[i].type = RED

    def _blue_tap(self):
        if self._dots[self._release].type != BLUE:
            if self._count == 0:
                self._lightbg.set_label(
                _('Now gently tap on the blue dot five times.'))
            else:
                self._lightbg.set_label(_('Tap on a blue dot.'))
            return
        self._count += 1
        if self._count > 4:
            self._count = 0
            self._next = self._shake_it
            self._lightbg.set_label('')
            # Since we don't end up in the button press
            GObject.timeout_add(500, self._next)
        else:
            self._lightbg.set_label(_('Keep tapping.'))
        i = self._targets[0]
        while i in self._targets:
            i = int(uniform(0, NINE * FIVE))
        self._targets.append(i)
        self._dots[i].set_shape(self._new_dot(self._colors[BLUE]))
        self._dots[i].type = BLUE

    def _shake_it(self):
        self._lightbg.set_label(_('OK. Now, shake the computer!!'))
        for dot in self._dots:
            if dot.type in [RED, YELLOW, BLUE]:
                dot.set_layer(200)
        self._next = self._shake_it_more
        self._shake = 'random'
        self._pausing = True
        GObject.timeout_add(5000, self._clear_pause)
        GObject.timeout_add(100, read_accelerometer, self)

    def _shake_it_more(self):
        self._lightbg.set_label(_('Shake it harder!!'))
        self._next = self._turn_left
        self._shake = 'random2'
        self._pausing = True
        GObject.timeout_add(5000, self._clear_pause)

    def _turn_left(self):
        self._lightbg.set_label(
            _('See what happens if you turn it to the left.'))
        self._next = self._turn_right
        self._shake = 'left'
        self._pausing = True

    def _turn_right(self):
        self._lightbg.set_label(_('Now turn it to the right.'))
        self._next = self._align
        self._pausing = True
        self._shake = 'right'

    def _align(self):
        self._lightbg.set_label(_('Shake it some more.'))
        self._next = self._tap_six
        self._pausing = True
        self._shake = 'align'

    def _tap_six(self):
        self._shake = None
        self._lightbg.set_label(_('OK. Now press each of the yellow dots.'))
        if self._tapped == None:
            self._tapped = []
        if self._dots[self._release].type != YELLOW:
            self._lightbg.set_label(_('Press the yellow dots.'))
            return
        else:
            if not self._release in self._tapped:
                self._tapped.append(self._release)
                self._dots[self._release].set_label(':)')
        if len(self._tapped) == 6:
            self._darkbg.set_layer(100)
            self._lightbg.set_layer(0)
            for dot in self._dots:
                if dot.type != YELLOW:
                    dot.set_layer(0)
            self._darkbg.set_label(_('Press all of the yellow dots again!'))
            self._tapped = None
            self._next = self._tap_six_too

    def _tap_six_too(self):
        self._shake = None
        if self._tapped == None:
            self._tapped = []
        if self._dots[self._release].type != YELLOW:
            return
        else:
            if not self._release in self._tapped:
                self._tapped.append(self._release)
                self._dots[self._release].set_label('')
        if len(self._tapped) == 6:
            self._lightbg.set_layer(100)
            self._darkbg.set_layer(0)
            for dot in self._dots:
                if dot.type in [RED, BLUE]:
                    dot.set_layer(100)
            pos1 = self._dots[self._targets[1]].get_xy()
            pos2 = self._dots[self._targets[2]].get_xy()
            self._dots[self._targets[1]].move(pos2)
            self._dots[self._targets[2]].move(pos1)
            self._lightbg.set_label(
                _('Tap on the two dots that switched positions.'))
            self._tapped = None
            self._next = self._tap_two

    def _tap_two(self):
        self._shake = None
        if self._tapped == None:
            self._tapped = []
        if not self._release in [self._targets[1], self._targets[2]]:
            self._lightbg.set_label(_('Keep trying.'))
            return
        else:
            if not self._release in self._tapped:
                self._tapped.append(self._release)
                self._dots[self._release].set_label(':)')
        if len(self._tapped) == 2:
            pos1 = self._dots[self._targets[1]].get_xy()
            pos2 = self._dots[self._targets[2]].get_xy()
            self._dots[self._targets[1]].move(pos2)
            self._dots[self._targets[2]].move(pos1)
            self._lightbg.set_label(_("Good job! Now let's shake again."))
            self._shake = 'random2'
            self._next = self._shake_three
            # Since we don't end up in the button press
            GObject.timeout_add(500, self._next)
            for i in self._tapped:
                self._dots[i].set_label('')
        elif len(self._tapped) == 1:
            self._lightbg.set_label(_('You found one. Now find the other one.'))

    def _shake_three(self):
        self._next = self._fade_it
        self._shake = 'random2'
        GObject.timeout_add(100, read_accelerometer, self)
        self._pausing = True
        GObject.timeout_add(2000, self._clear_pause)

    def _fade_it(self):
        for dot in self._dots:
            if dot.type in [RED, YELLOW, BLUE]:
                self._fade_dot(dot, 1)
        self._lightbg.set_label(_('Going'))
        self._shake = 'random2'
        self._next = self._fade_it_again
        self._pausing = True
        GObject.timeout_add(2000, self._clear_pause)

    def _fade_it_again(self):
        for dot in self._dots:
            if dot.type in [RED, YELLOW, BLUE]:
                self._fade_dot(dot, 2)
        self._lightbg.set_label(_('Going') + '..')
        self._shake = 'random2'
        self._next = self._and_again
        self._pausing = True
        GObject.timeout_add(2000, self._clear_pause)

    def _and_again(self):
        for dot in self._dots:
            if dot.type in [RED, YELLOW, BLUE]:
                self._fade_dot(dot, 3)
        self._lightbg.set_label(_('Going') + '...')
        self._shake = 'random2'
        self._next = self._one_last_time
        self._pausing = True
        GObject.timeout_add(2000, self._clear_pause)

    def _one_last_time(self):
        for dot in self._dots:
            if dot.type in [RED, YELLOW, BLUE]:
                self._fade_dot(dot, 4)
        self._lightbg.set_label(_('Gone!'))
        self._shake = None
        self._next = self._yellow_dot
        GObject.timeout_add(500, self._next)

    def _fade_dot(self, dot, i):
        if i == 4:
            dot.set_shape(self._new_dot(self._colors[WHITE]))
        else:
            dot.set_shape(self._new_dot(self._colors[dot.type + i]))

    def _set_label(self, string):
        ''' Set the label in the toolbar or the window frame. '''
        self._activity.status.set_label(string)

    def motion_cb(self, x, y, z):
        if read_accelerometer.device_path is None:
            jiggle_factor = 5
        else:
            jiggle_factor = 3
        if self._shake is None:
            return
        elif self._shake in ['random', 'random2']:
            if self._shake == 'random2':
                jiggle_factor *= 2
            for dot in self._dots:
                if dot.type in [RED, YELLOW, BLUE]:
                    x += int(uniform(-jiggle_factor, jiggle_factor))
                    z += int(uniform(-jiggle_factor, jiggle_factor))
                    # Randomize z drift, which tends toward up...
                    if int(uniform(0, 2)) == 0:
                        z = -z
                    dot.move_relative((x, z))
        elif self._shake == 'align':
            docked = True
            yellow = 0
            red = 0
            blue = 0
            for dot in self._dots:
                if dot.type == YELLOW:
                    docked = self._dock_dot(dot, yellow + 1, 1, jiggle_factor,
                                            docked)
                    yellow += 1
                elif dot.type == RED:
                    docked = self._dock_dot(dot, red + 2, 2, jiggle_factor,
                                            docked)
                    red += 1
                elif dot.type == BLUE:
                    docked = self._dock_dot(dot, blue + 3, 3, jiggle_factor,
                                            docked)
                    blue += 1
            if docked:
                self._lightbg.set_label(_('Interesting.'))
                self._pausing = False
        elif self._shake == 'left':
            right = False
            for dot in self._dots:
                if dot.type in [RED, YELLOW, BLUE]:
                    pos = dot.get_xy()
                    if pos[0] < 0:
                        if pos[1] > self._height:
                            z = int(uniform(-20, 0))
                        elif pos[1] < 0:
                            z = int(uniform(0, 20))
                        x = int(uniform(0, 10))
                        dot.move_relative((x, z))
                    elif x < 0:
                        x += int(uniform(-10, 0))
                        if pos[1] > self._height:
                            z = int(uniform(-20, 0))
                        elif pos[1] < 0:
                            z = int(uniform(0, 20))
                        if pos[0] > -x:
                            dot.move_relative((x, z))
                    pos = dot.get_xy()
                    if pos[0] > 100:
                        right = True
            if not right:
                self._lightbg.set_label(_('Hmm'))
                self._pausing = False
        elif self._shake == 'right':
            left = False
            for dot in self._dots:
                if dot.type in [RED, YELLOW, BLUE]:
                    pos = dot.get_xy()
                    if pos[0] > self._width - self._dot_size:
                        if pos[1] > self._height:
                            z = int(uniform(-20, 0))
                        elif pos[1] < 0:
                            z = int(uniform(0, 20))
                        x = int(uniform(-10, 0))
                        dot.move_relative((x, z))
                    elif x < self._width - self._dot_size:
                        x += int(uniform(0, 10))
                        if pos[1] > self._height:
                            z = int(uniform(-20, 0))
                        elif pos[1] < 0:
                            z = int(uniform(0, 20))
                        if pos[0] < self._width - x - self._dot_size:
                            dot.move_relative((x, z))
                    pos = dot.get_xy()
                    if pos[0] < self._width - self._dot_size - 100:
                        left = True
            if not left:
                self._lightbg.set_label(_('Hmm'))
                self._pausing = False
        if not self._pausing:
            if self._next is not None:
                GObject.timeout_add(1000, self._next)
            else:
                self._lightbg.set_label('')
                self._shake = None
        GObject.timeout_add(100, read_accelerometer, self)
        return

    def _dock_dot(self, dot, n, m, jiggle_factor, docked):
        x = (self._dot_size + self._space) * n
        y = (self._dot_size + self._space) * m
        pos = dot.get_xy()
        dx = x - pos[0]
        dy = y - pos[1]
        if abs(dx) < 11 and abs(dy) < 11:
            dot.move((x, y))
            return docked
        else:
            if dx < 0:
                dx = max(-10, dx)
            elif dx > 0:
                dx = min(10, dx)
            if dy < 0:
                dy = max(-10, dy)
            elif dy > 0:
                dy = min(10, dy)
            dx += int(uniform(-jiggle_factor, jiggle_factor))
            dy += int(uniform(-jiggle_factor, jiggle_factor))
            dot.move_relative((dx, dy))
            return False

    def _button_press_cb(self, win, event):
        if self._shake is not None:
            return True
        win.grab_focus()
        x, y = map(int, event.get_coords())
        self._press = True
        self._release = None

        spr = self._sprites.find_sprite((x, y))
        if spr == None:
            return True

        self.last_spr = spr
        if self._rubbing:
            self._pausing = True
            if spr in self._dots:
                for target in self._targets:
                    if self._dots.index(spr) == target:
                        self._release = target
            GObject.timeout_add(1000, self._clear_pause)
        return True

    def _button_release_cb(self, win, event):
        if self._shake is not None:
            return True
        self._press = False
        self._release = None

        if self._pausing:
            self._lightbg.set_label(_('Rub a little longer.'))
            return True

        x, y = map(int, event.get_coords())
        spr = self._sprites.find_sprite((x, y))
        if spr.type is not None:
            if spr in self._dots:
                for target in self._targets:
                    if self._dots.index(spr) == target:
                        self._release = target
                        if self._next is not None:
                            GObject.timeout_add(200, self._next)

    def _smile(self):
        for dot in self._dots:
            dot.set_label(':)')

    def __draw_cb(self, canvas, cr):
        self._sprites.redraw_sprites(cr=cr)

    def _grid_to_dot(self, pos):
        ''' calculate the dot index from a column and row in the grid '''
        return pos[0] + pos[1] * NINE

    def _dot_to_grid(self, dot):
        ''' calculate the grid column and row for a dot '''
        return [dot % NINE, int(dot / NINE)]

    def _destroy_cb(self, win, event):
        Gtk.main_quit()

    def _new_dot(self, color):
        ''' generate a dot of a color color '''
        self._dot_cache = {}
        if not color in self._dot_cache:
            self._stroke = color
            self._fill = color
            self._svg_width = self._dot_size
            self._svg_height = self._dot_size
            pixbuf = svg_str_to_pixbuf(
                self._header() + \
                self._circle(self._dot_size / 2., self._dot_size / 2.,
                             self._dot_size / 2.) + \
                self._footer())

            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                         self._svg_width, self._svg_height)
            context = cairo.Context(surface)
            Gdk.cairo_set_source_pixbuf(context, pixbuf, 0, 0)
            context.rectangle(0, 0, self._svg_width, self._svg_height)
            context.fill()
            self._dot_cache[color] = surface

        return self._dot_cache[color]

    def _line(self, vertical=True):
        ''' Generate a center line '''
        if vertical:
            self._svg_width = 3
            self._svg_height = self._height
            return svg_str_to_pixbuf(
                self._header() + \
                self._rect(3, self._height, 0, 0) + \
                self._footer())
        else:
            self._svg_width = self._width
            self._svg_height = 3
            return svg_str_to_pixbuf(
                self._header() + \
                self._rect(self._width, 3, 0, 0) + \
                self._footer())

    def _header(self):
        return '<svg\n' + 'xmlns:svg="http://www.w3.org/2000/svg"\n' + \
            'xmlns="http://www.w3.org/2000/svg"\n' + \
            'xmlns:xlink="http://www.w3.org/1999/xlink"\n' + \
            'version="1.1"\n' + 'width="' + str(self._svg_width) + '"\n' + \
            'height="' + str(self._svg_height) + '">\n'

    def _rect(self, w, h, x, y, color='#ffffff'):
        svg_string = '       <rect\n'
        svg_string += '          width="%f"\n' % (w)
        svg_string += '          height="%f"\n' % (h)
        svg_string += '          rx="%f"\n' % (0)
        svg_string += '          ry="%f"\n' % (0)
        svg_string += '          x="%f"\n' % (x)
        svg_string += '          y="%f"\n' % (y)
        svg_string += 'style="fill:%s;stroke:none;"/>\n' % (color)
        return svg_string

    def _circle(self, r, cx, cy):
        return '<circle style="fill:' + str(self._fill) + ';stroke:' + \
            str(self._stroke) + ';" r="' + str(r - 0.5) + '" cx="' + \
            str(cx) + '" cy="' + str(cy) + '" />\n'

    def _footer(self):
        return '</svg>\n'


def svg_str_to_pixbuf(svg_string):
    try:
        pl = GdkPixbuf.PixbufLoader.new_with_type('svg')
        pl.write(svg_string)
        pl.close()
        pixbuf = pl.get_pixbuf()
        return pixbuf
    except:
        print svg_string
        return None
