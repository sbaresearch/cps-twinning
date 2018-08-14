#!/usr/bin/env python

from Queue import PriorityQueue
from kafka import KafkaConsumer
from threading import Thread, Event
from constants import KAFKA_BOOTSTRAP_SERVERS, KAFKA_STIMULI_TOPIC
from datetime import datetime
from cpstwinning.twins import Plc, Hmi, RfidReaderMqttWiFi
from cpstwinning.utils import current_ms

import json
import time
import logging

logger = logging.getLogger(__name__)


# Cf. https://stackoverflow.com/a/28479873/5107545
class Sleep(object):
    def __init__(self):
        self.event = Event()

    def sleep(self, seconds):
        self.event.clear()
        return self.event.wait(timeout=seconds)

    def wake(self):
        self.event.set()


class Stimulus(object):

    def __init__(self):
        pass


class TagStimulus(Stimulus):

    def __init__(self, timestamp, twin_name, tag_name, value=None):
        super(TagStimulus, self).__init__()
        self.timestamp = timestamp
        self.twin_name = twin_name
        self.tag_name = tag_name
        self.value = value


class RfidStimulus(Stimulus):

    def __init__(self, timestamp, twin_name, value):
        super(RfidStimulus, self).__init__()
        self.timestamp = timestamp
        self.twin_name = twin_name
        self.value = value


class StimulusIssuer(Thread):

    def __init__(self, cpstw, queue, sleep, sleeper, bail_out=False):
        Thread.__init__(self)
        self.cpstw = cpstw
        self._pq = queue
        self._sleep = sleep
        self._sleeper = sleeper
        self.running = False
        self.bail_out = bail_out

    def run(self):

        def get_formatted_timestamp():
            return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        def issue_stimulus(stim):
            """Issues a stimulus on the respective digital twin."""
            if stim.twin_name in self.cpstw:
                twin = self.cpstw[stim.twin_name]
                if isinstance(twin, Plc) or isinstance(twin, Hmi):
                    logger.info("[%s] Issuing stimulus: [twin=%s,%s=%s,t=%d].", get_formatted_timestamp(),
                                stim.twin_name, stim.tag_name, stim.value, long(stim.timestamp))
                    # Check if stimulus represents a get call
                    if stim.value is None:
                        twin.get_var_value(stim.tag_name)
                    # Must be set call
                    else:
                        twin.set_var_value(stim.tag_name, stim.value)
                    logger.info("[%s] Issued stimulus: [twin=%s,%s=%s,t=%d].", get_formatted_timestamp(),
                                stim.twin_name, stim.tag_name, stim.value, long(stim.timestamp))
                elif isinstance(twin, RfidReaderMqttWiFi):
                    logger.info("[%s] Issuing stimulus: [twin=%s,value=%s,t=%d].", get_formatted_timestamp(),
                                stim.twin_name, stim.value, long(stim.timestamp))
                    twin.read_value(stim.value)
                    logger.info("[%s] Issued stimulus: [twin=%s,value=%s,t=%d].", get_formatted_timestamp(),
                                stim.twin_name, stim.value, long(stim.timestamp))
                else:
                    logger.error("Twin '%s' is neither PLC nor HMI, but '%s'. Issuing stimulus failed.", twin,
                                 type(twin))
            else:
                logger.error("Twin '%s' does not exist. Issuing stimulus failed.", stim.twin_name)

        self.running = True
        logger.info("Sleeping for %d seconds", self._sleep)
        time.sleep(self._sleep)
        logger.info("Awakening after sleeping %d seconds. Now starting to process queue if not empty.", self._sleep)

        first_issued_stimulus = None
        last_issued_stimulus = None
        issue_time = 0

        while self.running:
            # Still running and queue is not empty, check if we already processed the first stimuli
            if first_issued_stimulus is None:
                # Would block if queue is empty
                _, first_issued_stimulus = self._pq.get()
                # Track issue time
                issue_time = current_ms()
                issue_stimulus(first_issued_stimulus)
                last_issued_stimulus = first_issued_stimulus
            else:
                _, st = self._pq.get()
                delta = long(st.timestamp) - long(first_issued_stimulus.timestamp)
                logger.info("Stimulus_0: %d, Stimulus_i: %d. Time difference: %d.",
                            long(first_issued_stimulus.timestamp), long(st.timestamp), delta)
                delta_last = long(st.timestamp) - long(last_issued_stimulus.timestamp)
                # Check if time difference between most recent stimulus and last issued is negative
                if delta_last < 0:
                    logger.error("State mismatch!")
                    if self.bail_out:
                        logger.info("Stopped state replication.")
                        break

                time_to_sleep = (issue_time + delta) - current_ms()
                logger.info("Issuing next stimulus in %d ms.", time_to_sleep)
                if time_to_sleep > 0:
                    logger.info("Sleeping for %d ms.", time_to_sleep)
                    force_wakeup = self._sleeper.sleep(time_to_sleep / 1000.0)
                    # Wake up if: self.running == False or new stimulus arrived
                    logger.info("Force wakeup: %s", force_wakeup)
                    if force_wakeup:
                        if not self.running:
                            break
                        logger.info("Received new stimulus while waiting to issue stimulus: %d.", long(st.timestamp))
                        # Put the stimulus again in the queue
                        self._pq.put((st.timestamp, st))
                        continue
                else:
                    logger.info("State replication delay of %d ms.", time_to_sleep * -1)

                issue_stimulus(st)
                last_issued_stimulus = st

        logger.info("Stimulus issuer terminated.")

    def stop(self):
        if self.running:
            logger.info("Stopping stimulus issuer...")
            self.running = False
            self._sleeper.wake()
        else:
            logger.info("Stimulus issuer not started. Nothing to do!")


