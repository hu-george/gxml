import os
import re
import xml.etree.ElementTree as ET
import glib
import logging

logger = logging.getLogger(__name__)    # logger for inner thread message


class gXmlMod:
    ''' a module which contain: name, addr, regs, regs_byaddr
        regs/regs_byaddr is an dict:
            key: name/addr which val is the same gXmlReg object
            val: gXmlReg object
    '''
    def __init__(self, vname='module', vaddr=0):
        ''' init class member: name + addr
        :param vname: string  name(module's name)
        :param vaddr: integer addr(module's base address)
        '''
        self.name = vname
        self.addr = vaddr
        self.regs = {}
        self.regs_byaddr = {}

    def insert(self, vobj):
        ''' insert an gXmlReg object to <self.regs>
        :param vobj: type gXmlReg
        :return: None
        '''
        assert isinstance(vobj, gXmlReg)
        maddr = vobj.addr
        mname = vobj.name
        self.regs_byaddr[maddr] = vobj
        self.regs[mname] = vobj

    def append(self, vobj):
        # same as insert
        self.insert(vobj)

    def clear(self):
        # clear <self.regs>
        self.regs_byaddr.clear()
        self.regs.clear()

    def get_reg(self, vval):
        ''' return a gXmlReg object contained in <self.regs>
        can specify reg by name or addr
        :param vval: name/addr
        :return: gXmlReg object
        '''
        if (type(vval) is int):
            return self.regs_byaddr[vval]
        elif (type(vval) is str):
            return self.regs[vval]
        else:
            raise ValueError('type of {} must be int/str'.format(vval))

    def get_lst(self):
        # lst: item = (reg_name, reg_addr), sorted by addr
        mlst = []
        for null,kobj in self.regs.items():
            mname = kobj.name
            maddr = kobj.addr
            mlst.append((mname, maddr))
        return sorted(mlst, key=lambda x:x[1])

    def set_reg(self, vreg, vval):
        ''' modify an <self.regs> object's value
        set gXmlReg.bits's field value, gXmlReg is an <self.regs>'s val
        :param vreg: name/addr(<self.regs>'s key) of the reg
        :param vval: int/gXmlReg.bits
        :return: None
        '''
        mobj = self.get_reg(vreg)
        mobj.set(vval)


class gXmlReg:
    ''' a reg which contain: name, addr, val, bits
        bits is an 2 stage dict:
            the 1st stage dict <key> is each field's name
                               <val> is an 2nd stage dict
            the 2nd stage dict <key>:
                name: <name-field>'s name
                val : <name-field>'s value
                pos : <name-field>'s description ie 3:2 or 1
                msb : <name-field>'s high bit location
                lsb : <name-field>'s low  bit location
                n   : <name-field>'s bit number
    '''
    def __init__(self, vname='reg', vaddr=0):
        ''' init class member: name + addr
        :param vname: string  name
        :param vaddr: integer addr
        '''
        self.name = vname
        self.addr = vaddr
        self.val  = 0
        self.bits = {}
        # {name: dict{name, val, pos, msb, lsb, n}}

    def init(self, vlstdict_bit):
        ''' init(clear + set) class member <bits>
        :param vlstdict_bit: an dict list
            dict keys: 'name, pos, rst', rst <-> bits[*]['val']
        :return: None
        '''
        self.bits.clear()
        mval = 0
        for vdict_bit in vlstdict_bit:
            assert 'name' in vdict_bit.keys()
            assert 'pos'  in vdict_bit.keys()
            assert 'rst'  in vdict_bit.keys()
            # print('{}'.format(vdict_bit))

            mdict = {}
            mdict['name']   = vdict_bit['name']
            mdict['val']    = glib.str2int(vdict_bit['rst'])
            mpos = vdict_bit['pos']
            if ':' in mpos:
                k   = mpos.index(':')
                msb = int(mpos[0:k])
                lsb = int(mpos[k+1:])
                n   = msb - lsb + 1
                gpos = '{:2d}:{:2d}'.format(msb, lsb)
            else:
                msb = int(mpos)
                lsb = msb
                n   = 1
                gpos = '{:5d}'.format(lsb)
            mdict['msb']    = msb
            mdict['lsb']    = lsb
            mdict['n']      = n
            mdict['pos']    = gpos
            self.bits[vdict_bit['name']] = mdict
            mval += (mdict['val'] << lsb)
        self.val = mval

    def __set_bit(self, vbits):
        ''' set class member <self.bits[]['val']> & <self.val>
        :param vbits: 2 stage dict similar with <self.bits>
               vbits can be a subset of <self.bits>
        :return: None
        '''
        mval = self.val
        for mkey in vbits.keys():
            assert mkey  in self.bits.keys()
            assert 'val' in vbits[mkey].keys()

            kval = vbits[mkey]['val']
            self.bits[mkey]['val'] = kval
            msb = self.bits[mkey]['msb']
            lsb = self.bits[mkey]['lsb']
            mval = glib.hset(mval, msb, lsb, kval)
        self.val = mval

    def __set_val(self, vval):
        ''' set class member <self.bits[]['val']> & <self.val>
        :param vval: integer number
        :return: None
        '''
        self.val = vval
        for mkey in self.bits.keys():
            lsb = self.bits[mkey]['lsb']
            n   = self.bits[mkey]['n']
            kval = int(vval >> lsb) & ((1 << n) - 1)
            self.bits[mkey]['val'] = kval

    def get(self):
        ''' get <self.val> & <self.bits>
        :return:
        '''
        return self.val, self.bits

    def set(self, vval):
        ''' set class member <self.bits[]['val']> & <self.val>
        :param vval: type int or self.bits
        :return: None
        '''
        assert (type(vval) is int) or (type(vval) is dict)
        if type(vval) is int : self.__set_val(vval)
        if type(vval) is dict: self.__set_bit(vval)

    def get_lst(self):
        # lst: item = (<dict>bit), sorted by msb with high -> low
        mlst = self.bits.values()
        return sorted(mlst, key=lambda x:int(x['msb']), reverse=True)


