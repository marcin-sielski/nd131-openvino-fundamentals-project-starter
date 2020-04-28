"""People Counter."""
"""
 Copyright (c) 2018 Intel Corporation.
 Permission is hereby granted, free of charge, to any person obtaining
 a copy of this software and associated documentation files (the
 "Software"), to deal in the Software without restriction, including
 without limitation the rights to use, copy, modify, merge, publish,
 distribute, sublicense, and/or sell copies of the Software, and to
 permit person to whom the Software is furnished to do so, subject to
 the following conditions:
 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
 LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
 WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


import os
import sys
import time
import socket
import json
import cv2

import logging as log
import paho.mqtt.client as mqtt

from argparse import ArgumentParser
from inference import Network

from datetime import datetime
import time

# MQTT server environment variables
HOSTNAME = socket.gethostname()
IPADDRESS = socket.gethostbyname(HOSTNAME)
MQTT_HOST = IPADDRESS
MQTT_PORT = 3001
# Increase Keep Alive Interval for large models
MQTT_KEEPALIVE_INTERVAL = 600

# How long algorithm shall display the previous box if its new location was not
# found in the image
TIMEOUT = 2000

# List of boxes discovered in previous frame
PREVIOUS_BOXES = []

def build_argparser():
    """
    Parse command line arguments.

    :return: command line arguments
    """

    # str type to bool type coverter 
    def str2bool(v):
        if isinstance(v, bool):
            return v
        if v.lower() in ('yes', 'true', 't', 'y', '1'):
            return True
        elif v.lower() in ('no', 'false', 'f', 'n', '0'):
            return False
        else:
            raise argparse.ArgumentTypeError('Boolean value expected.')

    parser = ArgumentParser()
    parser.add_argument("-m", "--model", required=True, type=str,
                        help="Path to an xml file with a trained model.")
    parser.add_argument("-i", "--input", required=True, type=str,
                        help="Path to image or video file")
    parser.add_argument("-l", "--cpu_extension", required=False, type=str,
                        default=None,
                        help="MKLDNN (CPU)-targeted custom layers."
                             "Absolute path to a shared library with the"
                             "kernels impl.")
    parser.add_argument("-d", "--device", type=str, default="CPU",
                        help="Specify the target device to infer on: "
                             "CPU, GPU, FPGA or MYRIAD is acceptable. Sample "
                             "will look for a suitable plugin for device "
                             "specified (CPU by default)")
    parser.add_argument("-pt", "--prob_threshold", type=float, default=0.5,
                        help="Probability threshold for detections filtering"
                        "(0.5 by default)")
    parser.add_argument("-g", "--debug", type=str2bool, nargs='?', \
                        const=False, default=False, help="Enable debug mode"
                        "(False by default)")
    return parser


def connect_mqtt():
    ### TODO: Connect to the MQTT client ###
    client = mqtt.Client()
    client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)
    return client

def draw_boxes(frame, result, args, width, height):
    '''
    Draw bounding boxes onto the frame.
    '''

    def confidence(box):
        return box[2]

    global PREVIOUS_BOXES
    boxes = []
    best_boxes = []
    for box in result[0][0]: # Output shape is 1x1x100x7
        conf = box[2]
        if conf >= args.prob_threshold and box[1] == 1:
            boxes.append(box)
    if len(boxes) > 0:
        boxes.sort(key=confidence, reverse=True)
        found = False
        best_boxes = []
        for box in boxes:
            if found == False:
                found = True
                best_boxes.append(box)
            else:
                append = True
                for best_box in best_boxes:
                    if not (box[3] > best_box[5] or box[5] < best_box[3] or box[4] > best_box[6] or box[6] < best_box[4]):
                        append = False
                        break
                if append == True:
                    best_boxes.append(box)

        ### TODO: In real deployment all the boxes shall be treated separately
        ### because they may disappear independently. The code below should
        ### update relevant previous boxes with its new location. It can be
        ### potentially done by checking if location of preview box and new box
        ### location at least partially overlap 
        PREVIOUS_BOXES = []
        for box in best_boxes:
            if args.debug:
                print(box)
            xmin = int(box[3] * width)
            ymin = int(box[4] * height)
            xmax = int(box[5] * width)
            ymax = int(box[6] * height)
            cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 0, 255), 1)
            PREVIOUS_BOXES.append((datetime.timestamp(datetime.now()), box))
    else:
        if args.debug:
            print("No boxes found.")
        if len(PREVIOUS_BOXES) > 0:
            for box in PREVIOUS_BOXES:
                if datetime.timestamp(datetime.now()) - box[0] < TIMEOUT and box[1][3] > 0.01 and box[1][5] < 0.99:
                    best_boxes.append(box[1])
            for box in best_boxes:
                if args.debug:
                    print(box)
                xmin = int(box[3] * width)
                ymin = int(box[4] * height)
                xmax = int(box[5] * width)
                ymax = int(box[6] * height)
                cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 0, 255), 1)
    if args.debug:
        print("People count: " + str(len(best_boxes)))
    return frame, len(best_boxes)

def infer_on_stream(args, client):
    """
    Initialize the inference network, stream video to network,
    and output stats and video.

    :param args: Command line arguments parsed by `build_argparser()`
    :param client: MQTT client
    :return: None
    """
    # Initialise the class
    infer_network = Network()
    # Set Probability threshold for detections
    prob_threshold = args.prob_threshold

    ### TODO: Load the model through `infer_network` ###
    infer_network.load_model(args.model, args.device, args.cpu_extension, \
        args.debug)
    net_input_shape = infer_network.get_input_shape()
    if args.debug:
        print("Input shape of the model: " + str(net_input_shape))
    ### TODO: Handle the input stream ###
    cap = cv2.VideoCapture(args.input)
    cap.open(args.input)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = 0
    found = False
    total = 0
    ### TODO: Loop until stream is over ###
    if args.debug:
        print("Input size: "+str((height, width)))
    while cap.isOpened():
        ### TODO: Read from the video capture ###
        flag, frame = cap.read()
        if not flag:
            break
        key_pressed = cv2.waitKey(60)
        ### TODO: Pre-process the image as needed ###
        if frame_count == -1:
            frame = cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_I420)
        p_frame = cv2.resize(frame, (net_input_shape[3], net_input_shape[2]))
        p_frame = p_frame.transpose((2,0,1))
        p_frame = p_frame.reshape(1, *p_frame.shape)

        ### TODO: Start asynchronous inference for specified request ###
        infer_network.exec_net(p_frame)

        ### TODO: Wait for the result ###
        if infer_network.wait() == 0:

            ### TODO: Get the results of the inference request ###
            result = infer_network.get_output()

            ### TODO: Extract any desired stats from the results ###
            frame, count = draw_boxes(frame, result, args, width, height)

            ### TODO: Calculate and send relevant information on ###
            ### current_count, total_count and duration to the MQTT server ###
            ### Topic "person": keys of "count" and "total" ###
            ### Topic "person/duration": key of "duration" ###
            if not found and count > 0:
                total = total + count
                found = True
            if found and count > 0:
                frames = frames + 1
            if found and count == 0:
                found = False
                client.publish("person/duration", 
                json.dumps({"duration": int(frames/fps)}))
                frames = 0
            client.publish("person", 
            json.dumps({"count": count, "total": total}))
            
        ### TODO: Send the frame to the FFMPEG server ###
        if not args.debug and (frame_count > 0 or frame_count == -1):
            sys.stdout.buffer.write(frame)  
            sys.stdout.flush()
        ### TODO: Write an output image if `single_image_mode` ###
        else:
            cv2.imwrite("output.jpg", frame)
            print("Image saved to output.jpg")
    cap.release()
    cv2.destroyAllWindows()
    client.disconnect()

def main():
    """
    Load the network and parse the output.

    :return: None
    """
    # Grab command line args
    args = build_argparser().parse_args()
    # Connect to the MQTT server
    client = connect_mqtt()
    # Perform inference on the input stream
    infer_on_stream(args, client)


if __name__ == '__main__':
    main()