class KafkaStimuliConsumer(Thread):

    def __init__(self, cpstw):
        Thread.__init__(self)
        self.cpstw = cpstw
        self._kafka_consumer = None
        self.running = False
        self._pq = PriorityQueue()
        self._stimulus_issuer = None
        self._sleeper = Sleep()

    def __start_stimulus_issuer(self):
        self._stimulus_issuer = StimulusIssuer(self.cpstw, self._pq, 2, self._sleeper)
        self._stimulus_issuer.start()

    def __stop_stimulus_issuer(self):
        if self._stimulus_issuer is not None:
            self._stimulus_issuer.stop()

    def run(self):
        self.running = True
        self._kafka_consumer = KafkaConsumer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                                             auto_offset_reset='latest',
                                             consumer_timeout_ms=1000)
        self._kafka_consumer.subscribe([KAFKA_STIMULI_TOPIC])

        self.__start_stimulus_issuer()

        while self.running:
            for message in self._kafka_consumer:
                # Unmarshalling
                json_msg = json.loads(message.value)
                timestamp = json_msg["timestamp"]
                twin_name = json_msg["twin_name"]
                if twin_name in self.cpstw:
                    twin = self.cpstw[twin_name]
                    stimulus = None
                    if isinstance(twin, Plc) or isinstance(twin, Hmi):
                        tag_name = json_msg["tag_name"]
                        value = json_msg.get("value")
                        stimulus = TagStimulus(timestamp, twin_name, tag_name, value)
                    elif isinstance(twin, RfidReaderMqttWiFi):
                        value = json_msg["value"]
                        stimulus = RfidStimulus(timestamp, twin_name, value)
                    else:
                        logger.error(
                            "Could not replicate state, because [type=%s] of [twin=%s] is not supported.".format(
                                type(twin), twin_name))
                    # Add incoming stimulus to queue
                    if stimulus is not None:
                        self._pq.put((stimulus.timestamp, stimulus))
                        # Wake up stimuli issuer from sleeping
                        self._sleeper.wake()
                    else:
                        logger.error(
                            "Could not replicate state, [twin=%s] is unknown.".format(twin_name))

        self._kafka_consumer.close()
        logger.info("Kafka stimuli consumer terminated.")

    def stop(self):
        if self.running:
            logger.info("Stopping Kafka stimuli consumer...")
            if self._kafka_consumer is not None:
                self.__stop_stimulus_issuer()
                self.running = False
        else:
            logger.info("Kafka stimuli consumer not started. Nothing to stop!")


class Replication(object):

    def __init__(self, cpstw):
        self.cpstw = cpstw
        self.running = False
        self._stimuli_consumer = None

    def start(self):
        if not self.running:
            logger.debug("Starting replication...")
            self.__start_stimuli_consumer()
            self.running = True
        else:
            logger.info("Replication module already started. Nothing to do...")

    def stop(self):
        if self.running:
            logger.debug("Stopping replication...")
            self.__stop_stimuli_consumer()
            self.running = False
        else:
            logger.info("Replication module already stopped. Nothing to do...")

    def __start_stimuli_consumer(self):
        self._stimuli_consumer = KafkaStimuliConsumer(self.cpstw)
        self._stimuli_consumer.start()

    def __stop_stimuli_consumer(self):
        if self._stimuli_consumer is not None:
            self._stimuli_consumer.stop()
        else:
            logger.error("Stimuli consumer has not yet been started. Nothing to stop!")
