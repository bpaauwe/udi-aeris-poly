# Node definition for a daily forecast node

CLOUD = False
try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface
    CLOUD = True

import json
import time
import datetime
import et3

LOGGER = polyinterface.LOGGER

class DailyNode(polyinterface.Node):
    id = 'daily'
    drivers = [
            {'driver': 'GV19', 'value': 0, 'uom': 25},     # day of week
            {'driver': 'GV0', 'value': 0, 'uom': 4},       # high temp
            {'driver': 'GV1', 'value': 0, 'uom': 4},       # low temp
            {'driver': 'CLIHUM', 'value': 0, 'uom': 22},   # humidity
            {'driver': 'BARPRES', 'value': 0, 'uom': 118}, # pressure
            {'driver': 'GV13', 'value': 0, 'uom': 25},     # conditions
            {'driver': 'GV14', 'value': 0, 'uom': 22},     # clouds
            {'driver': 'GV4', 'value': 0, 'uom': 49},      # wind speed
            {'driver': 'GV16', 'value': 0, 'uom': 71},     # UV index
            {'driver': 'GV20', 'value': 0, 'uom': 106},    # mm/day
            ]
    uom = {'GV19': 25,
            'GV0': 4,
            'GV1': 4,
            'CLIHUM': 22,
            'BARPRES': 118,
            'GV13': 25,
            'GV14': 22,
            'GV4': 49,
            'GV16': 71,
            'GV20': 107,
            }

    def set_driver_uom(self, units):
        if units == 'metric':
            self.uom['BARPRES'] = 118
            self.uom['GV0'] = 4
            self.uom['GV1'] = 4
            self.uom['GV19'] = 25
            self.uom['GV4'] = 49
        elif units == 'imperial':
            self.uom['BARPRES'] = 118
            self.uom['GV0'] = 17
            self.uom['GV1'] = 17
            self.uom['GV19'] = 25
            self.uom['GV4'] = 48

    def set_units(self, units):
        try:
            for driver in self.drivers:
                if units == 'imperial':
                    if driver['driver'] == 'BARPRES': driver['uom'] = 118
                    if driver['driver'] == 'GV0': driver['uom'] = 17
                    if driver['driver'] == 'GV1': driver['uom'] = 17
                    if driver['driver'] == 'GV19': driver['uom'] = 25
                    if driver['driver'] == 'GV4': driver['uom'] = 48
                elif units == 'metric':
                    if driver['driver'] == 'BARPRES': driver['uom'] = 118
                    if driver['driver'] == 'GV0': driver['uom'] = 4
                    if driver['driver'] == 'GV1': driver['uom'] = 4
                    if driver['driver'] == 'GV19': driver['uom'] = 25
                    if driver['driver'] == 'GV4': driver['uom'] = 49
        except:
            for drv in self.drivers:
                if units == 'imperial':
                    if drv == 'BARPRES': self.drivers[drv]['uom'] = 118
                    if drv == 'GV0': self.drivers[drv]['uom'] = 17
                    if drv == 'GV1': self.drivers[drv]['uom'] = 17
                    if drv == 'GV19': self.drivers[drv]['uom'] = 25
                    if drv == 'GV4': self.drivers[drv]['uom'] = 48
                elif units == 'metric':
                    if drv == 'BARPRES': self.drivers[drv]['uom'] = 118
                    if drv == 'GV0': self.drivers[drv]['uom'] = 4
                    if drv == 'GV1': self.drivers[drv]['uom'] = 4
                    if drv == 'GV19': self.drivers[drv]['uom'] = 25
                    if drv == 'GV4': self.drivers[drv]['uom'] = 49


    def mm2inch(self, mm):
        return mm/25.4

    def update_forecast(self, forecast, latitude, elevation, plant_type, units):

        epoch = int(forecast['dt'])
        dow = time.strftime("%w", time.gmtime(epoch))
        LOGGER.info('Day of week = ' + dow)

        humidity = (forecast['Hmin'] + forecast['Hmax']) / 2
        self.setDriver('CLIHUM', round(humidity, 0), True, False, self.uom['CLIHUM'])
        self.setDriver('BARPRES', round(forecast['pressure'], 1), True, False, self.uom['BARPRES'])
        self.setDriver('GV0', round(forecast['temp_max'], 1), True, False, self.uom['GV0'])
        self.setDriver('GV1', round(forecast['temp_min'], 1), True, False, self.uom['GV1'])
        self.setDriver('GV14', round(forecast['clouds'], 0), True, False, self.uom['GV14'])
        self.setDriver('GV4', round(forecast['speed'], 1), True, False, self.uom['GV4'])

        self.setDriver('GV19', int(dow), True, False, self.uom['GV19'])
        self.setDriver('GV13', forecast['weather'], True, False, self.uom['GV13'])
        self.setDriver('GV16', round(forecast['uv'], 1), True, False, self.uom['GV16'])

        # Calculate ETo
        #  Temp is in degree C and windspeed is in m/s, we may need to
        #  convert these.
        J = datetime.datetime.fromtimestamp(epoch).timetuple().tm_yday

        Tmin = forecast['temp_min']
        Tmax = forecast['temp_max']
        Ws = forecast['speed']
        if units != 'si':
            LOGGER.info('Conversion of temperature/wind speed required')
            Tmin = et3.FtoC(Tmin)
            Tmax = et3.FtoC(Tmax)
            Ws = et3.mph2ms(Ws)

        et0 = et3.evapotranspriation(Tmax, Tmin, None, Ws, float(elevation), forecast['Hmax'], forecast['Hmin'], latitude, float(plant_type), J)
        self.setDriver('GV20', round(et0, 2), True, False)
        LOGGER.info("ETo = %f %f" % (et0, self.mm2inch(et0)))


