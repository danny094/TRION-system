PLUGIN_META_FILE = ".trion-plugin.json"
PLUGIN_PERMISSION_KEYS = ("api", "events", "tools")

ALLOWED_KINDS = {"app", "widget", "theme", "panel"}
ALLOWED_MOUNTS = {
    "launchpad": {"app"},
    "settings.tab": {"app", "panel"},
    "sidebar": {"widget"},
    "chat.panel": {"panel"},
    "theme": {"theme"},
}
