"""Shared Cycles settings for Scene 1 (and future scenes)."""
import bpy


def apply(scene, quality='final'):
    r = scene.render
    r.engine = 'CYCLES'
    r.resolution_x, r.resolution_y = 1920, 1080
    r.resolution_percentage = 100 if quality in ('final', 'check') else 50
    r.fps = 24
    c = scene.cycles
    c.device = 'CPU'
    c.samples = {'final': 28, 'check': 16, 'preview': 10}[quality]
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.035 if quality == 'final' else 0.06
    c.use_denoising = True
    c.denoiser = 'OPENIMAGEDENOISE'
    c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    c.denoising_prefilter = 'ACCURATE'
    c.max_bounces = 5
    c.diffuse_bounces = 2
    c.glossy_bounces = 2
    c.transmission_bounces = 4
    c.transparent_max_bounces = 10
    c.volume_bounces = 0
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.blur_glossy = 1.0
    c.sample_clamp_indirect = 3.0
    c.use_light_tree = True
    r.use_persistent_data = True
    r.use_motion_blur = True
    r.motion_blur_shutter = 0.45
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.display_settings.display_device = 'sRGB'
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_depth = '8'
    r.film_transparent = False
