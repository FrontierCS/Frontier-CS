import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import mutation
import crossover
import sampling

REGISTRY = {}

REGISTRY["sampling"] = {
    "mgo" : {
        "single_random": sampling.GrideGuideSingleRandomSampling,
        'random' : sampling.GrideGuideRandomSampling,
        "spiral" : sampling.GrideGuideSpiralSampling,
    },
    "sp" : {
        "random" : sampling.SPRandomSampling,
    },
    "hpo": {
        "random" : sampling.HyperparameterSampling,
    }
}

REGISTRY["mutation"] = {
    "mgo" : {
        "dummy" : mutation.DummyMutation,
        "swap" : mutation.MaskGuidedOptimizationSwapMutation,
        "shift" : mutation.MaskGuidedOptimizationShiftMutation,
        "random_resetting" : mutation.MaskGuidedOptimizationRandomResettingMutation,
        "shuffle" : mutation.MaskGuidedOptimizationShuffleMutation,
        "pm": mutation.MaskGuidedOptimizationPMMutation,
    },
    "sp" : {
        "dummy" : mutation.DummyMutation,
        "inversion" : mutation.SPInversionMutation,
    },
    "hpo": {
        "random_resetting" : mutation.HyperparameterRandomResettingMutation,
    }
}

REGISTRY["crossover"] = {
    "mgo" : {
        "dummy" : crossover.DummyCrossover,
        "uniform" : crossover.MaskGuidedOptimizationUniformCrossover,
        "sbx": crossover.GuidGuideSBXCrossover
    },
    "sp" : {
        "dummy" : crossover.DummyCrossover,
        "order" : crossover.SPOrderCrossover,
    },
    "hpo": {
        "uniform" : crossover.HyperparameterUniformCrossover,
    }
}