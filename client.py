'''
/*
 * Copyright 2019 ground0state. All Rights Reserved.
 * Released under the MIT license
 * https://opensource.org/licenses/mit-license.php
/
/*
 * Copyright 2010-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License").
 * You may not use this file except in compliance with the License.
 * A copy of the License is located at
 *
 *  http://aws.amazon.com/apache2.0
 *
 * or in the "license" file accompanying this file. This file is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
 * express or implied. See the License for the specific language governing
 * permissions and limitations under the License.
 */
 '''

import argparse
import json
import logging
import time
from datetime import datetime

import socks
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from generator.ARIMA_generator import ARIMA111

AllowedActions = ['both', 'publish', 'subscribe']


# Custom MQTT message callback
def customCallback(client, userdata, message):
    print("Received a new message: ")
    print(message.payload)
    print("from topic: ")
    print(message.topic)
    print("--------------\n\n")


# Configure logging
now = datetime.today().strftime('%Y%m%d%H%M%S')
logger = logging.getLogger("clien.py")
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler()
fileHandler = logging.FileHandler(filename=f"./logs/{now}.log", mode='a')
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
fileHandler.setFormatter(formatter)
logger.addHandler(streamHandler)
logger.addHandler(fileHandler)
logger.debug(f"start script")

# Read in command-line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-e", "--endpoint", action="store", required=True,
                    dest="host", help="Your AWS IoT custom endpoint")
parser.add_argument("-r", "--rootCA", action="store", dest="rootCAPath",
                    default="./cert/AmazonRootCA1.pem", help="Root CA file path")
parser.add_argument("-c", "--cert", action="store",
                    dest="certificatePath", default="./cert/certificate.pem", help="Certificate file path")
parser.add_argument("-k", "--key", action="store",
                    dest="privateKeyPath", default="./cert/private.pem", help="Private key file path")
parser.add_argument("-p", "--port", action="store",
                    dest="port", type=int, help="Port number override")
parser.add_argument("-w", "--websocket", action="store_true", dest="useWebsocket", default=False,
                    help="Use MQTT over WebSocket")
parser.add_argument("-id", "--clientId", action="store", dest="clientId", default="basicPubSub",
                    help="Targeted client id")
parser.add_argument("-t", "--topic", action="store", dest="topic",
                    default="sdk/test/Python", help="Targeted topic")
parser.add_argument("-m", "--mode", action="store", dest="mode", default="both",
                    help="Operation modes: %s" % str(AllowedActions))
parser.add_argument("-s", "--sensor", action="store", dest="numOfSensors", default=1, type=int,
                    help="Number of sensors")
parser.add_argument("--proxy", action="store_true", dest="useProxy", default=False,
                    help="Use Proxy")
parser.add_argument("--proxyAddr", action="store",
                    dest="proxyAddr", help="Proxy address")
parser.add_argument("--proxyPort", action="store",
                    dest="proxyPort", type=int, help="Proxy port")
parser.add_argument("--proxyType", action="store",
                    dest="proxyType", type=int, help="Proxy type")

args = parser.parse_args()
host = args.host
rootCAPath = args.rootCAPath
certificatePath = args.certificatePath
privateKeyPath = args.privateKeyPath
port = args.port
useWebsocket = args.useWebsocket
clientId = args.clientId
topic = args.topic
numOfSensors = args.numOfSensors

useProxy = args.useProxy
proxyAddr = args.proxyAddr
proxyPort = args.proxyPort
proxyType = args.proxyType

logger.debug(f"host: {host}")
logger.debug(f"port: {port}")
logger.debug(f"clientId: {clientId}")
logger.debug(f"topic: {topic}")
logger.debug(f"numOfSensors: {numOfSensors}")

sensor_list = ["device" + str(i+1) for i in range(numOfSensors)]
data_generator_list = [ARIMA111() for i in range(numOfSensors)]


if args.mode not in AllowedActions:
    parser.error("Unknown --mode option %s. Must be one of %s" %
                 (args.mode, str(AllowedActions)))
    exit(2)

if args.useWebsocket and args.certificatePath and args.privateKeyPath:
    parser.error(
        "X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
    exit(2)

if not args.useWebsocket and (not args.certificatePath or not args.privateKeyPath):
    parser.error("Missing credentials for authentication.")
    exit(2)

# Port defaults
if args.useWebsocket and not args.port:  # When no port override for WebSocket, default to 443
    port = 443
if not args.useWebsocket and not args.port:  # When no port override for non-WebSocket, default to 8883
    port = 8883

# Init AWSIoTMQTTClient
myAWSIoTMQTTClient = None
if useWebsocket:
    myAWSIoTMQTTClient = AWSIoTMQTTClient(clientId, useWebsocket=True)
    myAWSIoTMQTTClient.configureEndpoint(host, port)
    myAWSIoTMQTTClient.configureCredentials(rootCAPath)
else:
    myAWSIoTMQTTClient = AWSIoTMQTTClient(clientId)
    myAWSIoTMQTTClient.configureEndpoint(host, port)
    myAWSIoTMQTTClient.configureCredentials(
        rootCAPath, privateKeyPath, certificatePath)

# AWSIoTMQTTClient connection configuration
myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
# Infinite offline Publish queueing
myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)
myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

# AWSIoTMQTTClient socket configuration
# import pysocks to help us build a socket that supports a proxy configuration
if useProxy:
    # set proxy arguments (for SOCKS5 proxy: proxy_type=2, for HTTP proxy: proxy_type=3)
    proxy_config = {"proxy_addr": proxyAddr,
                    "proxy_port": proxyPort, "proxy_type": proxyType}
    # create anonymous function to handle socket creation
    def socket_factory(): return socks.create_connection((host, port), **proxy_config)
    myAWSIoTMQTTClient.configureSocketFactory(socket_factory)

# Connect and subscribe to AWS IoT
myAWSIoTMQTTClient.connect()
if args.mode == 'both' or args.mode == 'subscribe':
    logger.debug("subscribe start")
    myAWSIoTMQTTClient.subscribe(topic, 1, customCallback)
time.sleep(2)

# Publish to the same topic in a loop forever
logger.debug("publish start")
try:
    while True:
        if args.mode == 'both' or args.mode == 'publish':
            t = int(time.time())
            for sensorName, data_generator in zip(sensor_list, data_generator_list):
                message = {}
                message['device'] = sensorName
                message['value'] = data_generator.get_value(p=0.01)
                message['timestamp'] = t*1000
                messageJson = json.dumps(message)
                myAWSIoTMQTTClient.publish(topic, messageJson, 1)
                if args.mode == 'publish':
                    print('Published topic %s: %s\n' % (topic, messageJson))
        time.sleep(1)
except KeyboardInterrupt as e:
    logger.debug(
        f"KeyboardInterrupt: {datetime.today().strftime('%Y%m%d%H%M%S')}")

except Exception:
    logger.debug(f"Other error: {datetime.today().strftime('%Y%m%d%H%M%S')}")
