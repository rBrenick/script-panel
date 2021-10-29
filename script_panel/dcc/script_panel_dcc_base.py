class BaseInterface(object):
    name = "UNDFEFIEDF"

    @staticmethod
    def open_script(script_path):
        raise NotImplementedError("open_script requires implementation")

    @staticmethod
    def get_dcc_extension_map():
        return dict()
