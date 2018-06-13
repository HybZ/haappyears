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

config = ConfigParser.ConfigParser()
config.read(os.path.dirname(os.path.abspath(__file__)) + '/../conf/application.cfg')
config.sections()

logger = logging.getLogger('happyears')
handler = logging.FileHandler(config.get('log', 'file'))
formatter = logging.Formatter(config.get('log', 'format', 1))
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
maxValues = 900
max60Values = 3600
dbList = [0] * maxValues
db60List = [0] * max60Values
sendDelay = 299
index = 0
index60 = 0
awsDelay = 0
laeq = 0
laeq60 = 0

def initUsb():
    global dev
    dev = usb.core.find(idVendor=0x16c0, idProduct=0x5dc)
    assert dev is not None
    logger.info(dev)
    logger.info('Hex : ' + (hex(dev.idVendor) + ',' + hex(dev.idProduct)))

def awsCallback(client, userdata, message):
    logger.info(message.payload)

# arn:aws:iot:eu-west-1:521595501823:thing/happyearsRaspberryPi
def initAwsMqtt():
    # For certificate based connection
    global myMQTTClient
    # myMQTTClient = AWSIoTMQTTClient("happyearsRaspberryPi")
    myMQTTClient = AWSIoTMQTTClient(config.get('aws', 'client-name'))
    # Configurations
    # For TLS mutual authentication
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

# for formula see : http://forum.studiotips.com/viewtopic.php?f=1&t=2912
# logarithmic average :
#   10  * LOG(sum) - 10 * LOG(nbrOfValues) = 10 * LOG(sum / numberOfValues)
def calculateLaeq15():
    global laeq
    global maxValues
    sum = 0
    # print dbList
    for db in dbList:
        sum += math.pow(10, db/10.0)
    laeq = 10.0 * math.log10(sum/maxValues)

def calculateLaeq60():
    global laeq60
    global max60Values
    sum = 0
    for db in db60List:
        sum += math.pow(10, db/10.0)
    laeq60 = 10.0 * math.log10(sum/max60Values)

def signal_term_handler(signal, frame):
    logger.warning('got SIGTERM')
    myMQTTClient.disconnect()
    sys.exit(0)

initUsb()
initAwsMqtt()
signal.signal(signal.SIGTERM, signal_term_handler)

try:
    while True:
        time.sleep(1)
        ret = dev.ctrl_transfer(0xC0, 4, 0, 0, 200)
        dB = (ret[0] + ((ret[1] & 3) * 256)) * 0.1 + 30
        if (logger.isEnabledFor(logging.DEBUG)):
            logger.debug('red : ' +  str(dB))
        dbList[index] = dB
        db60List[index60] = dB
        index += 1
        index60 += 1
        awsDelay += 1
        if (index == maxValues):
            index = 0
        if (index60 == max60Values):
            index60 = 0
        if (awsDelay == sendDelay):
            calculateLaeq15()
            calculateLaeq60()
            if not laeq60 > 0:
                laeq60 = 0
            if (logger.isEnabledFor(logging.DEBUG)):
                logger.debug("Laeq : " + str(laeq))
                logger.debug("Laeq60 : " + str(laeq60))
            if (laeq > 0):
                currentDatetime = datetime.today().isoformat()
                if (logger.isEnabledFor(logging.DEBUG)):
                    logger.debug('Sending : ' + '{"deviceId":"b7072dd6-444a-4fd9-b75c-dc215a04831f", "date":"' + currentDatetime + '", "Laeq15":' + '"' + str(laeq) + '", "Laeq60":"' + str(laeq) + '", "Lceq15":"0", "Lceq60":"0"}')
                myMQTTClient.publish(config.get('aws', 'publish-topic'), '{"deviceId":"' + config.get('aws', 'device-id') + '", "date":"' + currentDatetime + '", "Laeq15":' + '"' + str(laeq) + '", "Laeq60":"' + str(laeq60) + '", "Lceq15":"0", "Lceq60":"0"}', 0)
            awsDelay = 0
except KeyboardInterrupt:
    logger.warning('got Ctrl+C')
    myMQTTClient.disconnect()
    sys.exit(0)
except:
    logger.error('Detected exception : ' + sys.exc_info()[0])
    raise