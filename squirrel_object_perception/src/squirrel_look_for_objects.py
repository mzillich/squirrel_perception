#!/usr/bin/env python
import rospy
import actionlib
import dynamic_reconfigure.server
from squirrel_object_perception.cfg import squirrel_look_for_objectsConfig as ConfigType
from squirrel_object_perception_msgs.srv import ObjectRecognizer, segment_init, segment_once, get_saliency
from squirrel_object_perception_msgs.msg import LookForObjectsAction, LookForObjectsFeedback, LookForObjectsResult
from sensor_msgs.msg import PointCloud2


class squirrel_look_for_objects_impl:
    _feedback = LookForObjectsFeedback()
    _result = LookForObjectsResult()
    _point_cloud = None
    _objects = None
    _saliency_map = None

    def __init__(self):

        # protected region initCode on begin #
        # protected region initCode end #
        pass

    def configure(self):
        # protected region configureCode on begin #
        # protected region configureCode end #
        pass

    def update(self):
        # protected region updateCode on begin #
        # protected region updateCode end #
        pass

    def set_publish_feedback(self, phase, status, percent):
        self._feedback.current_phase = phase
        self._feedback.current_status = status
        self._feedback.percent_completed = percent
        self.as_squirrel_object_perception.publish_feedback(self._feedback)
        print(self._feedback)
        return

    def do_recognition(self):
        recognizer = rospy.ServiceProxy('mp_recognition', ObjectRecognizer)
        result = None
        self.set_publish_feedback('recognition', 'started', 11)
        try:
            rospy.wait_for_service('mp_recognition', timeout=5)
            result = recognizer(self._point_cloud)
            self.set_publish_feedback('recognition', 'done', 50)
        except (rospy.ROSException, rospy.ServiceException) as e:
            self.set_publish_feedback('recognition', 'service call failed', 11)
            rospy.logdebug('mp_recognition: %s' % str(e))
        return result

    def get_saliency_map(self):
        get_saliency_map = rospy.ServiceProxy(
            'squirrel_attention_location', get_saliency)
        try:
            rospy.wait_for_service('squirrel_attention_location', timeout=5)
            result = get_saliency_map(self._point_cloud)
            self._saliency_map = result.saliency_map
            self.set_publish_feedback('attention', 'done', 50)
        except (rospy.ROSException, rospy.ServiceException) as e:
            self.set_publish_feedback('attention', 'service call failed', 11)
            rospy.logdebug('attention: %s' % str(e))

    def setup_segmentation(self):
        init_segmenter = rospy.ServiceProxy(
            'squirrel_segmentation_incremental_init', segment_init)
        try:
            rospy.wait_for_service(
                'squirrel_segmentation_incremental_init', timeout=5)
            init_segmenter(self._point_cloud, self._saliency_map)
            self.set_publish_feedback('attention', 'done', 50)
            return True
        except (rospy.ROSException, rospy.ServiceException) as e:
            self.set_publish_feedback('attention', 'service call failed', 11)
            rospy.logdebug('attention: %s' % str(e))
            return False

    def run_segmenter_once(self):
        do_segment = rospy.ServiceProxy(
            'squirrel_segmentation_incremental_once', segment_once)
        try:
            rospy.wait_for_service(
                'squirrel_segmentation_incremental_once', timeout=5)
            self.segment_result = do_segment()
            self.set_publish_feedback('attention', 'done', 50)
        except (rospy.ROSException, rospy.ServiceException) as e:
            self.set_publish_feedback('attention', 'service call failed', 11)
            rospy.logdebug('attention: %s' % str(e))


    def execute_squirrel_object_perception_cb(self, goal):
        # Examples: self.as_squirrel_object_perception.set_succeeded(_result)
        #           self.as_squirrel_object_perception.set_aborted()
        #           self.as_squirrel_object_perception.publish_feedback(_feedback)
        # _feedback = LookForObjectsFeedback()
        # _result = LookForObjectsResult()
        # protected region user implementation of action callback for squirrel_object_perception on begin #
        # protected region user implementation of action callback for squirrel_object_perception end #

        # initialize feedback
        self.set_publish_feedback('init', 'done', 5)

        # start executing the action
        # check that preempt has not been requested by the client
        if self.as_squirrel_object_perception.is_preempt_requested():
            rospy.loginfo('%s: Preempted' % self._action_name)
            self.as_squirrel_object_perception.set_preempted()
            return

        # Start getting data from /camera/depth_registered/points
        # Set feedback to data acquisition succeeded and set percentage
        self._point_cloud = rospy.wait_for_message(
            '/camera/depth_registered/points',
            PointCloud2,
            timeout=5
        )
        if not self._point_cloud:
            self.set_publish_feedback('receive_data', 'failed', 6)
            self._result.result_status = 'aborted'
            rospy.loginfo('Aborted' % self._action_name)
            self.as_squirrel_object_perception.set_aborted(self._result)
            return
        self.set_publish_feedback('receive_data', 'done', 10)

        # call Aitor's recognition service
        self.do_recognition()
        # Start attention, segmentation classification pipeline
        self.set_publish_feedback('attention', 'started', 51)
        self.get_saliency_map()
        self.set_publish_feedback('attention', 'done', 60)
        self.set_publish_feedback('segmentation', 'started', 61)
        self.setup_segmentation()
        self.run_segmenter_once()
        self.set_publish_feedback('segmentation', 'done', 75)
        self.set_publish_feedback('classification', 'started', 76)
        self.set_publish_feedback('classification', 'done', 97)

        # check for recognized or classified objects. Push them into database
        if not self._objects:
            self.set_publish_feedback('Pipeline results', 'empty', 99)
            self._result.result_status = 'aborted'
            rospy.loginfo('%s: Aborted' % self._action_name)
            self.as_squirrel_object_perception.set_aborted(self._result)
            return

        self.set_publish_feedback('database_update', 'started', 98)
        self.set_publish_feedback('database_update', 'done', 99)

        self.set_publish_feedback('finish', 'done', 100)
        self._result.result_status = 'success'
        rospy.loginfo('%s: Succeeded' % self._action_name)
        self.as_squirrel_object_perception.set_succeeded(self._result)
        return


class squirrel_look_for_objects:
    def __init__(self):
        self.impl = squirrel_look_for_objects_impl()
        self.impl._action_name = 'squirrel_object_perception'
        self_dynrecon_server = dynamic_reconfigure.server.Server(ConfigType, self.config_callback)
        self.impl.as_squirrel_object_perception = actionlib.SimpleActionServer('squirrel_object_perception', LookForObjectsAction, execute_cb=self.impl.execute_squirrel_object_perception_cb, auto_start=False)
        self.impl.as_squirrel_object_perception.start()

    def run(self):
        self.impl.update()

    def config_callback(self, config, level):
        return config

if __name__ == "__main__":
    try:
        rospy.init_node('squirrel_look_for_objects')
        n = squirrel_look_for_objects()
        n.impl.configure()
        while not rospy.is_shutdown():
            n.run()
            rospy.sleep(10.0)

    except rospy.ROSInterruptException:
        print "Exit"
