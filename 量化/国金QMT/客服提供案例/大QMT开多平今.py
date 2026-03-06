#coding:gbk
from xtquant.qmttools.functions import passorder


def handlebar(ContextInfo):
    if not ContextInfo.is_last_bar():
        return
    target = 'rb2511.SF'
    passorder(0, 1101, '229682', target, 5, -1, 10, 1, ContextInfo)

    target = 'rb2511.SF'
    passorder(6, 1101, '229682', target, 5, -1, 2, 1, ContextInfo)