class gXmlParser:
    def __init__(self, vpath=r'D:\bt_test\AIC_Register_Tool\xml', vfile=r'aic8800_hard_doc.xml'):
        logger.info('gXmlParser: vpath = {}, vfile = {}'.format(vpath, vfile))
        if os.path.isdir(vpath):
            self.path   = vpath # root xml dir
            self.file   = vfile # root xml file
        elif os.path.isfile(vpath):
            self.set(vpath)
        self.mods_file  = []    # by once   parse_root_xml: 'file_name'
        self.mods_name  = {}    # by once   parse_root_xml: 'modu_name': modu_addr
        self.mods       = {}    # by itered parse_modu_xml: 'modu_name': gXmlMod
        self.strs       = []    # by once   collect       : list of (name, addr) pair, name = all reg.name, bit.name

    def set(self, vfilepath):
        logger.info('gXmlParser.set: vfilepath = {}'.format(vfilepath))
        (self.path, self.file) = os.path.split(vfilepath)

    def load(self):
        mfile = os.path.join(self.path, self.file)
        assert os.path.exists(mfile)
        self.parse_root_xml(mfile)
        self.trav_modu_lst()
        self.collect()

    def parse_root_xml(self, vfile):
        # archive
        # -> include
        # -> instance
        self.mods_file.clear()
        self.mods_name.clear()

        mtree = ET.parse(vfile)
        mroot = mtree.getroot()
        for x in mroot:
            if 'include' in x.tag:
                assert 'file' in x.attrib.keys()
                mfile = x.attrib['file']
                self.mods_file.append(mfile)
                logger.info('parse_root file: {}'.format(mfile))
            elif 'instance' in x.tag:
                assert 'address' in x.attrib.keys()
                assert 'type' in x.attrib.keys()
                addr = x.attrib['address']
                name = x.attrib['type'].lower()
                self.mods_name[name] = int(addr, 16)
                logger.info('parse_root modu: {} = {}'.format(name, addr))

    def parse_modu_xml(self, vfile, vdict_modu):
        # archive
        # -> module
        #    -> reg
        #       -> bits
        #    -> hole
        logger.info('{}'.format(vfile))
        mtree = ET.parse(vfile)
        mroot = mtree.getroot()
        for xmod in mroot:
            if (xmod.tag == 'module') and xmod.attrib.get('name'):
                mod_name = xmod.attrib.get('name').lower()
                if (mod_name in vdict_modu.keys()):
                    break
        else:
            logger.warning('{}\n\tmodule name not in top file'.format(vfile))
            return None

        mod_addr = vdict_modu[mod_name]
        mmod = gXmlMod(mod_name, mod_addr)
        reg_addr = mod_addr
        for x in xmod:
            if 'reg' in x.tag:
                lst_bit = []
                for y in x:
                    if 'bits' == y.tag.lower():
                        assert 'name' in y.attrib.keys()
                        assert 'pos' in y.attrib.keys()
                        assert 'rst' in y.attrib.keys()
                        mdict = y.attrib
                        # mdict['addr'] = reg_addr
                        lst_bit.append(mdict)
                        # tbd: bits may have tag <comment>
                mXmlReg = gXmlReg(x.attrib['name'], reg_addr)
                mXmlReg.init(lst_bit)
                mmod.insert(mXmlReg)
                reg_addr += 4
            elif 'hole' in x.tag:
                assert 'size' in x.attrib.keys()
                reg_addr += int(eval(x.attrib['size'])/8)
        return mmod

    def trav_modu_lst(self):
        self.mods.clear()
        for x in self.mods_file:
            #. mfile = os.path.join(self.path, 'module_xml', x)
            mfile = self.find_file(x)
            if mfile:   #os.path.exists(mfile):
                mmod = self.parse_modu_xml(mfile, self.mods_name)
                if mmod and len(mmod.regs):
                    logger.info('mod: {}'.format(mmod.name))
                    self.mods[mmod.name] = mmod

    def find_file(self, vname):
        for root, dirs, files in os.walk(self.path):
            if vname in files:
                logger.info('mod file: {}, -> {}'.format(vname, root))
                return os.path.join(root, vname)
        else:
            logger.info('mod file: {} not found'.format(vname))
            return None

    def collect(self):
        ''' set self.strs with all regs.name and all bits.name
        :return: str list [regs.name, bits.name]
        '''
        self.strs.clear()
        for kmod in self.mods.values():
            for kreg in kmod.regs.values():
                self.strs.append((kreg.name, kreg.addr))
                for kbit in kreg.bits.keys():
                    self.strs.append((kbit, kreg.addr))

    def filter(self, vprtn):
        ''' filter self.strs with partern
        :param vprtn: patern
        :return: list strs
        '''
        mlst = []
        try:
            for kstr in self.strs:
                if re.search(vprtn, kstr[0], re.I):
                    mlst.append(kstr)
            logger.info('filter: {}, pre = {}, pst = {}'.format(vprtn, len(self.strs), len(mlst)))
        except Exception as err:
            logger.warning('Exception in gxml.filter: {}'.format(repr(err), exc_info=True))
        return mlst

    def get_lst(self):
        # lst: item = (modu_name, modu_addr), sorted by addr
        mlst = []
        for name in self.mods:
            mlst.append((name, self.mods[name].addr))
        return sorted(mlst, key=lambda x:x[1])

    def get_modreg(self, vstr):
        ''' search reg.name or bit.name equals vstr
        :param vstr:
            type(str): reg.name or bit.name
            type(int): reg.addr
        :return: (mod_name, reg_name)
        '''
        if type(vstr) is str:
            for kmod in self.mods.values():
                if vstr in kmod.regs.keys():
                    return (kmod.name, vstr)
                for kreg in kmod.regs.values():
                    if vstr in kreg.bits.keys():
                        return (kmod.name, kreg.name)
        elif type(vstr) is int:
            for kmod in self.mods.values():
                for kreg in kmod.regs.values():
                    if vstr == kreg.addr:
                        return (kmod.name, kreg.name)
        return (None, None)


# print('root-tag:', root.tag, ', root-attrib: ', root.attrib, ', root-text: ', root.text)
# for child in root:
#     print('child-tag:', child.tag, ', child-attrib: ', child.attrib, ', child-text: ', child.text)
#     for sub in child:
#         print('sub-tag:', sub.tag, ', sub-attrib: ', sub.attrib, ', sub-text: ', sub.text)
if __name__ == '__main__':
    mxml = gXmlParser()
    mxml.load()
    print(len(mxml.get_lst()))
    print(len(mxml.strs))
    print((mxml.filter('phi')))
    print((mxml.get_modreg('dphi_fo')))
    #mpath = r'D:\bt_test\AIC_Register_Tool\xml'
    #mfile = os.path.join(mpath, r'aic8800_hard_doc.xml')
    #(lst_file, dict_modu) = parse_root_xml(mfile)
    #trav_lst_file(lst_file, dict_modu)
