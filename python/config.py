import json

class SingletonInstance:
  __instance = None

  @classmethod
  def __getInstance(cls):
    return cls.__instance

  @classmethod
  def instance(cls, *args, **kargs):
    cls.__instance = cls(*args, **kargs)
    cls.instance = cls.__getInstance
    return cls.__instance

class Config(SingletonInstance):
    _vals = {
            "CctvIpAddr": "192.168.1.100",
            "CctvPortNo": 80,
            "CctvID": "carpos",
            "CctvPassword": "carpos1910",
            "ModbusPortNo": 502,
            "Left":170,
            "Top":120,
            "Right":550,
            "Bottom":300,
            "Reboot":0
            }

    def __init__(self):
        pass

    @classmethod
    def load(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as cfile:
                self._vals = json.load(cfile)
            return True
        except:
            return False

    @classmethod
    def save(self, path):
        try:
            with open(path, 'w', encoding='utf-8') as cfile:
                json.dump(self._vals, cfile, indent='\t')
            return True
        except:
            return False

    @property
    def cctv_ip_addr(self):
        return self._vals['CctvIpAddr']

    @cctv_ip_addr.setter
    def cctv_ip_addr(self, ipAddr):
        self._vals['CctvIpAddr'] = ipAddr

    @property
    def cctv_port_no(self):
        return self._vals['CctvPortNo']

    @cctv_port_no.setter
    def cctv_port_no(self, portno):
        self._vals['CctvPortNo'] = portno

    @property
    def cctv_id(self):
        return self._vals['CctvID']

    @cctv_id.setter
    def cctv_id(self, cctvid):
        self._vals['CctvID'] = cctvid

    @property
    def cctv_passwd(self):
        return self._vals['CctvPassword']

    @cctv_passwd.setter
    def cctv_passwd(self, passwd):
        self._vals['CctvPassword'] = passwd
    @property
    def cctv_modbus_port_no(self):
        return self._vals['ModbusPortNo']

    @cctv_modbus_port_no.setter
    def cctv_modbus_port_no(self, modbusportno):
        self._vals['ModbusPortNo'] = modbusportno

    @property
    def cctv_roi_left(self):
        return self._vals['Left']

    @cctv_roi_left.setter
    def cctv_roi_left(self, left):
        self._vals['Left'] = left

    @property
    def cctv_roi_top(self):
        return self._vals['Top']

    @cctv_roi_top.setter
    def cctv_roi_top(self, top):
        self._vals['Top'] = top

    @property
    def cctv_roi_right(self):
        return self._vals['Right']

    @cctv_roi_right.setter
    def cctv_roi_right(self, right):
        self._vals['Right'] = right

    @property
    def cctv_roi_bottom(self):
        return self._vals['Bottom']

    @cctv_roi_bottom.setter
    def cctv_roi_bottom(self, bottom):
        self._vals['Bottom'] = bottom

    @property
    def cctv_reboot(self):
        return self._vals['Reboot']

    @cctv_reboot.setter
    def cctv_roi_bottom(self, reboot):
        self._vals['Reboot'] = reboot


if __name__ == "__main__":
    print('Config class test...')
    cfg = Config.instance()
    cfg.load('config.json')

    print('CCTV IP Addr: ' + cfg.cctv_ip_addr)

    cfg.save('cfg.json')
