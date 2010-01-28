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
import cjson
import time
from datetime import datetime
from sugar.activity.activity import Activity, ActivityToolbox, SCOPE_PRIVATE
from sugar.graphics.alert import NotifyAlert
from sugar.graphics.style import (Color, COLOR_BLACK, COLOR_WHITE, 
    COLOR_BUTTON_GREY, FONT_BOLD, FONT_NORMAL)
from sugar.graphics.roundbox import CanvasRoundBox
from sugar.graphics.xocolor import XoColor
from sugar.graphics.palette import Palette, CanvasInvoker
from sugar.graphics.menuitem import MenuItem
from sugar.util import timestamp_to_elapsed_string

from telepathy.client import Connection, Channel
from telepathy.interfaces import (
    CHANNEL_INTERFACE, CHANNEL_INTERFACE_GROUP, CHANNEL_TYPE_TEXT,
    CONN_INTERFACE_ALIASING)
from telepathy.constants import (
    CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES,
    CHANNEL_TEXT_MESSAGE_TYPE_NORMAL)

logger = logging.getLogger('minichat-activity')

class MiniChat(Activity):
    def __init__(self, handle):
        Activity.__init__(self, handle)

        root = self.make_root()
        self.set_canvas(root)
        root.show_all()
        self.entry.grab_focus()

        toolbox = ActivityToolbox(self)
        self.set_toolbox(toolbox)
        toolbox.show()

        self.owner = self._pservice.get_owner()
        self._chat_log = ''
        # Auto vs manual scrolling:
        self._scroll_auto = True
        self._scroll_value = 0.0
        # Track last message, to combine several messages:
        self._last_msg = None
        self._last_msg_sender = None
        # Chat is room or one to one:
        self._chat_is_room = False
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
        self._chat_is_room = True
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
            if type(buddy) is dict:
                nick = buddy['nick']
            else:
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

    def can_close(self):
        """Perform cleanup before closing.
        
        Close text channel of a one to one XMPP chat.
        
        """
        if self._chat_is_room is False:
            if self.text_channel is not None:
                self.text_channel.close()
        return True

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
        box.pack_start(canvas)
        box.pack_start(hbox, expand=False)

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

    def _link_activated_cb(self, link):
        url = url_check_protocol(link.props.text)
        self._show_via_journal(url)

    def add_text(self, buddy, text, status_message=False):
        """Display text on screen, with name and colors.

        buddy -- buddy object or dict {nick: string, color: string}
                 (The dict is for loading the chat log from the journal,
                 when we don't have the buddy object any more.)
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
        |             | | text | url | | |
        |             | +------------+ | |
        |             +----------------+ |
        `--------------------------------'
        """
        if buddy:
            if type(buddy) is dict:
                # dict required for loading chat log from journal
                nick = buddy['nick']
                color = buddy['color']
            else:
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

    def add_separator(self, timestamp):
        """Add whitespace and timestamp between chat sessions."""
        box = hippo.CanvasBox(padding=2)
        time_with_current_year = (time.localtime(time.time())[0],) +\
                time.strptime(timestamp, "%b %d %H:%M:%S")[1:]
        timestamp_seconds = time.mktime(time_with_current_year)
        if timestamp_seconds > time.time():
            time_with_previous_year = (time.localtime(time.time())[0]-1,) +\
                    time.strptime(timestamp, "%b %d %H:%M:%S")[1:]
            timestamp_seconds = time.mktime(time_with_previous_year)
        message = hippo.CanvasText(
            text=timestamp_to_elapsed_string(timestamp_seconds),
            color=COLOR_BUTTON_GREY.get_int(),
            font_desc=FONT_NORMAL.get_pango_desc(),
            xalign=hippo.ALIGNMENT_CENTER)
        box.append(message)
        self.conversation.append(box)
        self._last_msg_sender = None

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

