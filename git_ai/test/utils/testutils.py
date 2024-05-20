import random


def sample_array(array: list, min_sample=0):
    return random.sample(array, random.randint(min_sample, len(array)))
