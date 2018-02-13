import signal
import sys
import math
import usb.core
import time
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

maxValues = 900
dbList = [0] * maxValues
index = 0
awsDelay = 0
laeq = 0

def initUsb():
    global dev
    dev = usb.core.find(idVendor=0x16c0, idProduct=0x5dc)
    assert dev is not None
    # print dev
    # print 'Hex : ' + (hex(dev.idVendor) + ',' + hex(dev.idProduct))

def awsCallback(client, userdata, message):
    print 'Hello world!'
    print 'Message: '
    print message.payload

# arn:aws:iot:eu-west-1:521595501823:thing/happyearsRaspberryPi
def initAwsMqtt():
    # For certificate based connection
    global myMQTTClient
    myMQTTClient = AWSIoTMQTTClient("happyearsRaspberryPi")
    # Configurations
    # For TLS mutual authentication
    myMQTTClient.configureEndpoint("agyofls4sq7af.iot.eu-west-1.amazonaws.com", 8883)
    myMQTTClient.configureCredentials("ca/root_ca", "ca/f33efb6efa-private.pem.key", "ca/f33efb6efa-certificate.pem.crt.txt")
    myMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    myMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
    myMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
    myMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec
    myMQTTClient.connect()
    myMQTTClient.subscribe("sub", 1, awsCallback)

# for formula see : http://forum.studiotips.com/viewtopic.php?f=1&t=2912
# logarithmic average :
#   10  * LOG(sum) - 10 * LOG(nbrOfValues) = 10 * LOG(sum / numberOfValues)
def calculateLaeq15():
    global laeq
    global myMQTTClient
    sum = 0
    # print dbList
    for db in dbList:
        sum += math.pow(10, db/10.0)
    laeq = 10.0 * math.log10(sum/maxValues)

def signal_term_handler(signal, frame):
    print 'got SIGTERM'
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
        # print dB
        dbList[index] = dB
        index += 1
        awsDelay += 1
        if (index == maxValues):
            index = 0
            # print laeq
        if (awsDelay == 299):
            if (laeq > 0):
                myMQTTClient.publish("pub", '{' + '"laeq15":' + '"' + str(laeq) + '"' + '}', 0)
            awsDelay = 0
except KeyboardInterrupt:
    print 'got Ctrl+C'
    myMQTTClient.disconnect()
    sys.exit(0)
