#!/usr/bin/env python


class PlcMessage(object):

    def __init__(self):
        pass


class StartMessage(PlcMessage):

    def __init__(self):
        super(StartMessage, self).__init__()


class StopMessage(PlcMessage):

    def __init__(self):
        super(StopMessage, self).__init__()


class ShowTagsMessage(PlcMessage):

    def __init__(self):
        super(ShowTagsMessage, self).__init__()


class ShowTagsResponseMessage(PlcMessage):

    def __init__(self, tags):
        super(ShowTagsResponseMessage, self).__init__()
        self.tags = tags


class GetTagsMessage(PlcMessage):

    def __init__(self):
        super(GetTagsMessage, self).__init__()


class GetTagsResponseMessage(PlcMessage):

    def __init__(self, tags):
        super(GetTagsResponseMessage, self).__init__()
        self.tags = tags


class GetTagMessage(PlcMessage):

    def __init__(self, name):
        super(GetTagMessage, self).__init__()
        self.name = name


class GetTagResponseMessage(PlcMessage):

    def __init__(self, value):
        super(GetTagResponseMessage, self).__init__()
        self.value = value


class SetTagMessage(PlcMessage):

    def __init__(self, name, value):
        super(SetTagMessage, self).__init__()
        self.name = name
        self.value = value


class SetTagResponseMessage(PlcMessage):

    def __init__(self):
        super(SetTagResponseMessage, self).__init__()


class MonitorMessage(PlcMessage):

    def __init__(self, tag_names):
        super(MonitorMessage, self).__init__()
        self.tag_names = tag_names


class GetAllTagNamesMessage(PlcMessage):

    def __init__(self):
        super(GetAllTagNamesMessage, self).__init__()


class GetAllTagNamesResponseMessage(PlcMessage):

    def __init__(self, tag_names):
        super(GetAllTagNamesResponseMessage, self).__init__()
        self.tag_names = tag_names


class MonitorResponseMessage(PlcMessage):

    def __init__(self, name, value):
        super(MonitorResponseMessage, self).__init__()
        self.name = name
        self.value = value


class CloseMessage(PlcMessage):

    def __init__(self):
        super(CloseMessage, self).__init__()


class TerminateMessage(PlcMessage):

    def __init__(self):
        super(TerminateMessage, self).__init__()


class SuccessPlcMessage(PlcMessage):

    def __init__(self):
        super(SuccessPlcMessage, self).__init__()


class FailedPlcMessage(PlcMessage):

    def __init__(self):
        super(FailedPlcMessage, self).__init__()
