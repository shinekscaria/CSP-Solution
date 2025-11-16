# simple_kmeans.py
# Lightweight K-Means implementation without external dependencies.

import random
import math


def kmeans(points, k=3, max_iter=100, seed=None):
    """
    points: list of list[float]
    returns: (labels, centroids)
    """
    if not points:
        return [], []

    n = len(points)
    dim = len(points[0])

    rnd = random.Random(seed)

    # initialize centroids: choose k distinct points
    if k > n:
        k = n
    centroids = [points[i] for i in rnd.sample(range(n), k)]

    def distance2(a, b):
        return sum((x - y) ** 2 for x, y in zip(a, b))

    labels = [0] * n

    for _ in range(max_iter):
        # assign step
        changed = False
        for i, p in enumerate(points):
            best_j = 0
            best_d = distance2(p, centroids[0])
            for j in range(1, k):
                d = distance2(p, centroids[j])
                if d < best_d:
                    best_d = d
                    best_j = j
            if labels[i] != best_j:
                labels[i] = best_j
                changed = True

        # update step
        new_centroids = [[0.0] * dim for _ in range(k)]
        counts = [0] * k
        for lbl, p in zip(labels, points):
            counts[lbl] += 1
            for d in range(dim):
                new_centroids[lbl][d] += p[d]
        for j in range(k):
            if counts[j] == 0:
                # reinitialize empty cluster to random point
                new_centroids[j] = list(points[rnd.randrange(n)])
            else:
                for d in range(dim):
                    new_centroids[j][d] /= counts[j]

        centroids = new_centroids
        if not changed:
            break

    return labels, centroids
