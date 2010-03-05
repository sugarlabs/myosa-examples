import gtk
import gconf

from sugar.graphics.toolbarbox import ToolbarButton
from sugar.activity.widgets import ActivityToolbar
from sugar.graphics.xocolor import XoColor
from sugar.graphics.icon import Icon
from sugar.bundle.activitybundle import ActivityBundle

def _create_activity_icon(metadata):
    if metadata.get('icon-color', ''):
        color = XoColor(metadata['icon-color'])
    else:
        client = gconf.client_get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))

    from sugar.activity.activity import get_bundle_path
    bundle = ActivityBundle(get_bundle_path())
    icon = Icon(file=bundle.get_icon(), xo_color=color)

    return icon

class MyActivityToolbarButton(ToolbarButton):

    def __init__(self, activity, **kwargs):
        toolbar = ActivityToolbar(activity, orientation_left=True)
        toolbar.stop.hide()
        toolbar.keep.hide()

        ToolbarButton.__init__(self, page=toolbar, **kwargs)

        icon = _create_activity_icon(activity.metadata)
        self.set_icon_widget(icon)
        icon.show()
