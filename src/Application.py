import signal
import sys
import math
import usb.core
import time
import logging
import ConfigParser
import os
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from datetime import datetime

##
# Loading configuration. First find the application location, then search for application.cfg
##
config = ConfigParser.ConfigParser()
config.read(os.path.dirname(os.path.abspath(__file__)) + '/../conf/application.cfg')
config.sections()

##
# Constants and attributes used by the script
##
logger = logging.getLogger('happyears')
handler = logging.FileHandler(config.get('log', 'file'))
formatter = logging.Formatter(config.get('log', 'format', 1))
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
# Represents 15 minutes in seconds
max15Values = 900
# Represents 1 hour in seconds
max60Values = 3600
laeq15ValueList = [0] * max15Values
laeq60ValueLIst = [0] * max60Values
# Amount of seconds between to sends. Defined to 5 minutes.
sendDelay = 299
#This index is used to position each read in the correct place in the laeqXXValueList. When maxXXValues is reached
# the index is reset to 0. Thus we loop the laeqXXValueList and we have always the last 15 and 60 minutes red values.
laeq15Index = 0
laeq60Index = 0
# This index is checked against sendDelay to decide if the script should publish data to the MQTT queue
sendTimer = 0
# Logarithmic mean values representing the sound pressure over a period of 15 or 60 minutes
laeq15 = 0
laeq60 = 0

##
# This method initialize the link with the USB sound meter using "USB core" library (see imports)
##
def initUsb():
    global dev
    dev = usb.core.find(idVendor=0x16c0, idProduct=0x5dc)
    assert dev is not None
    logger.info(dev)
    logger.info('Hex : ' + (hex(dev.idVendor) + ',' + hex(dev.idProduct)))

def awsCallback(client, userdata, message):
    logger.info(message.payload)

##
# This method initialize the connection to the AWS MQTT queue. It should be called only once.
# It uses the certificate based connection described by Amazon (TLS mutual authentication) using AWS SDK (see imports)
def initAwsMqtt():
    global myMQTTClient
    myMQTTClient = AWSIoTMQTTClient(config.get('aws', 'client-name'))
    myMQTTClient.configureEndpoint(config.get('aws', 'endpoint'), config.get('aws', 'endpoint-port'))
    myMQTTClient.configureCredentials(config.get('aws', 'root-ca'), config.get('aws', 'private-key'), config.get('aws', 'certificate'))
    myMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    myMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
    myMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
    myMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec
    logger.info('Trying to connect to AWS')
    myMQTTClient.connect()
    logger.info('Connected to AWS')
    myMQTTClient.subscribe(config.get('aws', 'subscription-topic'), 1, awsCallback)
    logger.info('Subscribed to topic : ' + config.get('aws', 'subscription-topic'))

##
# This method computes the logarithmic mean value for sound level measures for a 15 minutes period.
# The formula was found on : http://forum.studiotips.com/viewtopic.php?f=1&t=2912
# logarithmic average :
#   10  * LOG(sum) - 10 * LOG(nbrOfValues) = 10 * LOG(sum / numberOfValues)
# The calculation of Laeq values are independent one from the other and could be mult-ithreaded.
##
def calculateLaeq15():
    global laeq15
    global max15Values
    sum = 0
    for db in laeq15ValueList:
        sum += math.pow(10, db/10.0)
    laeq15 = 10.0 * math.log10(sum / max15Values)

##
# This method computes the logarithmic mean value for sound level measures for a 60 minutes period.
# The calculation of Laeq values are independent one from the other and could be multi-threaded.
##
def calculateLaeq60():
    global laeq60
    global max60Values
    sum = 0
    for db in laeq60ValueLIst:
        sum += math.pow(10, db/10.0)
    laeq60 = 10.0 * math.log10(sum/max60Values)

##
# Gracefully handling exit so that the application closes the MQTT socket it opened earlier.
##
def signal_term_handler(signal, frame):
    logger.warning('got SIGTERM')
    myMQTTClient.disconnect()
    sys.exit(0)

############################
# Application starst here  #
############################
initUsb()
initAwsMqtt()
signal.signal(signal.SIGTERM, signal_term_handler) # registering signal_term_handler method to the SIGTERM signal

##
# Application loop. It will run forever unless a SIGTERM is received
##
try:
    while True:
        time.sleep(1)
        ret = dev.ctrl_transfer(0xC0, 4, 0, 0, 200)
        dB = (ret[0] + ((ret[1] & 3) * 256)) * 0.1 + 30
        if (logger.isEnabledFor(logging.DEBUG)):
            logger.debug('red : ' +  str(dB))
        laeq15ValueList[laeq15Index] = dB
        laeq60ValueLIst[laeq60Index] = dB
        laeq15Index += 1
        laeq60Index += 1
        sendTimer += 1
        if (laeq15Index == max15Values):
            laeq15Index = 0
        if (laeq60Index == max60Values):
            laeq60Index = 0
        if (sendTimer == sendDelay):
            # these calls could be multi-threaded
            calculateLaeq15()
            calculateLaeq60()
            # ensure that we do not send garbage data during the warmup of laeq60ValueList
            if not laeq60 > 0:
                laeq60 = 0
            if (logger.isEnabledFor(logging.DEBUG)):
                logger.debug("Laeq15 : " + str(laeq15))
                logger.debug("Laeq60 : " + str(laeq60))
            if (laeq15 > 0):
                currentDatetime = datetime.today().isoformat()
                if (logger.isEnabledFor(logging.DEBUG)):
                    logger.debug('Sending : ' + '{"deviceId":' + config.get('aws', 'device-id') + ', "date":"' + currentDatetime + '", "Laeq15":' + '"' + str(laeq15) + '", "Laeq60":"' + str(laeq15) + '", "Lceq15":"0", "Lceq60":"0"}')
                myMQTTClient.publish(config.get('aws', 'publish-topic'), '{"deviceId":"' + config.get('aws', 'device-id') + '", "date":"' + currentDatetime + '", "Laeq15":' + '"' + str(laeq15) + '", "Laeq60":"' + str(laeq60) + '", "Lceq15":"0", "Lceq60":"0"}', 0)
            sendTimer = 0
except KeyboardInterrupt:
    logger.warning('got Ctrl+C')
    myMQTTClient.disconnect()
    sys.exit(0)
except:
    logger.error('Detected exception : ' + sys.exc_info()[0])
    raise
