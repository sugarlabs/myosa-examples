#
# <one line to give the program's name and a brief idea of what it does.>
# Copyright (C) <YEAR>  <NAME>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

from gi.repository import Gtk
import gst
import random
from gettext import gettext as _

def gstmessage_cb(bus, message, pipe):
    if message.type in (gst.MESSAGE_EOS, gst.MESSAGE_ERROR):
        pipe.set_state(gst.STATE_NULL)

def make_pipe():
    pipeline = 'espeak name=src ! autoaudiosink'
    pipe = gst.parse_launch(pipeline)

    src = pipe.get_by_name('src')
    src.props.text = _('Hello, World!')
    src.props.pitch = random.randint(-100, 100)
    src.props.rate = random.randint(-100, 100)

    voices = src.props.voices
    voice = voices[random.randint(0, len(voices)-1)]
    src.props.voice = voice[0]

    bus = pipe.get_bus()
    bus.add_signal_watch()
    bus.connect('message', gstmessage_cb, pipe)

    pipe.set_state(gst.STATE_PLAYING)

for i in range(10):
    make_pipe()

Gtk.main()
