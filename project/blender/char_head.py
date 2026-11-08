"""ARJUN — head sculpt (SDF).  Head-local space: origin between the eyes,
-Y is the face direction, +Z up, +X is the character's left. Metres."""
import numpy as np
from sdf import (ellipsoid, round_cone, sphere, smin, ssub, capsule, rot,
                 value_noise3)

EYE_R = 0.0140
EYE_L = np.array([0.0316, -0.0700, 0.0])     # character's left eye centre
EYE_RT = EYE_L * np.array([-1, 1, 1])


def mirror_x(P):
    Q = P.copy(); Q[:, 0] = np.abs(Q[:, 0]); return Q


VARIANT = {}   # e.g. {'age': 1.0, 'nose': 1.15, 'cheek': 1.0} for other characters


def head_sdf(P, socket=True, neck=True):
    M = mirror_x(P)              # symmetric features evaluated on |x|
    V = VARIANT
    # --- big masses
    d = ellipsoid(P, (0, 0.006, 0.028), (0.075, 0.094, 0.092))          # cranium
    d = smin(d, ellipsoid(P, (0, -0.036, 0.044), (0.068, 0.056, 0.060)), 0.02)  # forehead
    d = smin(d, ellipsoid(P, (0, -0.030, -0.026), (0.066, 0.059, 0.060)), 0.02)  # midface
    d = smin(d, ellipsoid(P, (0, -0.020, -0.060), (0.053, 0.058, 0.044)), 0.02)  # jaw mass
    d = smin(d, sphere(M, (0.044, -0.002, -0.060), 0.014), 0.03)                # jaw angle
    d = smin(d, capsule(M, (0.0, -0.058, -0.091), (0.045, 0.002, -0.069), 0.014), 0.025)
    d = smin(d, ellipsoid(P, (0, -0.063, -0.093), (0.022, 0.018, 0.016)), 0.014)  # chin
    d = smin(d, ellipsoid(M, (0.044, -0.058, -0.019), (0.024, 0.017, 0.016)), 0.016)  # cheekbone
    d = smin(d, ellipsoid(M, (0.034, -0.052, -0.040), (0.020, 0.019, 0.021)), 0.02)  # cheek fullness
    d = smin(d, ellipsoid(M, (0.028, -0.075, 0.020), (0.029, 0.013, 0.010),
                          rot('y', -8)), 0.014)                            # brow ridge
    # --- nose
    nose = round_cone(P, (0, -0.079, 0.010), (0, -0.101, -0.027), 0.0072, 0.0098)
    nose = smin(nose, sphere(P, (0, -0.1005, -0.0295), 0.0122), 0.006)
    nose = smin(nose, ellipsoid(M, (0.0135, -0.0900, -0.0345), (0.0082, 0.0092, 0.0072)), 0.005)
    d = smin(d, nose, 0.007)
    d = ssub(d, ellipsoid(M, (0.0072, -0.0965, -0.0405), (0.0035, 0.0045, 0.0022)), 0.0025)
    # --- mouth area
    d = smin(d, ellipsoid(P, (0, -0.075, -0.050), (0.025, 0.014, 0.013)), 0.010)   # philtrum zone
    d = smin(d, ellipsoid(P, (0, -0.0835, -0.0566), (0.0200, 0.0080, 0.0060)), 0.005)  # upper lip
    d = smin(d, ellipsoid(M, (0.0062, -0.0850, -0.0552), (0.0075, 0.0062, 0.0042)), 0.003)  # cupid's bow
    d = smin(d, ellipsoid(P, (0, -0.0818, -0.0662), (0.0180, 0.0094, 0.0074)), 0.005)  # lower lip
    d = ssub(d, ellipsoid(P, (0, -0.091, -0.0610), (0.0205, 0.0125, 0.0009)), 0.0018)  # slit
    d = ssub(d, sphere(M, (0.0208, -0.0772, -0.0624), 0.0028), 0.004)                # corners
    d = ssub(d, ellipsoid(P, (0, -0.080, -0.080), (0.016, 0.004, 0.005)), 0.008)     # mentolabial
    # --- ears
    ear = ellipsoid(M, (0.0760, 0.014, -0.008), (0.0095, 0.0175, 0.0275), rot('z', -18))
    ear = ssub(ear, ellipsoid(M, (0.0825, 0.012, -0.010), (0.0055, 0.0115, 0.0190), rot('z', -18)), 0.003)
    d = smin(d, ear, 0.006)
    # --- neck
    if neck:
        d = smin(d, round_cone(P, (0, 0.020, -0.080), (0, 0.024, -0.21), 0.052, 0.057), 0.014)
    # --- character variants (age: jowls, folds, bags; bigger nose; fuller cheeks)
    age = V.get('age', 0.0)
    if V.get('nose', 1.0) != 1.0:
        k = V['nose']
        d = smin(d, sphere(P, (0, -0.1005 - 0.004 * (k - 1), -0.0305), 0.0122 * k), 0.006)
        d = smin(d, ellipsoid(M, (0.0145 * k, -0.0895, -0.0355), (0.0085 * k, 0.0095, 0.0075)), 0.005)
    if V.get('cheek', 0.0):
        d = smin(d, ellipsoid(M, (0.040, -0.050, -0.045), (0.024, 0.022, 0.026)), 0.02)
    if age:
        d = smin(d, ellipsoid(M, (0.040, -0.040, -0.080), (0.020 * age, 0.024, 0.020 * age)), 0.02)   # jowls
        d = smin(d, ellipsoid(M, (0.031, -0.077, -0.018), (0.012, 0.006 * age, 0.0045)), 0.006)       # eye bags
        d = ssub(d, capsule(M, (0.019, -0.093, -0.036), (0.030, -0.080, -0.068), 0.0012 * age), 0.003)  # nasolabial
        d = ssub(d, capsule(P, (-0.03, -0.090, 0.046), (0.03, -0.090, 0.046), 0.0006 * age), 0.002)     # forehead line
        d = ssub(d, capsule(P, (-0.026, -0.088, 0.056), (0.026, -0.088, 0.056), 0.0005 * age), 0.002)
    # --- eye sockets (lids are separate shells)
    if socket:
        for E in (EYE_L, EYE_RT):
            d = ssub(d, sphere(P, E, EYE_R + 0.0009), 0.0022)
    return d


BBOX = ((-0.105, -0.125, -0.215), (0.105, 0.125, 0.135))
