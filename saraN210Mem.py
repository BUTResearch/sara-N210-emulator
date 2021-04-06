#!/usr/bin/python3
import enum

IMEI = '004402090454483'
SV = '00'
IMSI = '901288000011237'
IMEI_TEST = '+CGSN:(0,1,2,3)'
CFUN_TEST = '+CFUN:(0,1),(0,1)'
CSQ_TEST = '+CSQ: (0-31,99)(99)'
COPS_TEST = '+COPS: (1,,,"90128"),,(0-2),(2)'
CSCON_TEST = '+CSCON: (0,1)'
CGDCONT_TEST = '+CGDCONT: (0-10),("IP","NONIP"),,,(0),(0),,,,,(0,1)'
CGATT_TEST = '+CGATT: (0,1)'
CEREG_TEST = '+CEREG: (0,1,2,3,4,5)'
CPSM_TEST = '+CPSMS: (0,1,2),,,("00000000"-"11111111"),("00000000"-"11111111")'
NPSMR_TEST = '+NPSMR: (0,1)'

REBOOT = 'REBOOT_CAUSE_APPLICATION_AT\r\nNeul'
CLAC = ['AT+COPS', 'AT+CGATT', 'AT+NEARFCN', 'AT+NUESTATS', 'AT+NBAND', 'AT+CFUN', 'AT+NRB', 'AT+CIMI', 'AT+CSQ',
        'AT+CEREG', 'AT+CGPADDR', 'AT+CSCON', 'AT+NPSMR', 'AT+CMEE', 'AT+NPING', 'AT+NCONFIG', 'AT+NSOCR', 'AT+NSOST',
        'AT+NSOSTF', 'AT+NSORF', 'AT+NSOCL', 'AT+CGDCONT', 'AT+CCLK', 'AT+CTZR', 'AT+NCCID', 'AT+NLOGLEVEL', 'AT+CGMI',
        'AT+CGSN', 'AT+NTSETID', 'AT+NATSPEED', 'AT+NTPERMID', 'AT+CGMM', 'AT+CGMR', 'AT+CLAC', 'AT+CPSMS', 'AT+CSCA',
        'AT+CSMS', 'AT+CMGS', 'AT+CMGC', 'AT+CNMA', 'AT+CGACT', 'AT+CSODCP', 'AT+CRTDCP', 'AT+CEDRXS', 'AT+NPTWEDRXS',
        'AT+CEER', 'AT+CEDRXRDP', 'AT+NFWUPD', 'AT+NXLOG', 'AT+CGAPNRC', 'AT+NPOWERCLASS', 'AT+NPIN', 'AT+CIPCA']
MANUFACTURER = 'U-Blox'
MODEL = 'N210-02B-00'
FIRMWARE = ['SECURITY,V100R100C10B657SP2', 'PROTOCOL,V100R100C10B657SP2', 'APPLICATION,V100R100C10B657SP2',
            'SEC_UPDATER,V100R100C10B657SP2', 'APP_UPDATER,V100R100C10B657SP2', 'RADIO,sara-N210-01B-00']
STATS = {
    'BLER': {
        'RLC UL BLER': 0,
        'RLC DL BLER': 0,
        'MAC UL BLER': 0,
        'MAC DL BLER': 0,
        'Total TX bytes': 0,
        'Total RX bytes': 0,
        'Total TX blocks': 0,
        'Total RX blocks': 0,
        'Total RTX blocks': 0,
        'Total ACK/NACK RX': 0
    },
    'RADIO': {
        'Signal power': -32768,
        'Total power': -32768,
        'TX power': -32768,
        'TX time': 0,
        'RX time': 0,
        'Cell ID': 4294967295,
        'ECL': 255,
        'SNR': -32768,
        'EARFCN': 4294967295,
        'PCI': 65535,
        'RSRQ': -32768
    },
    'THP': {
        'RLC UL': 0,
        'RLC DL': 0,
        'MAC UL': 0,
        'MAC DL': 0
    },
    'APPSMEM': {
        'Current Allocated': 1154,
        'Total Free': 15024,
        'Max Free': 15024,
        'Num Allocs': 70,
        'Num Frees': 27
    },
    'CELL': {
        'EARFCN': 0,
        'Cell Id': 0,
        'Primary Cell': 0,
        'RSRP': 0,
        'RSRQ': 0,
        'RSSI': 0,
        'SNR': 0
    }
}

OK_RESPONSE = 'OK'
ERROR_RESPONSE = 'ERROR'

IDLE_TIMEOUT = 20 #seconds

PSM_PERIODIC = {
    0: 300,
    1: 3600,
    2: 36000,
    3: 2,
    4: 30,
    5: 60,
    6: 1152000,
    7: 0
}

PSM_ACTIVE = {
    0: 2,
    1: 60,
    2: 360,
    3: 0,
}


class Types(enum.Enum):
    Action = 1
    Test = 2
    Read = 3
    Set = 4
