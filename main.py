import sys
import os
from PyQt5 import QtWidgets, QtGui

import gcom
import gxml
import gxml_ui
import logging
import glogging
import base64
import gicon

logger = logging.getLogger(__name__)    # logger for inner thread message


if __name__ == '__main__':
    try:
        # glogging.log2stdout(logger, logging.WARNING)
        # glogging.log2stdout(logger, logging.INFO)
        # glogging.log2stdout(logger, logging.DEBUG)
        glogging.log2file(logger, logging.INFO)
        gxml.logger    = logger
        gxml_ui.logger = logger
        gcom.logger    = logger

        app = QtWidgets.QApplication(sys.argv)
        font = QtGui.QFont()
        font.setFamily("consolas")
        app.setFont(font)
        app.setStyleSheet('QPushButton:pressed { font: bold; color: black; background-color: #ff4000 }')
        #app.setWindowIcon(QtGui.QIcon(os.path.join('.', 'gx.png')))     # need copy gx.png file to exe dir
        # with open(os.path.join(r'D:\download', 'gx2.png'), 'rb') as fr, open('gicon.py', 'w') as fw:
        #    fw.write('icon = {}'.format(base64.b64encode(fr.read())))
        pixm = QtGui.QPixmap()
        pixm.loadFromData(base64.b64decode(gicon.icon))
        icon = QtGui.QIcon()
        icon.addPixmap(pixm)
        app.setWindowIcon(icon)

        # mw = QtWidgets.QWidget()
        # ui = test01.Ui_Form()
        # ui.setupUi(mw)
        # mw.show()
        ui = gxml_ui.gXmlTable()
        ui.setWindowTitle('ver 1.2')
        ui.show()

        sys.exit(app.exec_())
    except Exception as err:
        import traceback

        #. traceback.print_exc()
        logger.warning('Exception in main_ui: {}'.format(repr(err), exc_info=True))

        # <run in Terminal> pyinstaller -Fw main_ui.py -n gxml