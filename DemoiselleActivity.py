from gettext import gettext as _

import gtk
import pygame
from sugar.activity import activity
from sugar.graphics.alert import NotifyAlert
from sugar.graphics.toolbutton import ToolButton
import gobject
import sugargame.canvas
import demoiselle2

class DemoiselleActivity(activity.Activity):
    def __init__(self, handle):
        super(DemoiselleActivity, self).__init__(handle)
        
        # Build the activity toolbar.
        self.build_toolbar()

        # Create the game instance.
        self.game = demoiselle2.Demoiselle()

        # Build the Pygame canvas.
        self._pygamecanvas = sugargame.canvas.PygameCanvas(self)
        # Note that set_canvas implicitly calls read_file when resuming from the Journal.
        self.set_canvas(self._pygamecanvas)
        
        # Start the game running.
        self._pygamecanvas.run_pygame(self.game.run)
        
    def build_toolbar(self):
        toolbox = activity.ActivityToolbox(self)
        
        self.view_toolbar = ViewToolbar()
        toolbox.add_toolbar(_('View'), self.view_toolbar)
        self.view_toolbar.connect('go-fullscreen',
                self.view_toolbar_go_fullscreen_cb)
        self.view_toolbar.show()

        toolbox.show_all()
        self.set_toolbox(toolbox)

    def view_toolbar_go_fullscreen_cb(self, view_toolbar):
        self.fullscreen()

    def read_file(self, file_path):
        score_file = open(file_path, "r")
        while score_file:
            line = score_file.readline()
            alert(_('Previous Score'),  _('Your score last time was ') + line)
        score_file.close()
        
    def write_file(self, file_path):
        score = self.game.get_score()
        f = open(file_path, 'wb')
        try:
            f.write(score)
        finally:
            f.close

    def alert(self, title, text=None):
        alert = NotifyAlert(timeout=20)
        alert.props.title = title
        alert.props.msg = text
        self.add_alert(alert)
        alert.connect('response', self.alert_cancel_cb)
        alert.show()

    def alert_cancel_cb(self, alert, response_id):
        self.remove_alert(alert)
        self.textview.grab_focus()

class ViewToolbar(gtk.Toolbar):
    __gtype_name__ = 'ViewToolbar'

    __gsignals__ = {
        'needs-update-size': (gobject.SIGNAL_RUN_FIRST,
                              gobject.TYPE_NONE,
                              ([])),
        'go-fullscreen': (gobject.SIGNAL_RUN_FIRST,
                          gobject.TYPE_NONE,
                          ([]))
    }

    def __init__(self):
        gtk.Toolbar.__init__(self)
        self.fullscreen = ToolButton('view-fullscreen')
        self.fullscreen.set_tooltip(_('Fullscreen'))
        self.fullscreen.connect('clicked', self.fullscreen_cb)
        self.insert(self.fullscreen, -1)
        self.fullscreen.show()

    def fullscreen_cb(self, button):
        self.emit('go-fullscreen')
