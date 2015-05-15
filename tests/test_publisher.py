import unittest
import math

try:
    from unittest.mock import patch, ANY
except ImportError:
    from mock import patch, ANY

from trajectory_publisher import *

class ActuatorPublisherTestCase(unittest.TestCase):
    def test_can_create(self):
        pub = ActuatorPublisher()
        self.assertEqual(pub.trajectories, {})

    def test_can_update_actuator(self):
        pub = ActuatorPublisher()
        t1 = Trajectory(0., 1., (1, 2, 3))
        pub.update_actuator("base", t1)
        self.assertEqual(pub.trajectories, {'base': t1})

    def test_can_merge(self):
        pub = ActuatorPublisher()
        t1 = Trajectory(0., 1., (1, 2, 3))
        t2 = Trajectory(1., 1., (10, 20, 30))
        pub.update_actuator("base", t1)
        pub.update_actuator("base", t2)

        traj = pub.trajectories['base']

        self.assertEqual(traj, Trajectory(0., 1., (1, 10, 20, 30)))

    def test_can_get_trajectory_point(self):
        pub = ActuatorPublisher()
        pub.update_actuator("base", Trajectory(0., 1., (1, 2, 3)))

        state = pub.get_state("base", 1.4)
        self.assertEqual(state, 2)

    def test_can_get_sepoint(self):
        pub = ActuatorPublisher()

        pub.update_actuator("base", PositionSetpoint(10))
        state = pub.get_state("base", 1.4)
        self.assertEqual(state, PositionSetpoint(10))

    def test_can_gc(self):
        pub = ActuatorPublisher()
        traj = Trajectory(4., 1., (1, 2, 3, 4))
        pub.update_actuator("base", traj)
        pub.gc(6.)
        self.assertEqual(pub.trajectories['base'].points, (3, 4))

    def test_dont_gc_setpoint(self):
        pub = ActuatorPublisher()
        p = PositionSetpoint(10)
        pub.update_actuator("base", p)
        pub.gc(6.)
        self.assertEqual(pub.trajectories['base'], p)

    def test_publish_exists(self):
        pub = ActuatorPublisher()
        pub.publish(date=10.)


class SimpleRPCPublisherTestCase(unittest.TestCase):
    def setUp(self):
        self.pub = SimpleRPCActuatorPublisher(('localhost', 20000))

    def test_create(self):
        self.assertEqual(self.pub.trajectories, {})
        self.assertEqual(self.pub.target, ('localhost', 20000))

    def test_publish_positionpoint(self):
        self.pub.update_actuator('foo', PositionSetpoint(10.))

        with patch('cvra_rpc.message.send') as send:
            self.pub.publish(date=10.)
            send.assert_any_call(self.pub.target, 'actuator_position', ['foo', 10.])

    def test_publish_speed(self):
        self.pub.update_actuator('foo', SpeedSetpoint(10.))
        with patch('cvra_rpc.message.send') as send:
            self.pub.publish(date=10.)
            send.assert_any_call(self.pub.target, 'actuator_velocity', ['foo', 10.])

    def test_publish_torque(self):
        self.pub.update_actuator('foo', TorqueSetpoint(10.))
        with patch('cvra_rpc.message.send') as send:
            self.pub.publish(date=10.)
            send.assert_any_call(self.pub.target, 'actuator_torque', ['foo', 10.])

    def test_publish_chunk(self):
        traj = Trajectory(0.01, dt=0.5,
                          points=tuple(TrajectoryPoint(float(i), 10.,
                                                       acceleration=20.,
                                                       torque=30.)
                                       for i in range(100)))

        self.pub.update_actuator('foo', traj)

        expected_points = [[float(i), 10., 20., 30.] for i in range(20, 30)]

        with patch('cvra_rpc.message.send') as send:
            self.pub.publish(date=10.)
            # 9999 instead of 10000 us because of rounding error
            send.assert_any_call(self.pub.target, 'actuator_trajectory',
                                 ['foo', 10, 9999, expected_points])

