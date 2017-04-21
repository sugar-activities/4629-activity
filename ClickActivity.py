#Copyright (c) 2011 Walter Bender

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, 51 Franklin Street, Suite 500 Boston, MA 02110-1335 USA


from gi.repository import Gtk,Gdk
from sugar3.activity import activity
from sugar3 import profile
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.activity.widgets import StopButton

from toolbar_utils import button_factory, label_factory, separator_factory, \
                          radio_factory

from gettext import gettext as _

from game import Game

import logging
_logger = logging.getLogger('click-activity')


class ClickActivity(activity.Activity):
    """ Interactive reading game """

    def __init__(self, handle):
        """ Initialize the toolbars and the game board """
        super(ClickActivity, self).__init__(handle)

        self.nick = profile.get_nick_name()
        if profile.get_color() is not None:
            self.colors = profile.get_color().to_string().split(',')
        else:
            self.colors = ['#A0FFA0', '#FF8080']

        self._setup_toolbars()

        # Create a canvas
        canvas = Gtk.DrawingArea()
        canvas.set_size_request(Gdk.Screen.width(), \
                                Gdk.Screen.height())
        self.set_canvas(canvas)
        canvas.show()
        self.show_all()

        self._game = Game(canvas, parent=self, colors=self.colors)


    def _setup_toolbars(self):
        """ Setup the toolbars. """
        self.max_participants = 1

        toolbox = ToolbarBox()

        activity_button = ActivityToolbarButton(self)

        toolbox.toolbar.insert(activity_button, 0)
        activity_button.show()

        self.set_toolbar_box(toolbox)
        toolbox.show()
        self.toolbar = toolbox.toolbar

        self.status = label_factory(self.toolbar, '')

        separator_factory(toolbox.toolbar, True, False)

        stop_button = StopButton(self)
        stop_button.props.accelerator = '<Ctrl>q'
        toolbox.toolbar.insert(stop_button, -1)
        stop_button.show()
