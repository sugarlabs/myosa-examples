# minichat.py
# Copyright 2007-2008 One Laptop Per Child
# Copyright 2012 Aneesh Dogra <lionaneesh@gmail.com>
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

from gi.repository import GObject
from gettext import gettext as _
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango
import logging
from sugar3.activity.activity import Activity, SCOPE_PRIVATE
from sugar3.activity.widgets import ActivityToolbar, StopButton
from sugar3.graphics.alert import NotifyAlert
from sugar3.presence.presenceservice import PresenceService
from sugar3.graphics.style import (Color, COLOR_BLACK, COLOR_WHITE, 
    COLOR_BUTTON_GREY, FONT_BOLD, FONT_NORMAL)
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.palette import Palette

from textchannel import TextChannelWrapper

logger = logging.getLogger('minichat-activity')

class MiniChat(Activity):
    def __init__(self, handle):
        Activity.__init__(self, handle)

        toolbox = ActivityToolbar(self)

        stop_button = StopButton(self)
        stop_button.show()
        toolbox.insert(stop_button, -1)

        self.set_toolbar_box(toolbox)
        toolbox.show()

        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        root = self.make_root()
        self.set_canvas(root)
        root.show_all()
        self.entry.grab_focus()

        self.pservice = PresenceService()
        self.owner = self.pservice.get_owner()

        screen = Gdk.Screen.get_default()
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path('minichat.css')
        context = Gtk.StyleContext()
        context.add_provider_for_screen(screen,
                                        css_provider,
                                        Gtk.STYLE_PROVIDER_PRIORITY_USER)

        # Track last message, to combine several messages:
        self._last_msg = None
        self._last_msg_sender = None
        self.text_channel = None

        if self.shared_activity:
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

    def _joined_cb(self, activity):
        """Joined a shared activity."""
        if not self.shared_activity:
            return
        logger.debug('Joined a shared chat')
        for buddy in self.shared_activity.get_joined_buddies():
            self._buddy_already_exists(buddy)
        self._setup()

    def _setup(self):
        self.text_channel = TextChannelWrapper(
            self.shared_activity.telepathy_text_chan,
            self.shared_activity.telepathy_conn)
        self.text_channel.set_received_callback(self._received_cb)
        self._alert(_('On-line'), _('Connected'))
        self.shared_activity.connect('buddy-joined', self._buddy_joined_cb)
        self.shared_activity.connect('buddy-left', self._buddy_left_cb)
        self.entry.set_sensitive(True)
        self.entry.grab_focus()

    def _received_cb(self, buddy, text):
        """Show message that was received."""
        if buddy:
            nick = buddy.nick
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
            nick = buddy.nick
        else:
            nick = '???'
        self.add_text(buddy, buddy.nick+' '+_('joined the chat'),
            status_message=True)

    def _buddy_left_cb (self, activity, buddy):
        """Show a buddy who joined"""
        if buddy == self.owner:
            return
        if buddy:
            nick = buddy.nick
        else:
            nick = '???'
        self.add_text(buddy, buddy.nick+' '+_('left the chat'),
            status_message=True)

    def _buddy_already_exists(self, buddy):
        """Show a buddy already in the chat."""
        if buddy == self.owner:
            return
        if buddy:
            nick = buddy.nick
        else:
            nick = '???'
        self.add_text(buddy, buddy.nick+' '+_('is here'),
            status_message=True)

    def make_root(self):
        vbox = Gtk.VBox()

        self.conversation = Gtk.VBox()
        self.conversation.show_all()
        vbox.pack_start(self.conversation, False, False, 0)

        self.entry = Gtk.Entry()
        self.entry.modify_bg(Gtk.StateType.INSENSITIVE,
                             COLOR_WHITE.get_gdk_color())
        self.entry.modify_base(Gtk.StateType.INSENSITIVE,
                               COLOR_WHITE.get_gdk_color())
        self.entry.set_sensitive(False)

        setattr(self.entry, "nick", "???")
        self.entry.connect('activate', self.entry_activate_cb)
        vbox.pack_end(self.entry, False, False, 0)
        vbox.show()

        box = Gtk.VBox(homogeneous=False)
        box.pack_end(vbox, False, True, 0)
        box.show_all()

        return box

    def add_text(self, buddy, text, status_message=False):
        """Display text on screen, with name and colors.

        buddy -- buddy object
        text -- string, what the buddy said
        status_message -- boolean
            False: show what buddy said
            True: show what buddy did

        Gtk layout:
        
        .------------- rb ---------------.
        | +name_vbox+ +----msg_vbox----+ |
        | |         | |                | |
        | | nick:   | | +----entry---+ | |
        | |         | | | text       | | |
        | +---------+ | +------------+ | |
        |             |                | |
        |             | +----entry---+ | |
        |             | | text       | | |
        |             | +------------+ | |
        |             +----------------+ |
        `--------------------------------'

        """
        if buddy:
            nick = buddy.props.nick
        else:
            nick = '???'  # XXX: should be '' but leave for debugging

        logger.debug('Nick: %s' % nick)

        # Check for Right-To-Left languages:
        if Pango.find_base_dir(nick, -1) == Pango.Direction.RTL:
            lang_rtl = True
        else:
            lang_rtl = False

        logger.debug('lang_rtl: %s' % str(lang_rtl))

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

        else: # Its a new_msg, we need to create a new rb
            rb = Gtk.HBox()
            logger.debug('rb: %s' % str(rb))
            self._last_msg = rb
            self._last_msg_sender = buddy
            if not status_message:
                name = Gtk.Entry()
                name.set_text(nick+':   ')
                name_vbox = Gtk.VBox()
                name_vbox.add(name)
                rb.pack_start(name_vbox, False, True, 0)

            msg_vbox = Gtk.VBox()
            rb.pack_start(msg_vbox, True, True, 0)

        if status_message:
            self._last_msg_sender = None

        if text:
            msg = Gtk.TextView()
            text_buffer = msg.get_buffer()
            text_buffer.set_text(text)
            msg.show()
            msg.set_editable(False)
            msg.set_justification(Gtk.Justification.LEFT)
            msg.set_border_width(5)
            msg.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            msg_vbox.pack_start(msg, True, True, 1)

        # Order of boxes for RTL languages:
        if lang_rtl:
            msg_hbox.reverse()
            if new_msg:
                rb.reverse()

        if new_msg:
            self.conversation.add(rb)
        rb.show_all()

    def entry_activate_cb(self, entry):
        text = entry.get_text()
        logger.debug('Entry: %s' % text)
        if text:
            self.add_text(self.owner, text)
            entry.set_text('')
            if self.text_channel:
                self.text_channel.send(text)
            else:
                logger.debug('Tried to send message but text channel '
                    'not connected.')
