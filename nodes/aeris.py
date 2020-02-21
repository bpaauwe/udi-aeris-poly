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
            self.tag['windspeed'] = 'windKPH'
            self.tag['gustspeed'] = 'windGustKPH'
            self.tag['winddir'] = 'windDirDEG'
            self.tag['visibility'] = 'visibilityKM'
            self.tag['precipitation'] = 'precipMM'
            self.tag['dewpoint'] = 'dewpointC'
            self.tag['heatindex'] = 'heatindexC'
            self.tag['windchill'] = 'windchillC'
            self.tag['feelslike'] = 'feelslikeC'
            self.tag['solarrad'] = 'solradWM2'
            self.tag['sky'] = 'sky'
            self.tag['temp_min'] = 'minTempC'
            self.tag['temp_max'] = 'maxTempC'
            self.tag['humdity_min'] = 'minHumidity'
            self.tag['humdity_max'] = 'maxHumidity'
            self.tag['wind_min'] = 'windSpeedMinKPH'
            self.tag['wind_max'] = 'windSpeedMaxKPH'
        else:
            self.tag['temperature'] = 'tempF'
            self.tag['humidity'] = 'humidity'
            self.tag['pressure'] = 'pressureIN'
            self.tag['windspeed'] = 'windMPH'
            self.tag['gustspeed'] = 'windGustMPH'
            self.tag['winddir'] = 'windDirDEG'
            self.tag['visibility'] = 'visibilityMI'
            self.tag['precipitation'] = 'precipIN'
            self.tag['dewpoint'] = 'dewpointF'
            self.tag['heatindex'] = 'heatindexF'
            self.tag['windchill'] = 'windchillF'
            self.tag['feelslike'] = 'feelslikeF'
            self.tag['solarrad'] = 'solradWM2'
            self.tag['sky'] = 'sky'
            self.tag['temp_min'] = 'minTempF'
            self.tag['temp_max'] = 'maxTempF'
            self.tag['humdity_min'] = 'minHumidity'
            self.tag['humdity_max'] = 'maxHumidity'
            self.tag['wind_min'] = 'windSpeedMinMPH'
            self.tag['wind_max'] = 'windSpeedMaxMPH'

    def query_conditions(self):
        # Query for the current conditions. We can do this fairly
        # frequently, probably as often as once a minute.

        if not self.configured:
            LOGGER.info('Skipping connection because we aren\'t configured yet.')
            return


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

            ob = jdata['response']['ob']

            self.update_driver('CLITEMP', ob[self.tag['temperature']])
            self.update_driver('CLIHUM', ob[self.tag['humidity']])
            self.update_driver('BARPRES', ob[self.tag['pressure']])
            self.update_driver('GV4', ob[self.tag['windspeed']])
            self.update_driver('GV5', ob[self.tag['gustspeed']])
            self.update_driver('WINDDIR', ob[self.tag['winddir']])
            self.update_driver('GV15', ob[self.tag['visibility']])
            self.update_driver('GV6', ob[self.tag['precipitation']])
            self.update_driver('DEWPT', ob[self.tag['dewpoint']])
            self.update_driver('GV0', ob[self.tag['heatindex']])
            self.update_driver('GV1', ob[self.tag['windchill']])
            self.update_driver('GV2', ob[self.tag['feelslike']])
            self.update_driver('SOLRAD', ob[self.tag['solarrad']])
            # Weather conditions:
            #  ob['weather']
            #  ob['weatherShort']
            #  ob['weatherCoded']
            #    [coverage] : [intensity] : [weather]
            #     -- these can be mapped to strings

            LOGGER.debug('**>>> WeatherCoded = ' + ob['weatherCoded']);
            weather = ob['weatherCoded'].split(':')[0]
            self.update_driver('GV11', self.coverage_codes(weather))
            weather = ob['weatherCoded'].split(':')[1]
            self.update_driver('GV12', self.intensity_codes(weather))
            weather = ob['weatherCoded'].split(':')[2]
            LOGGER.debug('>>>  weather = ' + weather)
            self.update_driver('GV13', self.weather_codes(weather))
            LOGGER.debug('>>>  Setting GV13 to ' + str(self.weather_codes(weather)))

            # cloud cover
            #  ob['cloudsCoded'] ??
            self.update_driver('GV14', ob['sky'])

            '''
            TODO:
            - altimeter?
            - weather
            - snow depth
            - ceiling
            - light
            '''

    def query_forecast(self):
        if not self.configured:
            LOGGER.info('Skipping connection because we aren\'t configured yet.')
            return

        try:
            jdata = self.get_weather_data('observations')
            if jdata == None:
                LOGGER.error('Current condition query returned no data')
                return

            # Records are for each day, midnight to midnight
            day = 0
            if 'periods' in jdata['response'][0]:
                for forecast in jdata['response'][0]['periods']:
                    LOGGER.debug(' >>>>   period ' + forecast['dateTimeISO'])
                    #LOGGER.debug(forecast)
                    #LOGGER.debug('              ')
                    fcast[day] = {
                            'temp_max': forecast[self.tag['temp_max']],
                            'temp_min': forecast[self.tag['temp_min']],
                            'Hmax': forecast[self.tag['humidity_max']],
                            'Hmin': forecast[self.tag['humidity_min']],
                            'pressure': float(forecast[self.tag['pressure']]),
                            'speed': float(forecast[self.tag['windspeed']]),
                            'speed_max': float(forecast[self.tag['wind_max']]),
                            'speed_min': float(forecast[self.tag['wind_min']]),
                            'gust': float(forecast[self.tag['gustspeed']]),
                            'dir': forecast[self.tag['winddir']],
                            'dir_max': forecast[self.tag['winddir_max']],
                            'dir_min': forecast[self.tag['winddir_min']],
                            'timestamp': forecast[self.tag['timestamp']],
                            'pop': forecast[self.tag['pop']],
                            'precip': float(forecast[self.tag['precipitation']]),
                            'uv': forecast['uvi'],
                            'clouds': forecast['sky'],
                            'coverage': self.coverage_codes(forecast['weatherPrimaryCoded'].split(':')[0]),
                            'intensity': self.intensity_codes(forecast['weatherPrimaryCoded'].split(':')[1]),
                            'weather': self.weather_codes(forecast['weatherPrimaryCoded'].split(':')[2]),
                            }
                    day += 1


            for f in range(0,int(self.params.get('Forecast Days'))):
                address = 'forecast_' + str(f)
                self.nodes[address].update_forecast(fcast[f], self.latitude, self.params.get('Elevation'), self.params.get('Plant Type'), self.params.get('Units'))


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
            if int(self.params.get('Forecast Days')) > 14:
                addNotice('Number of days of forecast data is limited to 14 days', 'forecast')
                self.params.set('Forecast Days', 14)
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

    def weather_codes(self, code):
        code_map = {
                'A': 0,   # hail
                'BD': 1,  # blowing dust
                'BN': 2,  # blowing sand
                'BR': 3,  # mist
                'BS': 4,  # blowing snow
                'BY': 5,  # blowing spray
                'F': 6,   # fog
                'FR': 7,  # frost
                'H': 8,   # haze
                'IC': 9,  # ice crystals
                'IF': 10, # ice fog
                'IP': 11, # ice pellets / Sleet
                'K': 12,  # smoke
                'L': 13,  # drizzle
                'R': 14,  # rain
                'RW': 15, # rain showers
                'RS': 16, # rain/snow mix
                'SI': 17, # snow/sleet mix
                'WM': 18, # wintry mix (sno, sleet, rain)
                'S': 19,  # snow
                'SW': 20, # snow showers
                'T': 21,  # Thunderstorms
                'UP': 22, # unknown precipitation
                'VA': 23, # volcanic ash
                'WP': 24, # waterspouts
                'ZF': 25, # freezing fog
                'ZL': 26, # freezing drizzle
                'ZR': 27, # freezing rain
                'ZY': 28, # freezing spray
                'CL': 29, # Clear
                'FW': 30, # Fair/Mostly sunny
                'SC': 31, # Partly cloudy
                'BK': 32, # Mostly cloudy
                'OV': 33, # Cloudy/Overcast
                }

        if code in code_map:
            return code_map[code]

        return 22

    def intensity_codes(self, code):
        code_map = {
                'VL': 1,  # very light
                'L': 2,   # light
                'H': 3,   # heavy
                'VH': 4,  # very heavy
                }
        if code in code_map:
            return code_map[code]
        return 0  # moderate

    def coverage_codes(self, code):
        code_map = {
                'AR': 0,  # areas of
                'BR': 1,  # brief
                'C':  2,  # chance of
                'D':  3,  # definite
                'FQ': 4,  # frequent
                'IN': 5,  # intermittent
                'IS': 6,  # isolated
                'L':  7,  # likely
                'NM': 8,  # numerous
                'O':  9,  # occasional
                'PA': 10,  # patchy
                'PD': 11,  # periods of
                'S':  12,  # slight chance
                'SC': 13,  # scattered
                'VC': 14,  # in the vicinity/nearby
                'WD': 15,  # widespread
                }
        if code in code_map:
            return code_map[code]
        return 16


    def set_logging_level(self, level=None):
        if level is None:
            try:
                level = self.get_saved_log_level()
            except:
                LOGGER.error('set_logging_level: get saved log level failed.')

            if level is None:
                level = 10

            level = int(level)
        else:
            level = int(level['value'])

        self.save_log_level(level)
        LOGGER.info('set_logging_level: Setting log level to %d' % level)
        LOGGER.setLevel(level)

    commands = {
            'UPDATE_PROFILE': update_profile,
            'REMOVE_NOTICES_ALL': remove_notices_all
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
            {'driver': 'GV4', 'value': 0, 'uom': 49},      # wind speed
            {'driver': 'GV5', 'value': 0, 'uom': 49},      # gust speed
            {'driver': 'GV0', 'value': 0, 'uom': 4},       # heat index
            {'driver': 'GV1', 'value': 0, 'uom': 4},       # wind chill
            {'driver': 'GV2', 'value': 0, 'uom': 4},       # feels like
            {'driver': 'GV6', 'value': 0, 'uom': 82},      # rain
            {'driver': 'GV11', 'value': 0, 'uom': 25},     # climate coverage
            {'driver': 'GV12', 'value': 0, 'uom': 25},     # climate intensity
            {'driver': 'GV13', 'value': 0, 'uom': 25},     # climate conditions
            {'driver': 'GV14', 'value': 0, 'uom': 22},     # cloud conditions
            {'driver': 'GV15', 'value': 0, 'uom': 83},     # visibility
            {'driver': 'SOLRAD', 'value': 0, 'uom': 71},   # solar radiataion
            ]


