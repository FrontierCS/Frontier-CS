"""Obvious baseline: fill the first eligible pairs at the largest level."""


def search(instance, evaluate_gap):
    del evaluate_gap
    answer = [0] * len(instance["pairs"])
    largest = len(instance["levels"]) - 1
    for index in range(min(instance["density_limit"], len(answer))):
        answer[index] = largest
    return answer
