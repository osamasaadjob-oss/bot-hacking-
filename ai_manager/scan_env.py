import gym
from gym import spaces
import numpy as np
import logging

logger = logging.getLogger(__name__)

class AdvancedScanEnv(gym.Env):
    def __init__(self):
        super(AdvancedScanEnv, self).__init__()
        self.action_space = spaces.MultiDiscrete([5, 10, 5, 5, 5])
        self.observation_space = spaces.Box(low=0, high=1, shape=(20,), dtype=np.float32)

    def reset(self):
        return np.random.rand(20)

    def step(self, action):
        reward = np.random.uniform(-1, 10)
        done = True
        return np.random.rand(20), reward, done, {}

    def update_with_new_data(self, new_data):
        pass
