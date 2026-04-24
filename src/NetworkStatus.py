
import gi
import os

try:
    gi.require_version("NM", "1.0")
    from gi.repository import NMi

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

except ImportError:

    def get_active_interfaces():
        net_path = "/sys/class/net"
        active = []
        for iface in os.listdir(net_path):
            operstate = f"{net_path}/{iface}/operstate"
            if os.path.exists(operstate):
                with open(operstate) as f:
                    if f.read().strip() == "up":
                        active.append(iface)
        return active

    def isMobileData():
        isMobile = True
        for iface in get_active_interfaces():
            if iface.startswith(("wlan", "wl")):
                isMobile = False
            elif iface.startswith(("eth", "en")):
                isMobile = False
        return isMobile

