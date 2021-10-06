import toml

from _config import AgentConfig

def load_profiles(self, filepath):
    data = toml.load(filepath)
    self.profiles = data

def save_profiles(self, filepath):
    pass

def set_profile(self, profile):
    new_config = AgentConfig()

    # new_config.n = profile["N"]
    new_config.speed = profile["speed"]
    new_config.steer = profile["steer"]
    new_config.sensorAngleSpacing = profile["sensorAngleSpacing"]
    new_config.sensorDistance = profile["sensorDistance"]

    self.agent_config = new_config
