class BaseInterface(object):
    name = "UNDFEFIEDF"

    @staticmethod
    def open_script(script_path):
        raise NotImplementedError("open_script requires implementation")

    @staticmethod
    def setup_hotkey(*args, **kwargs):
        raise NotImplementedError("create_hotkey requires implementation")

    @staticmethod
    def add_to_shelf(*args, **kwargs):
        raise NotImplementedError("add_to_shelf requires implementation")

    @staticmethod
    def get_dcc_extension_map():
        return dict()

    @staticmethod
    def get_dcc_icon_from_browser():
        return ""
