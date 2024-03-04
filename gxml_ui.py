import os
import random

import glib
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import QAbstractItemView, QHeaderView, QFileDialog
from PyQt5.QtCore import Qt, QStringListModel, QRegExp

import gcom
import gxml
import logging

logger = logging.getLogger(__name__)    # logger for inner thread message


class gXmlTable(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.file_open = QtWidgets.QPushButton('Xml')
        self.uart_conn = QtWidgets.QPushButton('Connect/DisConnect')
        self.uart_dtct = QtWidgets.QPushButton('Detect')
        self.uart_list = QtWidgets.QComboBox()
        self.uart_list.setPlaceholderText('COM')
        self.uart_baud = QtWidgets.QLineEdit('921600')
        self.file_disp = QtWidgets.QLineEdit('')
        self.file_disp.setReadOnly(True)
        self.qtw_mods = QtWidgets.QTableWidget()
        self.qtw_regs = QtWidgets.QTableWidget()
        self.uart_lay = QtWidgets.QHBoxLayout()
        self.uart_lay.addWidget(self.file_open, 1)
        self.uart_lay.addWidget(self.uart_dtct, 1)
        self.uart_lay.addWidget(self.uart_list, 1)
        self.uart_lay.addWidget(self.uart_baud, 1)
        self.uart_lay.addWidget(self.uart_conn, 2)
        self.mods_lay = QtWidgets.QGridLayout()
        self.mods_lay.addLayout(self.uart_lay , 0, 0, 1, -1)
        self.mods_lay.addWidget(self.file_disp, 1, 0, 1, -1)
        self.mods_lay.addWidget(self.qtw_mods , 2, 0, -1, 1)
        self.mods_lay.addWidget(self.qtw_regs , 2, 1, -1, 1)

        self.reg_addrp  = QtWidgets.QLabel('addr:')
        self.reg_datap  = QtWidgets.QLabel('data:')
        self.reg_addr   = QtWidgets.QLineEdit()
        self.reg_data   = QtWidgets.QLineEdit()
        self.reg_read   = QtWidgets.QPushButton('Read')
        self.reg_read.setShortcut('r')
        self.reg_write  = QtWidgets.QPushButton('Write')
        self.reg_write.setShortcut('w')
        self.qtw_bits = QtWidgets.QTableWidget()
        self.bits_lay = QtWidgets.QGridLayout()
        self.bits_lay.addWidget(self.reg_addrp, 0, 0, 1, 1)
        self.bits_lay.addWidget(self.reg_datap, 1, 0, 1, 1)
        self.bits_lay.addWidget(self.reg_addr , 0, 1, 1, 1)
        self.bits_lay.addWidget(self.reg_data , 1, 1, 1, 1)
        self.bits_lay.addWidget(self.reg_read , 0, 2, 1, 1)
        self.bits_lay.addWidget(self.reg_write, 1, 2, 1, 1)
        self.bits_lay.addWidget(self.qtw_bits , 2, 0, -1, -1)

        self.qtw_lay = QtWidgets.QHBoxLayout()
        self.qtw_lay.addLayout(self.mods_lay)
        self.qtw_lay.addLayout(self.bits_lay)

        font = self.qtw_mods.horizontalHeader().font()
        font.setBold(True)
        for item in (self.qtw_mods, self.qtw_regs, self.qtw_bits):
            item.setSelectionBehavior(QAbstractItemView.SelectRows)
            item.setAlternatingRowColors(True)
            item.horizontalHeader().setFont(font)
            item.horizontalHeader().setStyleSheet("QHeaderView::section{background-color:skyblue;}")
            #item.horizontalHeader().setStyleSheet('color: green')
            #item.horizontalHeader().setStyleSheet('background-color: green')
        #QtWidgets.QPushButton::{color: red}

        self.flt_txt = QtWidgets.QLineEdit()
        self.flt_txt.setPlaceholderText('filter')
        #. self.flt_txt.setValidator(QRegExpValidator(QRegExp(r'\w+')))
        self.flt_lsv = QtWidgets.QListView()
        self.flt_lsv.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.flt_lay = QtWidgets.QVBoxLayout()
        self.flt_lay.addWidget(self.flt_txt)
        self.flt_lay.addWidget(self.flt_lsv)

        self.lay_top = QtWidgets.QHBoxLayout()
        self.lay_top.addLayout(self.qtw_lay, 3)
        self.lay_top.addLayout(self.flt_lay, 1)
        self.setLayout(self.lay_top)
        self.slm = QStringListModel()
        self.flt_lsv.setModel(self.slm)
        self.lst_flt = []   # list of filtered (name, addr)

        self.mxml = gxml.gXmlParser()
        self.omod = None    # object select gXmlMod
        self.oreg = None    # object select gXmlReg
        self.mcom = gcom.gCom()
        self.conn = False   # com connected status
        self.top_xml = 'gxml.ini'

        self.init_action()

        # read the top xml file path
        if os.path.isfile(self.top_xml):
            fr = open(self.top_xml, 'r')
            mline = fr.readline().rstrip()
            fr.close()
            if os.path.isfile(mline):
                self.init_xml(mline)

    def init_action(self):
        self.file_open.clicked.connect(self.slot_file_open)
        self.uart_dtct.clicked.connect(self.slot_uart_detect)
        self.uart_conn.clicked.connect(self.slot_uart_connect)
        self.qtw_mods.cellClicked.connect(self.slot_click_mod)
        self.qtw_regs.cellClicked.connect(self.slot_click_reg)
        self.qtw_bits.itemChanged.connect(self.slot_change_bit)
        self.flt_txt.textEdited.connect(self.slot_edit_flt)
        self.flt_lsv.clicked.connect(self.slot_click_flt)
        self.reg_read.clicked.connect(self.slot_addr_retn)
        self.reg_write.clicked.connect(self.slot_data_retn)
        self.reg_addr.returnPressed.connect(self.slot_addr_retn)
        self.reg_data.returnPressed.connect(self.slot_data_retn)

    def slot_click_mod(self, rmod, cmod):
        # when clicked <QTableWidget>-mods, select a module
        # do: update regs & bits
        logger.info('clicked mod({}, {})'.format(rmod, cmod))
        self.qtw_mods.setCurrentCell(rmod, cmod)
        mod_name = self.qtw_mods.item(rmod, 1).text()
        if (self.omod is None) or (mod_name != self.omod.name):
            self.omod = self.mxml.mods[mod_name]
            self.set_qtw_regs()
            self.slot_click_reg(0, 1)

    def slot_click_reg(self, rreg, creg):
        # when clicked <QTableWidget>-regs, select a reg
        # do: update bits
        logger.info('clicked reg({}, {})'.format(rreg, creg))
        self.qtw_regs.setCurrentCell(rreg, creg)
        reg_name = self.qtw_regs.item(rreg, 1).text()
        if (self.oreg is None) or (reg_name != self.oreg.name):
            self.oreg = self.omod.regs[reg_name]
            self.set_qtw_bits()

    def slot_change_bit(self, item):
        rbit = self.qtw_bits.row(item)
        cbit = self.qtw_bits.column(item)
        logger.info('changed bit({}, {})'.format(rbit, cbit))
        bit_data = self.qtw_bits.item(rbit, 1).text()
        bit_name = self.qtw_bits.item(rbit, 2).text()
        mval = glib.str2int(bit_data, 16)
        bit_dict = {bit_name: {'val': mval}}
        self.oreg.set(bit_dict)
        self.set_qtw_bits()

    def slot_edit_flt(self, vtxt=r'.*'):
        # when input filter text
        # do: update <QListView> filter out
        logger.info('slot_edit_flt: {}'.format(vtxt))
        if vtxt:
            self.lst_flt = self.mxml.filter(vtxt)
            mlst = [x[0] for x in self.lst_flt]
        else:
            mlst = []
        self.slm.setStringList(mlst)

    def slot_click_flt(self, idx):
        # when clicked a filter item
        # do: update <QTableWidget>-regs & <QTableWidget>-bits
        item = self.lst_flt[idx.row()]
        logger.info('slot_click_flt: ({}, 0x{:08x})'.format(item[0], item[1]))
        self.update_reg(item[1])

    def slot_file_open(self):
        # when push self.file_open
        # do: initialize the whole UI
        logger.info('slot_file_open')
        mfilepath,ok = QFileDialog.getOpenFileName(self, 'OpenFile')
        if ok:
            self.init_xml(mfilepath)
            # write the top xml file path
            with open(self.top_xml, 'w') as fw:
                fw.write(mfilepath)

    def slot_uart_detect(self):
        logger.info('slot_uart_detect')
        mlst = self.mcom.detect()
        if mlst is not None:
            self.uart_list.clear()
            self.uart_list.addItems(mlst)
            self.uart_list.setCurrentIndex(0)

    def slot_uart_connect(self):
        logger.info('slot_uart_connect')
        if self.conn:
            self.set_uart_conn(self.mcom.close())
        else:
            com_name = self.uart_list.currentText()
            com_baud = int(self.uart_baud.text())
            self.mcom.set(com_name, com_baud, 1)
            self.set_uart_conn(self.mcom.open())

    def set_uart_conn(self, ok):
        if ok:
            self.conn = True
            logger.info('slot_uart_connect success')
            self.uart_conn.setStyleSheet('QPushButton:!hover { font: normal; color: black; background-color: #00c500 }')
        else:
            self.conn = False
            logger.info('slot_uart_connect failed')
            self.uart_conn.setStyleSheet('QPushButton:!hover { font: italic; color: black; background-color: gray }')

    def slot_addr_retn(self):
        # when reg_addr edit done: Return or Lose Focus
        # do: [read] and update <QLineEdit>-reg and <QTableWidget>-bits
        reg_addr = self.reg_addr.text()
        logger.info('slot_addr_retn: addr = {}'.format(reg_addr))
        reg_addr = glib.str2int(reg_addr, 16)
        read_val = self.read(reg_addr)
        if read_val is not None:
            # update <QLineEdit>-reg @even if [reg_addr not in mxml]
            self.reg_addr.setText(format(reg_addr, '08x'))
            self.reg_data.setText(format(read_val, '08x'))
            # update self.oreg & <QTableWidget>-bits
            self.update_reg(reg_addr, read_val)
        else:
            self.set_uart_conn(self.mcom.close())
            self.update_reg(reg_addr, read_val)

    def slot_data_retn(self):
        # when reg_addr edit done: Return or Lose Focus
        # do: [write] [read] and update <QLineEdit>-reg and <QTableWidget>-bits
        reg_addr = self.reg_addr.text()
        reg_data = self.reg_data.text()
        logger.info('slot_data_retn: addr = {}, data = {}'.format(reg_addr, reg_data))
        reg_addr = glib.str2int(reg_addr, 16)
        reg_data = glib.str2int(reg_data, 16)
        self.reg_addr.setText(format(reg_addr, '08x'))
        self.reg_data.setText(format(reg_data, '08x'))
        # do write & read & check
        if not self.conn:
            self.update_reg(reg_addr, reg_data)
        elif self.write(reg_addr, reg_data):
            self.slot_addr_retn()
        else:
            self.set_uart_conn(self.mcom.close())

    def update_reg(self, vsel=None, vval=None):
        # search reg with @vsel, and set reg with @vval
        # update <QTableWidget>-{regs, bits}
        (mod_name, reg_name) = self.mxml.get_modreg(vsel)
        if (mod_name is not None) and (reg_name is not None):
            if mod_name != self.omod.name:
                self.omod = self.mxml.mods[mod_name]
                self.set_qtw_regs()
                self.oreg = self.omod.regs[reg_name]
                if vval is not None:
                    self.oreg.set(vval)
                self.set_qtw_bits()
            elif (reg_name != self.oreg.name) or (vval is not None):
                self.oreg = self.omod.regs[reg_name]
                if vval is not None:
                    self.oreg.set(vval)
                self.set_qtw_bits()

    def read(self, vaddr=0):
        # read dut addr
        # return read data or None
        #reg_data = random.randint(0, 2**32-1)
        if not self.conn:
            return None
        reg_data = self.mcom.read(vaddr)
        if reg_data is not None:
            logger.info('read: {:08x} = {:08x}'.format(vaddr, reg_data))
        else:
            logger.warning('read: {:08x} failed'.format(vaddr))
        return reg_data

    def write(self, vaddr=0, vdata=0):
        # write dut addr = data
        # return True or False
        if not self.conn:
            return False
        if vaddr != self.oreg.addr:
            logger.warning('self.oreg.addr({:08x}) != vaddr({:08x})'.format(self.oreg.addr, vaddr))
            logger.warning('\tyou neet update self.oreg outside')
        logger.info('write: {:08x} = {:08x}'.format(vaddr, vdata))
        return self.mcom.write(vaddr, vdata)

    def init_xml(self, vfilepath):
        # when get a valid top xml file path, init the whole content
        self.file_disp.setText(vfilepath)
        self.mxml.set(vfilepath)
        self.mxml.load()
        self.init_qtw()
        # clear filter & view
        self.flt_txt.clear()
        self.slm.setStringList([])

    def init_qtw(self):
        self.set_qtw_mods()
        for mobj in (self.qtw_mods, self.qtw_regs, self.qtw_bits):
            mobj.verticalHeader().setMinimumHeight(16)
            mobj.verticalHeader().setDefaultSectionSize(22)
            mobj.verticalHeader().setVisible(False)
            mobj.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            for k in range(mobj.columnCount()-1):
                mobj.horizontalHeader().setSectionResizeMode(k, QHeaderView.ResizeToContents)

    def set_qtw_mods(self):
        # update <QTableWidgets>-mods based on <self.mxml>
        self.qtw_mods.setColumnCount(2)
        mlst = self.mxml.get_lst()
        self.qtw_mods.setRowCount(len(mlst))
        for kr in range(len(mlst)):
            self.set_item_mod(kr, (format(mlst[kr][1], '08x'), mlst[kr][0]))
        #self.qtw_mods.sortItems(0)
        self.qtw_mods.setHorizontalHeaderLabels(['address', 'module'])

        self.slot_click_mod(0, 1)

    def set_qtw_regs(self):
        # update <QTableWidgets>-regs based on <self.omod>
        self.qtw_regs.setColumnCount(2)
        kr = 0
        mlst = self.omod.get_lst()
        self.qtw_regs.setRowCount(len(mlst))
        for kr in range(len(mlst)):
            self.set_item_reg(kr, ('0x'+format(mlst[kr][1], '03x'), mlst[kr][0]))
        #self.qtw_regs.sortItems(0)
        self.qtw_regs.setHorizontalHeaderLabels(['offset', 'reg'])

    def set_qtw_bits(self):
        # update <QTableWidgets>-bits based on <self.oreg>
        self.qtw_bits.blockSignals(True)    # disable itemChanged signal
        self.qtw_bits.setColumnCount(3)
        kr = 0
        self.qtw_bits.setRowCount(len(self.oreg.bits))
        for obit in self.oreg.get_lst():
            self.set_item_bit(kr, obit)
            kr += 1
        #self.qtw_bits.sortItems(0, Qt.DescendingOrder)
        self.qtw_bits.setHorizontalHeaderLabels(['bit', 'value', 'name'])
        self.set_addr_data()
        self.qtw_bits.blockSignals(False)

    def set_item_mod(self, kr, imod=('addr', 'name')):
        logger.info('set_item_mod<{}> = {}'.format(kr, imod))
        kc = 0
        for x in imod:
            item = self.qtw_mods.item(kr, kc)
            if item:
                item.setText(x)
            else:
                item = QtWidgets.QTableWidgetItem()
                item.setText(x)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.qtw_mods.setItem(kr, kc, item)
                logger.info('mod<{}, {}> = {}'.format(kr, kc, self.qtw_mods.item(kr, kc).text()))
            kc += 1

    def set_item_reg(self, kr, ireg=('addr', 'name')):
        logger.info('set_item_reg<{}> = {}'.format(kr, ireg))
        kc = 0
        for x in ireg:
            item = self.qtw_regs.item(kr, kc)
            if item:
                item.setText(x)
            else:
                item = QtWidgets.QTableWidgetItem()
                item.setText(x)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.qtw_regs.setItem(kr, kc, item)
                logger.info('reg<{}, {}> = {}'.format(kr, kc, self.qtw_regs.item(kr, kc).text()))
            kc += 1

    def set_item_bit(self, kr, gbit):
        # gbit: gXmlReg.bits[k]
        mlst = ('pos', 'val', 'name')
        kc = 0
        for x in mlst:
            item = self.qtw_bits.item(kr, kc)
            text = format(gbit[x], '0x') if 'val' == x else gbit[x]
            if item:
                item.setText(text)
            else:
                item = QtWidgets.QTableWidgetItem()
                item.setText(text)
                if 'val' == x:
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.qtw_bits.setItem(kr, kc, item)
                logger.info('bit<{}, {}> = {}'.format(kr, kc, self.qtw_bits.item(kr, kc).text()))
            kc += 1

    def set_addr_data(self):
        maddr = format(self.oreg.addr, '08x')
        mdata = format(self.oreg.val , '08x')
        self.reg_addr.setText(maddr)
        self.reg_data.setText(mdata)

