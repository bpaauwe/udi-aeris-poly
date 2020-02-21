# Node definition for a daily forecast node

try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface

import json
import time
import datetime
from nodes import et3
from nodes import uom
import node_funcs

LOGGER = polyinterface.LOGGER

@node_funcs.add_functions_as_methods(node_funcs.functions)
class DailyNode(polyinterface.Node):
    id = 'daily'
    # TODO: add wind speed min/max, pop, winddir min/max
    drivers = [
            {'driver': 'GV19', 'value': 0, 'uom': 25},     # day of week
            {'driver': 'GV0', 'value': 0, 'uom': 4},       # high temp
            {'driver': 'GV1', 'value': 0, 'uom': 4},       # low temp
            {'driver': 'CLIHUM', 'value': 0, 'uom': 22},   # humidity
            {'driver': 'BARPRES', 'value': 0, 'uom': 117}, # pressure
            {'driver': 'GV11', 'value': 0, 'uom': 25},     # coverage
            {'driver': 'GV12', 'value': 0, 'uom': 25},     # intensity
            {'driver': 'GV13', 'value': 0, 'uom': 25},     # weather
            {'driver': 'GV14', 'value': 0, 'uom': 22},     # clouds
            {'driver': 'GV4', 'value': 0, 'uom': 49},      # wind speed
            {'driver': 'GV5', 'value': 0, 'uom': 49},      # gust speed
            {'driver': 'GV6', 'value': 0, 'uom': 82},      # precipitation
            {'driver': 'GV7', 'value': 0, 'uom': 49},      # wind speed max
            {'driver': 'GV8', 'value': 0, 'uom': 49},      # wind speed min
            {'driver': 'GV18', 'value': 0, 'uom': 22},     # pop
            {'driver': 'GV16', 'value': 0, 'uom': 71},     # UV index
            {'driver': 'GV20', 'value': 0, 'uom': 106},    # mm/day
            ]
    uom = {'GV19': 25,
            'GV0': 4,
            'GV1': 4,
            'CLIHUM': 22,
            'BARPRES': 117,
            'GV11': 25,
            'GV12': 25,
            'GV13': 25,
            'GV14': 22,
            'GV4': 49,
            'GV5': 49,
            'GV6': 82,
            'GV7': 49,
            'GV8': 49,
            'GV16': 71,
            'GV20': 107,
            'GV18': 22,
            }

    def set_driver_uom(self, units):
        self.uom = uom.get_uom(units)
        self.units = units

    def mm2inch(self, mm):
        return mm/25.4


    '''
        self.fcast['temp_max']
        self.fcast['temp_min']
        self.fcast['Hmax']
        self.fcast['Hmin']
        self.fcast['pressure']
        self.fcast['speed']
        self.fcast['speed_max']
        self.fcast['speed_min']
        self.fcast['gust']
        self.fcast['gust_max']
        self.fcast['gust_min']
        self.fcast['dir']
        self.fcast['dir_max']
        self.fcast['dir_min']
        self.fcast['timestamp']
        self.fcast['pop']
        self.fcast['precip']
        self.fcast['uv']
        self.fcast['clouds']
    '''
    def update_forecast(self, forecast, latitude, elevation, plant_type, units):

        epoch = int(forecast['timestamp'])
        dow = time.strftime("%w", time.gmtime(epoch))
        LOGGER.info('Day of week = ' + dow)

        humidity = (forecast['Hmin'] + forecast['Hmax']) / 2
        self.update_driver('CLIHUM', round(humidity, 0))
        self.update_driver('BARPRES', round(forecast['pressure'], 1))
        self.update_driver('GV0', round(forecast['temp_max'], 1))
        self.update_driver('GV1', round(forecast['temp_min'], 1))
        self.update_driver('GV14', round(forecast['clouds'], 0))
        self.update_driver('GV4', round(forecast['speed'], 1))
        self.update_driver('GV5', round(forecast['gust'], 1))
        self.update_driver('GV6', round(forecast['precip'], 1))
        self.update_driver('GV7', round(forecast['speed_max'], 1))
        self.update_driver('GV8', round(forecast['speed_min'], 1))

        self.update_driver('GV19', int(dow))
        self.update_driver('GV16', round(forecast['uv'], 1))
        self.update_driver('GV18', round(forecast['pop'], 1))
        self.update_driver('GV11', forecast['coverage'])
        self.update_driver('GV12', forecast['intensity'])
        self.update_driver('GV13', forecast['weather'])

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
        else:
            Ws = et3.kph2ms(Ws)

        et0 = et3.evapotranspriation(Tmax, Tmin, None, Ws, float(elevation), forecast['Hmax'], forecast['Hmin'], latitude, float(plant_type), J)
        self.update_driver('GV20', round(et0, 2))
        LOGGER.info("ETo = %f %f" % (et0, self.mm2inch(et0)))
