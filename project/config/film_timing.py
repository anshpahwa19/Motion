"""THE LAST LOGIN — full film edit (24 fps). Each 3D 'set file' has its own
timeline; the EDL below assembles shots in film order.

EDL entry: (shot, source, src_first, src_last, kind, note)
  source = 's1' | 's2bed' | 'office' | 's6' | 'ui:<name>' | 'card:<name>'
"""
FPS = 24

S2BED = [  # bedroom morning file
    ('2a_morning_wide', 1, 84, 'CAM_2a'), ('2b_alarm_cu', 85, 168, 'CAM_2b'), ('2c_bed_edge', 169, 276, 'CAM_2c'),
]
OFFICE = [  # office day file
    ('2d_office_est', 1, 96, 'CAM_2d'), ('2e_desk_side', 97, 228, 'CAM_2e'), ('2f_present_absent', 229, 336, 'CAM_2f'),
    ('3a_prompt_ots', 337, 432, 'CAM_3a'), ('3c_face_monitor', 433, 528, 'CAM_3c'), ('3e_office_wide', 529, 648, 'CAM_3e'),
    ('3f_doubt', 649, 792, 'CAM_3f'),
    ('4a_test_wide', 793, 888, 'CAM_4a'), ('4c_rao_cu', 889, 1008, 'CAM_4c'), ('4d_arjun_realises', 1009, 1116, 'CAM_4d'),
    ('4e_two_shot', 1117, 1248, 'CAM_4e'), ('4g_arjun_thinks', 1249, 1356, 'CAM_4g'),
    ('5a_sketch', 1357, 1476, 'CAM_5a'), ('5c_face_engaged', 1477, 1584, 'CAM_5c'), ('5e_rao_success', 1585, 1704, 'CAM_5e'),
    ('5f_golden_wide', 1705, 1800, 'CAM_5f'),
]
S6 = [  # bedroom night (calm) file
    ('6a_night_wide', 1, 96, 'CAM_6a'), ('6b_phone_down', 97, 228, 'CAM_6b'), ('6c_lamp_off', 229, 324, 'CAM_6c'),
    ('6d_peace_cu', 325, 444, 'CAM_6d'), ('6e_overhead', 445, 540, 'CAM_6e'),
]

UI = {  # 2D inserts: name -> frames
    'ai_generate': 144, 'ai_result': 96, 'bank_app': 96, 'notebook': 108, 'cocreate': 144, 'result_test': 108,
}

EDL = (
    [('S1', 's1', 1, 612, None)] +
    [(n, 's2bed', a, b, c) for n, a, b, c in S2BED] +
    [(n, 'office', a, b, c) for n, a, b, c in OFFICE[:3]] +
    [OFFICE[3][:0] or ('3a_prompt_ots', 'office', 337, 432, 'CAM_3a'),
     ('3b_ai_generate', 'ui:ai_generate', 1, 144, None),
     ('3c_face_monitor', 'office', 433, 528, 'CAM_3c'),
     ('3d_ai_result', 'ui:ai_result', 1, 96, None),
     ('3e_office_wide', 'office', 529, 648, 'CAM_3e'),
     ('3f_doubt', 'office', 649, 792, 'CAM_3f'),
     ('4a_test_wide', 'office', 793, 888, 'CAM_4a'),
     ('4b_bank_app', 'ui:bank_app', 1, 96, None),
     ('4c_rao_cu', 'office', 889, 1008, 'CAM_4c'),
     ('4d_arjun_realises', 'office', 1009, 1116, 'CAM_4d'),
     ('4e_two_shot', 'office', 1117, 1248, 'CAM_4e'),
     ('4f_notebook', 'ui:notebook', 1, 108, None),
     ('4g_arjun_thinks', 'office', 1249, 1356, 'CAM_4g'),
     ('5a_sketch', 'office', 1357, 1476, 'CAM_5a'),
     ('5b_cocreate', 'ui:cocreate', 1, 144, None),
     ('5c_face_engaged', 'office', 1477, 1584, 'CAM_5c'),
     ('5d_result_test', 'ui:result_test', 1, 108, None),
     ('5e_rao_success', 'office', 1585, 1704, 'CAM_5e'),
     ('5f_golden_wide', 'office', 1705, 1800, 'CAM_5f')] +
    [(n, 's6', a, b, c) for n, a, b, c in S6] +
    [('E1_card', 'card:grow', 1, 144, None), ('E2_card', 'card:create', 1, 120, None),
     ('E3_card', 'card:questions', 1, 132, None), ('E4_title', 'card:title', 1, 108, None)]
)


def total_frames():
    return sum(e[3] - e[2] + 1 for e in EDL)


SCENE_STARTS = {  # for scene title-free chaptering in the audio/score
}

if __name__ == '__main__':
    t = total_frames(); print(t, 'frames =', t / FPS, 's')


def offsets():
    """film start frame (1-based) of every EDL shot name."""
    out, f = {}, 1
    for e in EDL:
        out[e[0]] = f
        f += e[3] - e[2] + 1
    return out


def at(shot, sec_into=0.0):
    """film time (s) for a moment inside a shot."""
    return (offsets()[shot] - 1) / FPS + sec_into


# (shot, seconds into shot, text, voice)
FILM_VO = [
    ('2a_morning_wide', 0.6, "Every morning, he goes to work...", 'narrator'),
    ('2c_bed_edge', 0.4, "wondering if today could be his last day.", 'narrator'),
    ('2e_desk_side', 1.2, "He's there.", 'narrator'),
    ('2f_present_absent', 0.3, "But his mind is somewhere else.", 'narrator'),
    ('3c_face_monitor', 0.5, "The machine never sleeps. It never doubts.", 'narrator'),
    ('3e_office_wide', 0.6, "It never stops.", 'narrator'),
    ('3f_doubt', 1.4, "And slowly, he starts to believe it doesn't need him.", 'narrator'),
    ('4c_rao_cu', 1.9, "Beta... which one sends the money? All these buttons look the same.", 'rao'),
    ('4d_arjun_realises', 1.9, "But a machine can't sit beside a real person...", 'narrator'),
    ('4g_arjun_thinks', 0.3, "and notice the exact moment they get lost.", 'narrator'),
    ('5a_sketch', 0.8, "AI can give him a thousand answers.", 'narrator'),
    ('5c_face_engaged', 0.3, "His job is to bring the right questions.", 'narrator'),
    ('5f_golden_wide', 0.2, "He stopped competing with it. He started creating with it.", 'narrator'),
    ('6b_phone_down', 1.0, "Tomorrow, the machines will be smarter.", 'narrator'),
    ('6c_lamp_off', 1.6, "So will he.", 'narrator'),
    ('6e_overhead', 0.2, "And tonight... the fear finally lets him sleep.", 'narrator'),
    ('E1_card', 0.5, "AI may change your job. But don't let the fear of it take away your ability to grow.", 'narrator'),
    ('E2_card', 0.4, "Don't compete with AI. Learn to create with it.", 'narrator'),
    ('E3_card', 0.4, "Because technology can generate answers... but meaningful questions still need people.", 'narrator'),
]
