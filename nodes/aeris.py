#!/usr/bin/env python3
"""
Polyglot v2 node server AERIS weather data
Copyright (C) 2019,2020 Robert Paauwe
"""

try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface
import sys
import time
import datetime
import requests
import socket
import math
import re
import json
import node_funcs
from nodes import aeris_daily
from nodes import uom
from nodes import weather_codes as wx

LOGGER = polyinterface.LOGGER

@node_funcs.add_functions_as_methods(node_funcs.functions)
class Controller(polyinterface.Controller):
    id = 'weather'
    #id = 'controller'
    hint = [0,0,0,0]
    def __init__(self, polyglot):
        super(Controller, self).__init__(polyglot)
        self.name = 'AERIS Weather'
        self.address = 'weather'
        self.primary = self.address
        self.configured = False
        self.latitude = 0
        self.longitude = 0
        self.force = True
        self.tag = {}

        self.params = node_funcs.NSParameters([{
            'name': 'ClientID',
            'default': 'set me',
            'isRequired': True,
            'notice': 'AERIS Client ID must be set',
            },
            {
            'name': 'ClientSecret',
            'default': 'set me',
            'isRequired': True,
            'notice': 'AERIS Client Secret must be set',
            },
            {
            'name': 'Location',
            'default': 'set me',
            'isRequired': True,
            'notice': 'AERIS location must be set',
            },
            {
             'name': 'Units',
            'default': 'imperial',
            'isRequired': False,
            'notice': '',
            },
            {
            'name': 'Forecast Days',
            'default': '0',
            'isRequired': False,
            'notice': '',
            },
            {
            'name': 'Elevation',
            'default': '0',
            'isRequired': False,
            'notice': '',
            },
            {
            'name': 'Plant Type',
            'default': '0.23',
            'isRequired': False,
            'notice': '',
            },
            ])


        self.poly.onConfig(self.process_config)

    # Process changes to customParameters
    def process_config(self, config):
        (valid, changed) = self.params.update_from_polyglot(config)
        if changed and not valid:
            LOGGER.debug('-- configuration not yet valid')
            self.removeNoticesAll()
            self.params.send_notices(self)
        elif changed and valid:
            LOGGER.debug('-- configuration is valid')
            self.removeNoticesAll()
            self.configured = True
            if self.params.isSet('Forecast Days'):
                self.discover()
        elif valid:
            LOGGER.debug('-- configuration not changed, but is valid')

    def start(self):
        LOGGER.info('Starting node server')
        self.check_params()
        self.set_tags(self.params.get('Units'))
        self.discover()
        LOGGER.info('Node server started')

        # Do an initial query to get filled in as soon as possible
        self.query_conditions()
        self.query_forecast()
        self.force = False

    def longPoll(self):
        self.query_forecast()

    def shortPoll(self):
        self.query_conditions()

    # Query for the condition an forecast data
    def get_weather_data(self, extra, lat=None, long=None):
        request = 'http://api.aerisapi.com/' + extra + '/'

        request += self.params.get('Location')
        request += '?client_id=' + self.params.get('ClientID')
        request += '&client_secret=' + self.params.get('ClientSecret')

        if extra == 'forecasts':
            request += '&filter=mdnt2mdnt'
            request += '&precise'
            request += '&limit=12'

        if extra == 'observations/summary':
            request += '&fields=periods.summary.precip'

        #FIXME: add unit support if available
        #request += '&units=' + self.units

        LOGGER.debug('request = %s' % request)

        try:
            c = requests.get(request)
            jdata = c.json()
            c.close()
            LOGGER.debug(jdata)
        except:
            LOGGER.error('HTTP request failed for api.aerisapi.com')
            jdata = None

        return jdata

    def set_tags(self, units):
        if units == 'metric':
            self.tag['temperature'] = 'tempC'
            self.tag['humidity'] = 'humidity'
            self.tag['pressure'] = 'pressureMB'
            self.tag['windspeed'] = 'windSpeedKPH'
            self.tag['gustspeed'] = 'windGustKPH'
            self.tag['winddir'] = 'windDirDEG'
            self.tag['visibility'] = 'visibilityKM'
            self.tag['precipitation'] = 'precipMM'
            self.tag['snow'] = 'snowDepthCM'
            self.tag['snowf'] = 'snowCM'
            self.tag['dewpoint'] = 'dewpointC'
            self.tag['heatindex'] = 'heatindexC'
            self.tag['windchill'] = 'windchillC'
            self.tag['feelslike'] = 'feelslikeC'
            self.tag['solarrad'] = 'solradWM2'
            self.tag['sky'] = 'sky'
            self.tag['temp_min'] = 'minTempC'
            self.tag['temp_max'] = 'maxTempC'
            self.tag['humidity_min'] = 'minHumidity'
            self.tag['humidity_max'] = 'maxHumidity'
            self.tag['wind_min'] = 'windSpeedMinKPH'
            self.tag['wind_max'] = 'windSpeedMaxKPH'
            self.tag['winddir_min'] = 'windDirMinDEG'
            self.tag['winddir_max'] = 'windDirMaxDEG'
            self.tag['uv'] = 'uvi'
            self.tag['pop'] = 'pop'
            self.tag['timestamp'] = 'timestamp'
            self.tag['precip_summary'] = 'totalMM'
        else:
            self.tag['temperature'] = 'tempF'
            self.tag['humidity'] = 'humidity'
            self.tag['pressure'] = 'pressureIN'
            self.tag['windspeed'] = 'windSpeedMPH'
            self.tag['gustspeed'] = 'windGustMPH'
            self.tag['winddir'] = 'windDirDEG'
            self.tag['visibility'] = 'visibilityMI'
            self.tag['precipitation'] = 'precipIN'
            self.tag['snow'] = 'snowDepthIN'
            self.tag['snowf'] = 'snowIN'
            self.tag['dewpoint'] = 'dewpointF'
            self.tag['heatindex'] = 'heatindexF'
            self.tag['windchill'] = 'windchillF'
            self.tag['feelslike'] = 'feelslikeF'
            self.tag['solarrad'] = 'solradWM2'
            self.tag['sky'] = 'sky'
            self.tag['temp_min'] = 'minTempF'
            self.tag['temp_max'] = 'maxTempF'
            self.tag['humidity_min'] = 'minHumidity'
            self.tag['humidity_max'] = 'maxHumidity'
            self.tag['wind_min'] = 'windSpeedMinMPH'
            self.tag['wind_max'] = 'windSpeedMaxMPH'
            self.tag['winddir_min'] = 'windDirMinDEG'
            self.tag['winddir_max'] = 'windDirMaxDEG'
            self.tag['uv'] = 'uvi'
            self.tag['pop'] = 'pop'
            self.tag['timestamp'] = 'timestamp'
            self.tag['precip_summary'] = 'totalIN'

    def query_conditions(self):
        # Query for the current conditions. We can do this fairly
        # frequently, probably as often as once a minute.

        if not self.configured:
            LOGGER.info('Skipping connection because we aren\'t configured yet.')
            return

        precipitation = 0

        try:
            jdata = self.get_weather_data('observations')
            if jdata == None:
                LOGGER.error('Current condition query returned no data')
                return
            '''
            Data from query has multiple units. Which one we want to use depends
            on what the user has selected.  Since we set the node to metric by
            default, lets just use those for testing.
            '''
        
            #jdata['response']['ob']['tempC']
            if 'response' not in jdata:
                LOGGER.error('No response object in query response.')
                return

            if 'ob' not in jdata['response']:
                LOGGER.error('No observation object in query response.')
                return

            if 'loc' in jdata['response']:
                if 'lat' in jdata['response']['loc']:
                    self.latitude = float(jdata['response']['loc']['lat'])
                else:
                    LOGGER.error('No latitude data in response.')
            else:
                LOGGER.error('No location data in response.')

            ob = jdata['response']['ob']

            self.update_driver('CLITEMP', ob[self.tag['temperature']])
            self.update_driver('CLIHUM', ob[self.tag['humidity']])
            self.update_driver('BARPRES', ob[self.tag['pressure']])
            self.update_driver('SPEED', ob[self.tag['windspeed']])
            self.update_driver('GV5', ob[self.tag['gustspeed']])
            self.update_driver('WINDDIR', ob[self.tag['winddir']])
            self.update_driver('DISTANC', ob[self.tag['visibility']])
            self.update_driver('DEWPT', ob[self.tag['dewpoint']])
            self.update_driver('GV3', ob[self.tag['heatindex']])
            self.update_driver('GV4', ob[self.tag['windchill']])
            self.update_driver('GV2', ob[self.tag['feelslike']])
            self.update_driver('SOLRAD', ob[self.tag['solarrad']])
            self.update_driver('UV', ob[self.tag['uv']])
            self.update_driver('GV15', ob[self.tag['snow']])
            # Weather conditions:
            #  ob['weather']
            #  ob['weatherShort']
            #  ob['weatherCoded']
            #    [coverage] : [intensity] : [weather]
            #     -- these can be mapped to strings

            LOGGER.debug('**>>> WeatherCoded = ' + ob['weatherCoded']);
            weather = ob['weatherCoded'].split(':')[0]
            self.update_driver('GV11', wx.coverage_codes(weather))
            weather = ob['weatherCoded'].split(':')[1]
            self.update_driver('GV12', wx.intensity_codes(weather))
            weather = ob['weatherCoded'].split(':')[2]
            LOGGER.debug('>>>  weather = ' + weather)
            self.update_driver('GV13', wx.weather_codes(weather))
            LOGGER.debug('>>>  Setting GV13 to ' + str(wx.weather_codes(weather)))

            # cloud cover
            #  ob['cloudsCoded'] ??
            self.update_driver('GV14', ob['sky'])

            # precipitation
            precipitation = ob[self.tag['precipitation']]

            '''
            TODO:
            - weather
            - snow depth
            - ceiling
            - light
            '''

        except Exception as e:
            LOGGER.error('Current observation update failure')
            LOGGER.error(e)

        try:
            # Get precipitation summary
            jdata = self.get_weather_data('observations/summary')
            if jdata == None:
                LOGGER.error('Precipitation summary query returned no data')
                return
            if 'response' not in jdata:
                LOGGER.error('No response object in query response.')
                return
            #LOGGER.debug(jdata)
            if type(jdata['response']) is list:
                rd = jdata['response'][0]['periods'][0]['summary']
            else:
                rd = jdata['response']['periods'][0]['summary']
            if 'precip' in rd:
                LOGGER.debug('Setting precipitation to: ' + str(rd['precip'][self.tag['precip_summary']]))
                self.update_driver('GV6', rd['precip'][self.tag['precip_summary']])
        except Exception as e:
            LOGGER.error('Precipitation summary update failure')
            LOGGER.error(e)
            self.update_driver('GV6', precipitation)
          try:
            # Calculate ETo based on actual values
            # Calculate ETo
            #  Temp is in degree C and windspeed is in m/s, we may need to
            #  convert these.
            epoch = int(rd['timestamp'])
            J = datetime.datetime.fromtimestamp(epoch).timetuple().tm_yday
            self.units = self.params.get('Units')
            Ws = rd['wind'][self.tag['wind_avg']]
            Tmax = rd['temp'][self.tag['temp_max_summ']]
            Tmin = rd['temp'][self.tag['temp_min_summ']]
            Tavg = rd['temp'][self.tag['temp_avg']]
            SolRad = rd['solrad'][self.tag['solarrad_summ']]
            if SolRad == 'Null' or SolRad == 0:
               SolRad = None
            Elevation = float(self.params.get('Elevation'))
            Hmax = rd['rh'][self.tag['humidity_max_summ']]
            Hmin = rd['rh'][self.tag['humidity_min_summ']]
            Latitude = self.latitude
            if self.units != 'metric':
                LOGGER.info('Conversion of temperature/wind speed required')
                Tmin = et3.FtoC(Tmin)
                Tmax = et3.FtoC(Tmax)
                Tavg = et3.FtoC(Tavg)              
                Ws = et3.mph2ms(Ws)
            else:
                LOGGER.info('Conversion of wind speed required')
                Ws = et3.kph2ms(Ws)            
            LOGGER.debug('Tmax= '+str(Tmax)+'C')
            LOGGER.debug('Tmin= '+str(Tmin)+'C')           
            LOGGER.debug('Tavg= '+str(Tavg)+'C')  
            LOGGER.debug('Elevation= '+str(Elevation))
            LOGGER.debug('Hmax= '+str(Hmax))
            LOGGER.debug('Hmin= '+str(Hmin))
            LOGGER.debug('SolRad= '+str(SolRad)+' WM2')  
            LOGGER.debug('J= '+str(J))
            LOGGER.debug('Latitude= '+str(Latitude))
            LOGGER.debug('Setting Ws: %f m/s' % (Ws))
            et0 = et3.evapotranspriation(Tmax, Tmin, SolRad, Ws, Elevation, Hmax, Hmin, Latitude, float(self.params.get('Plant Type')), J, Tavg)
            if self.units == 'metric'
               self.update_driver('GV20', round(et0, 2))
            else:
               self.update_driver('GV20', self.mm2inch(et0), 3)
            LOGGER.info("ETo Actuals= %f %f" % (et0, self.mm2inch(et0)))
        except Exception as e:
            LOGGER.error('ETo based on actuals update failure')
            LOGGER.error(e)              

    def query_forecast(self):
        if not self.configured:
            LOGGER.info('Skipping connection because we aren\'t configured yet.')
            return

        try:
            jdata = self.get_weather_data('forecasts')
            if jdata == None:
                LOGGER.error('Current condition query returned no data')
                return

            # Records are for each day, midnight to midnight
            day = 0
            if 'periods' in jdata['response'][0]:
                LOGGER.debug('Processing periods: %d' % len(jdata['response'][0]['periods']))
                for forecast in jdata['response'][0]['periods']:
                    address = 'forecast_' + str(day)
                    LOGGER.debug(' >>>>   period ' + forecast['dateTimeISO'] + '  ' + address)
                    self.nodes[address].update_forecast(forecast, self.latitude, self.params.get('Elevation'), self.params.get('Plant Type'), self.tag, self.force)
                    day += 1
                    if day >= int(self.params.get('Forecast Days')):
                        return

        except Exception as e:
            LOGGER.error('Forecast data failure: ' + str(e))


    def query(self):
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def discover(self, *args, **kwargs):
        # Create any additional nodes here
        LOGGER.info("In Discovery...")

        num_days = int(self.params.get('Forecast Days'))
        if num_days < 14:
            # delete any extra days
            for day in range(num_days, 7):
                address = 'forecast_' + str(day)
                try:
                    self.delNode(address)
                except:
                    LOGGER.debug('Failed to delete node ' + address)

        for day in range(0,num_days):
            address = 'forecast_' + str(day)
            title = 'Forecast ' + str(day)
            try:
                node = aeris_daily.DailyNode(self, self.address, address, title)
                self.addNode(node)
            except:
                LOGGER.error('Failed to create forecast node ' + title)

        self.set_driver_uom(self.params.get('Units'))

    # Delete the node server from Polyglot
    def delete(self):
        LOGGER.info('Removing node server')

    def stop(self):
        LOGGER.info('Stopping node server')

    def update_profile(self, command):
        st = self.poly.installprofile()
        return st

    def check_params(self):
        self.removeNoticesAll()

        if self.params.get_from_polyglot(self):
            LOGGER.debug('All required parameters are set!')
            self.configured = True
            if int(self.params.get('Forecast Days')) > 12:
                addNotice('Number of days of forecast data is limited to 12 days', 'forecast')
                self.params.set('Forecast Days', 12)
        else:
            LOGGER.debug('Configuration required.')
            LOGGER.debug('ClientID = ' + self.params.get('ClientID'))
            LOGGER.debug('ClientSecret = ' + self.params.get('ClientSecret'))
            LOGGER.debug('Location = ' + self.params.get('Location'))
            self.params.send_notices(self)

    # Set the uom dictionary based on current user units preference
    def set_driver_uom(self, units):
        LOGGER.info('Configure driver units to ' + units)
        self.uom = uom.get_uom(units)
        for day in range(0, int(self.params.get('Forecast Days'))):
            address = 'forecast_' + str(day)
            self.nodes[address].set_driver_uom(units)

    def remove_notices_all(self, command):
        self.removeNoticesAll()

    def set_logging_level(self, level=None):
        if level is None:
            try:
                # level = self.getDriver('GVP')
                level = self.get_saved_log_level()
            except:
                LOGGER.error('set_logging_level: get saved log level failed.')

            if level is None:
                level = 30

            level = int(level)
        else:
            level = int(level['value'])

        # self.setDriver('GVP', level, True, True)
        self.save_log_level(level)
        LOGGER.info('set_logging_level: Setting log level to %d' % level)
        LOGGER.setLevel(level)

    commands = {
            'UPDATE_PROFILE': update_profile,
            'REMOVE_NOTICES_ALL': remove_notices_all,
            'DEBUG': set_logging_level,
            }

    # For this node server, all of the info is available in the single
    # controller node.
    drivers = [
            {'driver': 'ST', 'value': 1, 'uom': 2},   # node server status
            {'driver': 'CLITEMP', 'value': 0, 'uom': 4},   # temperature
            {'driver': 'CLIHUM', 'value': 0, 'uom': 22},   # humidity
            {'driver': 'DEWPT', 'value': 0, 'uom': 4},     # dewpoint
            {'driver': 'BARPRES', 'value': 0, 'uom': 117}, # pressure
            {'driver': 'WINDDIR', 'value': 0, 'uom': 76},  # direction
            {'driver': 'SPEED', 'value': 0, 'uom': 32},    # wind speed
            {'driver': 'GV5', 'value': 0, 'uom': 32},      # gust speed
            {'driver': 'GV2', 'value': 0, 'uom': 4},       # feels like
            {'driver': 'GV3', 'value': 0, 'uom': 4},       # heat index
            {'driver': 'GV4', 'value': 0, 'uom': 4},       # wind chill
            {'driver': 'GV6', 'value': 0, 'uom': 82},      # rain
            {'driver': 'GV15', 'value': 0, 'uom': 82},     # snow depth
            {'driver': 'GV11', 'value': 0, 'uom': 25},     # climate coverage
            {'driver': 'GV12', 'value': 0, 'uom': 25},     # climate intensity
            {'driver': 'GV13', 'value': 0, 'uom': 25},     # climate conditions
            {'driver': 'GV14', 'value': 0, 'uom': 22},     # cloud conditions
            {'driver': 'DISTANC', 'value': 0, 'uom': 83},  # visibility
            {'driver': 'SOLRAD', 'value': 0, 'uom': 74},   # solar radiataion
            {'driver': 'UV', 'value': 0, 'uom': 71},       # uv index
            {'driver': 'GVP', 'value': 30, 'uom': 25},     # log level
            ]


