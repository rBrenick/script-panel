from .ui_utils import QtCore

_qt = QtCore.Qt  # quicker access to properties


class ScriptPanelSortProxyModel(QtCore.QSortFilterProxyModel):
    """
    Sorting proxy model that always places folders on top.
    copied from https://stackoverflow.com/a/25627929

    """

    def __init__(self, model):
        super(ScriptPanelSortProxyModel, self).__init__(model)
        self.setSourceModel(model)

    def lessThan(self, left, right):
        """
        Perform sorting comparison.
        Since we know the sort order, we can ensure that folders always come first.
        """
        left_path_data = left.data(_qt.UserRole)  # type: PathData
        right_path_data = right.data(_qt.UserRole)  # type: PathData
        left_is_folder = left_path_data.is_folder if left_path_data else False
        left_data = left.data(_qt.DisplayRole) or ""
        right_is_folder = right_path_data.is_folder if right_path_data else False
        right_data = right.data(_qt.DisplayRole) or ""
        sort_order = self.sortOrder()

        if left_is_folder and not right_is_folder:
            result = sort_order == _qt.AscendingOrder
        elif not left_is_folder and right_is_folder:
            result = sort_order != _qt.AscendingOrder
        else:
            result = left_data < right_data
        return result

    def filterAcceptsRow(self, source_row, source_parent):
        filter_regex = self.filterRegExp()
        if filter_regex.isEmpty():
            return True

        r = source_row  # type: int
        p = source_parent  # type: QtCore.QModelIndex
        model_index = self.sourceModel().index(r, 0, p)
        path_data = self.sourceModel().data(model_index, _qt.UserRole)  # type: PathData

        # check children
        for i in range(self.sourceModel().rowCount(model_index)):
            if self.filterAcceptsRow(i, model_index):
                return True

        result = filter_regex.indexIn(path_data.relative_path)
        if result == -1:
            return False
        return True


class PathData(object):
    def __init__(self, relative_path, full_path=None, is_folder=False):
        self.relative_path = relative_path
        self.full_path = full_path
        self.is_folder = is_folder