class TextChannelWrapper(object):
    """Wrap a telepathy Text Channel to make usage simpler."""
    def __init__(self, text_chan, conn):
        """Connect to the text channel"""
        self._activity_cb = None
        self._activity_close_cb = None
        self._text_chan = text_chan
        self._conn = conn
        self._logger = logging.getLogger(
            'chat-activity.TextChannelWrapper')
        self._signal_matches = []
        m = self._text_chan[CHANNEL_INTERFACE].connect_to_signal(
            'Closed', self._closed_cb)
        self._signal_matches.append(m)

    def send(self, text):
        """Send text over the Telepathy text channel."""
        # XXX Implement CHANNEL_TEXT_MESSAGE_TYPE_ACTION
        if self._text_chan is not None:
            self._text_chan[CHANNEL_TYPE_TEXT].Send(
                CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, text)

    def close(self):
        """Close the text channel."""
        self._logger.debug('Closing text channel')
        try:
            self._text_chan[CHANNEL_INTERFACE].Close()
        except:
            self._logger.debug('Channel disappeared!')
            self._closed_cb()

    def _closed_cb(self):
        """Clean up text channel."""
        self._logger.debug('Text channel closed.')
        for match in self._signal_matches:
            match.remove()
        self._signal_matches = []
        self._text_chan = None
        if self._activity_close_cb is not None:
            self._activity_close_cb()

    def set_received_callback(self, callback):
        """Connect the function callback to the signal.

        callback -- callback function taking buddy and text args
        """
        if self._text_chan is None:
            return
        self._activity_cb = callback
        m = self._text_chan[CHANNEL_TYPE_TEXT].connect_to_signal('Received',
            self._received_cb)
        self._signal_matches.append(m)

    def handle_pending_messages(self):
        """Get pending messages and show them as received."""
        for id, timestamp, sender, type, flags, text in \
            self._text_chan[
                CHANNEL_TYPE_TEXT].ListPendingMessages(False):
            self._received_cb(id, timestamp, sender, type, flags, text)

    def _received_cb(self, id, timestamp, sender, type, flags, text):
        """Handle received text from the text channel.

        Converts sender to a Buddy.
        Calls self._activity_cb which is a callback to the activity.
        """
        if self._activity_cb:
            try:
                self._text_chan[CHANNEL_INTERFACE_GROUP]
            except:
                # One to one XMPP chat
                nick = self._conn[
                    CONN_INTERFACE_ALIASING].RequestAliases([sender])[0]
                buddy = {'nick': nick, 'color': '#000000,#808080'}
            else:
                # Normal sugar MUC chat
                # XXX: cache these
                buddy = self._get_buddy(sender)
            self._activity_cb(buddy, text)
            self._text_chan[
                CHANNEL_TYPE_TEXT].AcknowledgePendingMessages([id])
        else:
            self._logger.debug('Throwing received message on the floor'
                ' since there is no callback connected. See '
                'set_received_callback')

    def set_closed_callback(self, callback):
        """Connect a callback for when the text channel is closed.

        callback -- callback function taking no args

        """
        self._activity_close_cb = callback

    def _get_buddy(self, cs_handle):
        """Get a Buddy from a (possibly channel-specific) handle."""
        # XXX This will be made redundant once Presence Service 
        # provides buddy resolution
        from sugar.presence import presenceservice
        # Get the Presence Service
        pservice = presenceservice.get_instance()
        # Get the Telepathy Connection
        tp_name, tp_path = pservice.get_preferred_connection()
        conn = Connection(tp_name, tp_path)
        group = self._text_chan[CHANNEL_INTERFACE_GROUP]
        my_csh = group.GetSelfHandle()
        if my_csh == cs_handle:
            handle = conn.GetSelfHandle()
        elif group.GetGroupFlags() & \
            CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES:
            handle = group.GetHandleOwners([cs_handle])[0]
        else:
            handle = cs_handle

            # XXX: deal with failure to get the handle owner
            assert handle != 0

        return pservice.get_buddy_by_telepathy_handle(
            tp_name, tp_path, handle)
