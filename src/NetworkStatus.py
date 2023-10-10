
import gi

gi.require_version("NM", "1.0")
from gi.repository import NM

def isMobileData():
    """ Return True if not on Wifi and potentially on metered 4g/phone connection """
    isMobile = True
    client = NM.Client.new(None)
    devices = client.get_all_devices()
    for device in devices:
        if device.is_real() and device.get_state() == NM.DeviceState.ACTIVATED:
            if type(device) == NM.DeviceEthernet:
                isMobile = False
            if type(device) == NM.DeviceWifi:
                isMobile = False
    return isMobile

if __name__ == '__main__':
    print('Mobile data status: %s' % (isMobileData(), ))
