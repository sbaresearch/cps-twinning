#!/usr/bin/env python

from kafka import KafkaProducer

import numpy as np
import argparse
import cv2
import time
import json

kafka_bootstrap_servers = '192.168.56.3:9092'

color_threshold = 100
change_detection_threshold = 200
# In seconds:
publish_threshold = 5000

candies = {
    # 'blue': 'Raspberry',
    'pink': 'Cherry',
    'yellow': 'Mint',
    # 'gray': 'Cola'
}

# Color boundaries
boundaries = {
    'pink': ([77, 51, 127], [105, 72, 165]),
    # 'blue': ([86, 31, 4], [220, 88, 50]),
    'yellow': ([2, 110, 137], [26, 135, 159]),
    #  'gray': ([103, 86, 65], [145, 133, 128])
}


class CandyDetector(object):
    def __init__(self, live_mode, image_path, resize_factor, demo_mode):
        if not demo_mode:
            self.kafka_producer = KafkaProducer(bootstrap_servers=kafka_bootstrap_servers)
        else:
            self.kafka_producer = None
        self.last_published = None
        # This value will be updated on each frame (live mode) in order to determine changes
        self.last_max_color_val = 0
        if live_mode is not None and live_mode:
            self.__start_live_mode()
        elif image_path is not None:
            self.image = cv2.imread(image_path)
            if resize_factor is not None:
                self.image = cv2.resize(self.image, (0, 0), fx=resize_factor, fy=resize_factor)
            candy = self.__get_candy(self.image)
            if candy is not None:
                self.__publish_candy(candy)
            print candy
        else:
            print "ERROR! Invalid args."
        self.kafka_producer.close()

    def __start_live_mode(self):
        cap = cv2.VideoCapture(0)
        cap.set(cv2.cv.CV_CAP_PROP_FPS, 5)
        while True:
            # Capture frame-by-frame
            ret, frame = cap.read()
            if ret:
                # Display the resulting frame
                cv2.imshow('frame', frame)
                candy = self.__get_candy(frame)
                if candy is not None:
                    self.__publish_candy(candy)
                    print candy
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # Release the capture
        cap.release()
        cv2.destroyAllWindows()

    def __get_candy(self, frame):
        cnts = {}
        for k, (lower, upper) in boundaries.iteritems():
            # create NumPy arrays from the boundaries
            lower = np.array(lower, dtype="uint8")
            upper = np.array(upper, dtype="uint8")

            # Retrieve mask (binary result = pixel is within range or not)
            mask = cv2.inRange(frame, lower, upper)
            cnts[k] = cv2.countNonZero(mask)
            #output = cv2.bitwise_and(frame, frame, mask=mask)
            # Show images
            #cv2.imshow("images", np.hstack([frame, output]))
            #cv2.waitKey(0)
        # print cnts
        # Return candy name with max. counts
        color = max(cnts, key=cnts.get)
        max_color_val = cnts[color]
        if max_color_val >= color_threshold and abs(
                max_color_val - self.last_max_color_val) >= change_detection_threshold:
            print max_color_val
            self.last_max_color_val = max_color_val
            return candies.get(color)
        return None

    def __publish_candy(self, candy):
        if self.kafka_producer is not None and (self.last_published is None or (
                self.__get_timestamp() - int(self.last_published['timestamp'])) > publish_threshold):
            timestamp = self.__get_timestamp()
            log = {'timestamp': str(timestamp), 'name': 'CandySensor1', 'candy': candy}
            json_log = json.dumps(log, ensure_ascii=False)
            self.kafka_producer.send('p_logs', key=log['name'], value=json_log)
            self.last_published = log
            print "Published"

    def __get_timestamp(self):
        return int(round(time.time() * 1000))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--image", help="path to the image")
    parser.add_argument("-r", "--resize", type=float, help="resize factor, e.g., 0.2")
    parser.add_argument("-l", "--live", help="starts sensor in live mode", action='store_true')
    parser.add_argument("-d", "--demo", help="starts sensor in demo mode (no log publishing)", action='store_true')
    args = parser.parse_args()
    cd = CandyDetector(args.live, args.image, args.resize, args.demo)
