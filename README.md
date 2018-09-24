# Happyears 

This application is inspired by Brussels' amplified sound use case which is known under the umbrella [Happy Ears](https://environnement.brussels/thematiques/bruit/son-amplifie-electroniquement). It's a way to measure the sound pressure in a room and publish it on a IoT platform which can then later be visualised using a web portal as [CIRB-CIBG Happy Ears](https://happyears.irisnet.be).

<p align="center">
  <img src="https://environnement.brussels/sites/default/files/styles/content_page/public/user_files/logo_picto_140x140mm_cat1-85db.jpg?itok=RhuKHLD0" alt="Happy Ears pictogram green" /><img src="https://leefmilieu.brussels/sites/default/files/styles/content_page/public/user_files/logo_picto_140x140mm_cat2-95db.jpg?itok=j1M-XUwL" alt="Happy Ears pictogram orange" /><img src="https://leefmilieu.brussels/sites/default/files/styles/content_page/public/user_files/docu_autocollant-140x140mm-fluo-def-20170322-3_imp1.jpg?itok=u0D0O_OW" alt="Happy Ears pictogram pink" />
</p>

## Introduction

This application, which is designed for a [Raspberry Pi 3](https://www.raspberrypi.org/), acts as a Gateway for a [Wensn ws1361](http://www.wensn.com/html_products/WS1361-17.html) sound meter device. It reads every second the sound level from the device connected via USB and calculates a logarithmic mean value for the last 15 and 60 minutes then publishes the data every 5 minutes on an [AWS IoT](https://aws.amazon.com/iot/) topic using MQTT protocol.

## Requirements

* A Raspberry Pi
* A Wensn ws1364
* An AWS account with a configured IoT device. You will need the certificate, root_ca and private key.
* Python 2.7

On your Raspberry Pi, make sure that ntp is running and that date is correctly configured for your timezone, for Raspian Jetty run `sudo dpkg-reconfigure tzdata`

## How to run

The first step, before starting the application, is to update the [configuration file](https://github.com/HybZ/haappyears/blob/master/conf/application.cfg).

The application uses logging and will write it in a file specified in application.cfg

### Manually

Simply execute `sudo python Application.py`

### As a systemctl service

Refer to [happyears.service](https://github.com/HybZ/haappyears/blob/master/happyears.service) comments in order create a systemctl service.

## How to configure

Various parts are configurable through [configuration file](https://github.com/HybZ/haappyears/blob/master/conf/application.cfg). Among them :
* AWS credentials
* MQTT subscription and publication topics
* Current device ID 

## Exchanged data

This application is specific to the CIRB-CIBG IOT platform. The data must respect a contract which is represented by the following Json :

```json
{
  "deviceId":"12345678-90ab-cdef-1234-567890abcdef", 
  "date":"20180101T00:00:00", 
  "Laeq15":"0", 
  "Laeq60":"0", 
  "Lceq15":"0", 
  "Lceq60":"0"
}
```

To learn more about the meaning of Laeq values please refer to a sound specilized site such as : [http://www.gracey.co.uk/basics/leq-b1.htm]()http://www.gracey.co.uk/basics/leq-b1.htm)

## Lisence 
Apache 2.0
 
## Author
Adi Bajramov

## Special thanks to [Troy from ebswift.com](https://www.ebswift.com/reverse-engineering-spl-usb.html)
 
