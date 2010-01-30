# Copyright 2007-2008 One Laptop Per Child
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
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from gettext import gettext as _
import hippo
import gtk
import pango
import logging
from sugar.activity.activity import Activity, ActivityToolbox, SCOPE_PRIVATE
from sugar.graphics.alert import NotifyAlert
from sugar.graphics.style import (Color, COLOR_BLACK, COLOR_WHITE, 
    COLOR_BUTTON_GREY, FONT_BOLD, FONT_NORMAL)
from sugar.graphics.roundbox import CanvasRoundBox
from sugar.graphics.xocolor import XoColor
from sugar.graphics.palette import Palette, CanvasInvoker

from textchannel import TextChannelWrapper

logger = logging.getLogger('minichat-activity')

class MiniChat(Activity):
    def __init__(self, handle):
        Activity.__init__(self, handle)

        root = self.make_root()
        self.set_canvas(root)
        root.show_all()
        self.entry.grab_focus()

        toolbox = ActivityToolbox(self)
        activity_toolbar = toolbox.get_activity_toolbar()
        activity_toolbar.keep.props.visible = False
        self.set_toolbox(toolbox)
        toolbox.show()

        self.owner = self._pservice.get_owner()
        # Auto vs manual scrolling:
        self._scroll_auto = True
        self._scroll_value = 0.0
        # Track last message, to combine several messages:
        self._last_msg = None
        self._last_msg_sender = None
        self.text_channel = None

        if self._shared_activity:
            # we are joining the activity
            self.connect('joined', self._joined_cb)
            if self.get_shared():
                # we have already joined
                self._joined_cb()
        else:
            # we are creating the activity
            if not self.metadata or self.metadata.get('share-scope',
                    SCOPE_PRIVATE) == SCOPE_PRIVATE:
                # if we are in private session
                self._alert(_('Off-line'), _('Share, or invite someone.'))
            self.connect('shared', self._shared_cb)

    def _shared_cb(self, activity):
        logger.debug('Chat was shared')
        self._setup()

    def _setup(self):
        self.text_channel = TextChannelWrapper(
            self._shared_activity.telepathy_text_chan,
            self._shared_activity.telepathy_conn)
        self.text_channel.set_received_callback(self._received_cb)
        self._alert(_('On-line'), _('Connected'))
        self._shared_activity.connect('buddy-joined', self._buddy_joined_cb)
        self._shared_activity.connect('buddy-left', self._buddy_left_cb)
        self.entry.set_sensitive(True)
        self.entry.grab_focus()

    def _joined_cb(self, activity):
        """Joined a shared activity."""
        if not self._shared_activity:
            return
        logger.debug('Joined a shared chat')
        for buddy in self._shared_activity.get_joined_buddies():
            self._buddy_already_exists(buddy)
        self._setup()

    def _received_cb(self, buddy, text):
        """Show message that was received."""
        if buddy:
                nick = buddy.props.nick
        else:
            nick = '???'
        logger.debug('Received message from %s: %s', nick, text)
        self.add_text(buddy, text)

    def _alert(self, title, text=None):
        alert = NotifyAlert(timeout=5)
        alert.props.title = title
        alert.props.msg = text
        self.add_alert(alert)
        alert.connect('response', self._alert_cancel_cb)
        alert.show()

    def _alert_cancel_cb(self, alert, response_id):
        self.remove_alert(alert)

    def _buddy_joined_cb (self, activity, buddy):
        """Show a buddy who joined"""
        if buddy == self.owner:
            return
        if buddy:
            nick = buddy.props.nick
        else:
            nick = '???'
        self.add_text(buddy, buddy.props.nick+' '+_('joined the chat'),
            status_message=True)

    def _buddy_left_cb (self, activity, buddy):
        """Show a buddy who joined"""
        if buddy == self.owner:
            return
        if buddy:
            nick = buddy.props.nick
        else:
            nick = '???'
        self.add_text(buddy, buddy.props.nick+' '+_('left the chat'),
            status_message=True)

    def _buddy_already_exists(self, buddy):
        """Show a buddy already in the chat."""
        if buddy == self.owner:
            return
        if buddy:
            nick = buddy.props.nick
        else:
            nick = '???'
        self.add_text(buddy, buddy.props.nick+' '+_('is here'),
            status_message=True)

    def make_root(self):
        conversation = hippo.CanvasBox(
            spacing=0,
            background_color=COLOR_WHITE.get_int())
        self.conversation = conversation

        entry = gtk.Entry()
        entry.modify_bg(gtk.STATE_INSENSITIVE,
                        COLOR_WHITE.get_gdk_color())
        entry.modify_base(gtk.STATE_INSENSITIVE,
                          COLOR_WHITE.get_gdk_color())
        entry.set_sensitive(False)
        entry.connect('activate', self.entry_activate_cb)
        self.entry = entry

        hbox = gtk.HBox()
        hbox.add(entry)

        sw = hippo.CanvasScrollbars()
        sw.set_policy(hippo.ORIENTATION_HORIZONTAL, hippo.SCROLLBAR_NEVER)
        sw.set_root(conversation)
        self.scrolled_window = sw
        
        vadj = self.scrolled_window.props.widget.get_vadjustment()
        vadj.connect('changed', self.rescroll)
        vadj.connect('value-changed', self.scroll_value_changed_cb)

        canvas = hippo.Canvas()
        canvas.set_root(sw)

        box = gtk.VBox(homogeneous=False)
        box.pack_start(hbox, expand=False)
        box.pack_start(canvas)

        return box

    def rescroll(self, adj, scroll=None):
        """Scroll the chat window to the bottom"""
        if self._scroll_auto:
            adj.set_value(adj.upper-adj.page_size)
            self._scroll_value = adj.get_value()

    def scroll_value_changed_cb(self, adj, scroll=None):
        """Turn auto scrolling on or off.
        
        If the user scrolled up, turn it off.
        If the user scrolled to the bottom, turn it back on.
        """
        if adj.get_value() < self._scroll_value:
            self._scroll_auto = False
        elif adj.get_value() == adj.upper-adj.page_size:
            self._scroll_auto = True

    def add_text(self, buddy, text, status_message=False):
        """Display text on screen, with name and colors.

        buddy -- buddy object
        text -- string, what the buddy said
        status_message -- boolean
            False: show what buddy said
            True: show what buddy did

        hippo layout:
        .------------- rb ---------------.
        | +name_vbox+ +----msg_vbox----+ |
        | |         | |                | |
        | | nick:   | | +--msg_hbox--+ | |
        | |         | | | text       | | |
        | +---------+ | +------------+ | |
        |             |                | |
        |             | +--msg_hbox--+ | |
        |             | | text       | | |
        |             | +------------+ | |
        |             +----------------+ |
        `--------------------------------'
        """
        if buddy:
            nick = buddy.props.nick
            color = buddy.props.color
            try:
                color_stroke_html, color_fill_html = color.split(',')
            except ValueError:
                color_stroke_html, color_fill_html = ('#000000', '#888888')
            # Select text color based on fill color:
            color_fill_rgba = Color(color_fill_html).get_rgba()
            color_fill_gray = (color_fill_rgba[0] + color_fill_rgba[1] +
                               color_fill_rgba[2])/3
            color_stroke = Color(color_stroke_html).get_int()
            color_fill = Color(color_fill_html).get_int()
            if color_fill_gray < 0.5:
                text_color = COLOR_WHITE.get_int()
            else:
                text_color = COLOR_BLACK.get_int()
        else:
            nick = '???'  # XXX: should be '' but leave for debugging
            color_stroke = COLOR_BLACK.get_int()
            color_fill = COLOR_WHITE.get_int()
            text_color = COLOR_BLACK.get_int()
            color = '#000000,#FFFFFF'

        # Check for Right-To-Left languages:
        if pango.find_base_dir(nick, -1) == pango.DIRECTION_RTL:
            lang_rtl = True
        else:
            lang_rtl = False

        # Check if new message box or add text to previous:
        new_msg = True
        if self._last_msg_sender:
            if not status_message:
                if buddy == self._last_msg_sender:
                    # Add text to previous message
                    new_msg = False

        if not new_msg:
            rb = self._last_msg
            msg_vbox = rb.get_children()[1]
            msg_hbox = hippo.CanvasBox(
                orientation=hippo.ORIENTATION_HORIZONTAL)
            msg_vbox.append(msg_hbox)
        else:
            rb = CanvasRoundBox(background_color=color_fill,
                                border_color=color_stroke,
                                padding=4)
            rb.props.border_color = color_stroke  # Bug #3742
            self._last_msg = rb
            self._last_msg_sender = buddy
            if not status_message:
                name = hippo.CanvasText(text=nick+':   ',
                    color=text_color,
                    font_desc=FONT_BOLD.get_pango_desc())
                name_vbox = hippo.CanvasBox(
                    orientation=hippo.ORIENTATION_VERTICAL)
                name_vbox.append(name)
                rb.append(name_vbox)
            msg_vbox = hippo.CanvasBox(
                orientation=hippo.ORIENTATION_VERTICAL)
            rb.append(msg_vbox)
            msg_hbox = hippo.CanvasBox(
                orientation=hippo.ORIENTATION_HORIZONTAL)
            msg_vbox.append(msg_hbox)

        if status_message:
            self._last_msg_sender = None

        if text:
            message = hippo.CanvasText(
                text=text,
                size_mode=hippo.CANVAS_SIZE_WRAP_WORD,
                color=text_color,
                font_desc=FONT_NORMAL.get_pango_desc(),
                xalign=hippo.ALIGNMENT_START)
            msg_hbox.append(message)

        # Order of boxes for RTL languages:
        if lang_rtl:
            msg_hbox.reverse()
            if new_msg:
                rb.reverse()

        if new_msg:
            box = hippo.CanvasBox(padding=2)
            box.append(rb)
            self.conversation.append(box)

    def entry_activate_cb(self, entry):
        text = entry.props.text
        logger.debug('Entry: %s' % text)
        if text:
            self.add_text(self.owner, text)
            entry.props.text = ''
            if self.text_channel:
                self.text_channel.send(text)
            else:
                logger.debug('Tried to send message but text channel '
                    'not connected.')
