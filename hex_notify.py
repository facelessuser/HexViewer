"""
Hex Viewer.

Licensed under MIT
Copyright (c) 2011-2015 Isaac Muse <isaacmuse@gmail.com>
"""
import sublime
try:
    from SubNotify.sub_notify import SubNotifyIsReadyCommand as Notify
except:
    class Notify:
        @classmethod
        def is_ready(cls):
            return False


def notify(msg):
    settings = sublime.load_settings("hex_viewer.sublime-settings")
    if settings.get("use_sub_notify", False) and Notify.is_ready():
        sublime.run_command("sub_notify", {"title": "HexViewer", "msg": msg})
    else:
        sublime.status_message(msg)


def error(msg):
    settings = sublime.load_settings("hex_viewer.sublime-settings")
    if settings.get("use_sub_notify", False) and Notify.is_ready():
        sublime.run_command("sub_notify", {"title": "HexViewer", "msg": msg, "level": "error"})
    else:
        sublime.error_message("HexViewer:\n%s" % msg)
