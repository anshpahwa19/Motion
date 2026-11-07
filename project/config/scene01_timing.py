"""Scene 1 — THE FEAR NEVER SLEEPS: master timing (24 fps, 1-based frames).
Single source of truth for animation, phone UI, audio and edit."""
FPS = 24

SHOTS = [  # name, first, last, scene, camera, description
    ('S1_establish', 1, 96, 'Bedroom', 'CAM_S1', 'Wide night bedroom, slow push-in, clock 2:17'),
    ('S2a_phone_wakes', 97, 150, 'Bedroom', 'CAM_S2a', 'Phone lights up, he turns, picks it up'),
    ('S2b_screen', 151, 216, 'Bedroom', 'CAM_S2b', 'Unlock, headline 1 then 2'),
    ('S3a_face', 217, 264, 'Bedroom', 'CAM_S3a', 'Face lit by phone, curiosity -> concern'),
    ('S3b_headline3', 265, 300, 'Bedroom', 'CAM_S3b', 'Scrolls to "Will AI replace UX designers?"'),
    ('S3c_eyes', 301, 360, 'Bedroom', 'CAM_S3c', 'Extreme close-up eyes, world darkens'),
    ('S4a_turn_away', 361, 420, 'Bedroom', 'CAM_S4a', 'Locks phone, sets it down, turns away, closes eyes'),
    ('F1_desk', 421, 438, 'Office', 'CAM_F1', 'Empty office desk'),
    ('F2_laptop', 439, 456, 'Office', 'CAM_F2', 'Laptop screen goes black'),
    ('F3_idcard', 457, 482, 'Office', 'CAM_F3', 'ID card slips off the desk and falls'),
    ('F4_chair', 483, 498, 'Office', 'CAM_F4', 'Empty chair'),
    ('F5_workspace', 499, 516, 'Office', 'CAM_F5', 'His workspace without him'),
    ('S5a_wake', 517, 560, 'Bedroom', 'CAM_S5a', 'Eyes snap open, deep breath'),
    ('S5b_clock', 561, 594, 'Bedroom', 'CAM_S5b', 'Clock still 2:17, him awake behind'),
    ('S5c_overhead', 595, 636, 'Bedroom', 'CAM_S5c', 'Top-down through the fan, pull back, fade'),
    ('T_title', 637, 744, 'Post', None, 'THE LAST LOGIN + subtitle'),
]
LAST_FRAME = 744
FADE_OUT = (612, 636)          # picture fade to black

PHONE_ON = 100                  # screen wakes (notification)
PHONE_UNLOCK = 153              # lock screen slides away
SCROLL_1 = (189, 201)           # headline 1 -> 2
SCROLL_2 = (268, 283)           # headline 2 -> 3
PHONE_LOCK = 368                # screen off
PICKUP = 134                    # hand closes on phone
PUTDOWN = 393                   # phone released on table

VO = [  # (start_seconds, text, voice)
    (0.70, "Every night, before he sleeps, he fights a battle no one can see.", 'narrator'),
    (5.55, "Not with his manager. Not with deadlines.", 'narrator'),
    (9.35, "But with a question that keeps getting louder...", 'narrator'),
    (12.95, "What if AI takes my job?", 'narrator'),
    (19.25, "What if tomorrow is my last day?", 'inner'),
]

HEADLINES = [
    ("AI can now design complete websites in seconds.", "TechPulse", "12m"),
    ("Companies are rethinking traditional design roles.", "The Business Desk", "1h"),
    ("Will AI replace UX designers?", "DesignWeek Daily", "2h"),
]
