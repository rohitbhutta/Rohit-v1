#!/usr/bin/env python3
"""
AI Faceless Studio — Web UI
Beautiful web interface for generating YouTube Shorts from a topic.
Just open http://localhost:5000 and type your topic!
"""

import os
import sys
# Fix Windows console encoding so emojis don't crash prints
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
os.environ['PYTHONIOENCODING'] = 'utf-8'
import json
import uuid
import re
import threading
import webbrowser
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, jsonify, request, send_from_directory

# Add scripts directory to path
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')
sys.path.insert(0, SCRIPTS_DIR)

from config_loader import load_config

app = Flask(__name__)

# In-memory job storage
jobs = {}

VOICE_PRESETS = {
    'auto_smart': {'label': 'Smart Match', 'voice': ''},
    'male_calm': {'label': 'Male Calm', 'voice': 'en-US-GuyNeural'},
    'male_deep': {'label': 'Male Deep', 'voice': 'en-US-ChristopherNeural'},
    'male_british': {'label': 'Male British', 'voice': 'en-GB-RyanNeural'},
    'female_warm': {'label': 'Female Warm', 'voice': 'en-US-JennyNeural'},
    'female_clear': {'label': 'Female Clear', 'voice': 'en-US-AriaNeural'},
    'female_story': {'label': 'Female Story', 'voice': 'en-AU-NatashaNeural'},
}

VIBE_PRESETS = {
    'auto': {
        'label': 'Auto Match',
        'script_style': 'Choose the best storytelling mode from the topic itself. Stay natural and audience-first.',
        'seo_style': 'Match the strongest YouTube Shorts framing for the topic.',
        'visual_terms': '',
    },
    'informative': {
        'label': 'Informative',
        'script_style': 'Use clear, researched, trustworthy explanation. Prioritize defensible facts and clarity.',
        'seo_style': 'Frame the video as useful, credible, and high-value.',
        'visual_terms': 'clean factual visuals documentary style',
    },
    'storytelling': {
        'label': 'Storytelling',
        'script_style': 'Tell it like a tight story with setup, escalation, and payoff.',
        'seo_style': 'Emphasize curiosity, narrative tension, and payoff.',
        'visual_terms': 'cinematic storytelling dramatic sequence',
    },
    'sci_fi': {
        'label': 'Sci-Fi',
        'script_style': 'Lean futuristic, imaginative, and cinematic while staying coherent.',
        'seo_style': 'Use futuristic, high-concept, curiosity-driven framing.',
        'visual_terms': 'futuristic sci fi neon space technology',
    },
    'money': {
        'label': 'Money Earned',
        'script_style': 'Focus on money, business, growth, leverage, upside, and real-world opportunity.',
        'seo_style': 'Use wealth, business, income, and high-upside language without sounding spammy.',
        'visual_terms': 'money business growth charts luxury success',
    },
    'mystery': {
        'label': 'Mystery',
        'script_style': 'Use suspense, unanswered questions, and gradual reveals.',
        'seo_style': 'Frame the hook around intrigue and the need to know.',
        'visual_terms': 'mystery dark atmospheric reveal',
    },
    'luxury': {
        'label': 'Luxury',
        'script_style': 'Make it sleek, premium, aspirational, and polished.',
        'seo_style': 'Use elite, premium, rare, and aspirational language with restraint.',
        'visual_terms': 'luxury premium lifestyle elegant wealth',
    },
    'motivational': {
        'label': 'Motivational',
        'script_style': 'Make it energizing, direct, and emotionally activating.',
        'seo_style': 'Push drive, transformation, momentum, and action.',
        'visual_terms': 'motivation fitness achievement sunrise',
    },
    'shocking_facts': {
        'label': 'Shocking Facts',
        'script_style': 'Use sharp reveal-driven fact delivery with big contrast and surprise.',
        'seo_style': 'Frame around unbelievable but credible facts.',
        'visual_terms': 'surprising facts dramatic close up',
    },
    'dark_truth': {
        'label': 'Dark Truth',
        'script_style': 'Use serious, high-stakes, unsettling framing without becoming melodramatic.',
        'seo_style': 'Emphasize hidden reality, consequences, and tension.',
        'visual_terms': 'dark moody reality serious tension',
    },
    'future_tech': {
        'label': 'Future Tech',
        'script_style': 'Focus on innovation, next-wave technology, and what changes next.',
        'seo_style': 'Use advanced tech, disruption, future, and breakthrough framing.',
        'visual_terms': 'future technology robotics ai innovation',
    },
}

DEFAULT_PREVIEW_TEXT = (
    "This is a live preview of your voice, timing, and subtitle grouping. "
    "Adjust the speed, switch the voice, and change the caption size until it feels right."
)
SCRIPT_GENERATION_TIMEOUT_SECONDS = 120

SUBTITLE_STYLE_PRESETS = {
    'auto_smart': {
        'label': 'Smart Match',
        'font_color': [255, 255, 255],
        'highlight_color': [42, 201, 161],
        'stroke_color': [0, 0, 0],
        'highlight_mode': 'keywords',
    },
    'clean_white': {
        'label': 'Clean White',
        'font_color': [255, 255, 255],
        'highlight_color': [42, 201, 161],
        'stroke_color': [0, 0, 0],
        'highlight_mode': 'keywords',
    },
    'money_glow': {
        'label': 'Money Glow',
        'font_color': [255, 249, 230],
        'highlight_color': [255, 214, 74],
        'stroke_color': [16, 24, 16],
        'highlight_mode': 'keywords',
    },
    'neon_tech': {
        'label': 'Neon Tech',
        'font_color': [226, 248, 255],
        'highlight_color': [0, 229, 255],
        'stroke_color': [3, 8, 18],
        'highlight_mode': 'keywords',
    },
    'dark_contrast': {
        'label': 'Dark Contrast',
        'font_color': [255, 255, 255],
        'highlight_color': [255, 105, 104],
        'stroke_color': [0, 0, 0],
        'highlight_mode': 'keywords',
    },
    'luxury_gold': {
        'label': 'Luxury Gold',
        'font_color': [252, 247, 239],
        'highlight_color': [233, 196, 106],
        'stroke_color': [26, 20, 12],
        'highlight_mode': 'last_word',
    },
    'documentary_blue': {
        'label': 'Documentary Blue',
        'font_color': [245, 248, 252],
        'highlight_color': [130, 196, 255],
        'stroke_color': [5, 12, 22],
        'highlight_mode': 'keywords',
    },
}

SUBTITLE_POSITION_PRESETS = {
    'auto_smart': {'label': 'Smart Match', 'anchor': 'lower_third'},
    'top_banner': {'label': 'Top Banner', 'anchor': 'top'},
    'center_focus': {'label': 'Center Focus', 'anchor': 'center'},
    'lower_third': {'label': 'Lower Third', 'anchor': 'lower_third'},
    'bottom_punch': {'label': 'Bottom Punch', 'anchor': 'bottom'},
}

SMART_VOICE_BY_VIBE = {
    'informative': ('male_calm', 'Clear authority fits informative topics best.'),
    'storytelling': ('female_story', 'Warm narrative delivery fits storytelling best.'),
    'sci_fi': ('male_british', 'A cinematic British read matches sci-fi pacing well.'),
    'money': ('male_deep', 'Deeper delivery fits money and authority topics.'),
    'mystery': ('male_british', 'A suspenseful British tone supports mystery pacing.'),
    'luxury': ('female_clear', 'A polished, premium voice suits luxury content.'),
    'motivational': ('male_deep', 'A stronger, deeper voice helps motivational delivery.'),
    'shocking_facts': ('female_clear', 'Crisp contrast helps reveal-style facts land better.'),
    'dark_truth': ('male_british', 'A serious, dramatic delivery supports darker themes.'),
    'future_tech': ('female_clear', 'A sharp modern voice suits future-tech topics.'),
}

SMART_SUBTITLE_STYLE_BY_VIBE = {
    'informative': 'documentary_blue',
    'storytelling': 'clean_white',
    'sci_fi': 'neon_tech',
    'money': 'money_glow',
    'mystery': 'dark_contrast',
    'luxury': 'luxury_gold',
    'motivational': 'money_glow',
    'shocking_facts': 'dark_contrast',
    'dark_truth': 'dark_contrast',
    'future_tech': 'neon_tech',
}

SMART_SUBTITLE_POSITION_BY_VIBE = {
    'informative': 'lower_third',
    'storytelling': 'center_focus',
    'sci_fi': 'center_focus',
    'money': 'top_banner',
    'mystery': 'center_focus',
    'luxury': 'lower_third',
    'motivational': 'bottom_punch',
    'shocking_facts': 'top_banner',
    'dark_truth': 'center_focus',
    'future_tech': 'center_focus',
}

HIGHLIGHT_MODE_LABELS = {
    'keywords': 'Auto Keywords',
    'last_word': 'Last Word',
    'off': 'Off',
}

ASPECT_RATIO_PRESETS = {
    'vertical_9_16': {'label': 'Vertical 9:16', 'width_ratio': 9, 'height_ratio': 16, 'preview_css': '9 / 16'},
    'portrait_4_5': {'label': 'Portrait 4:5', 'width_ratio': 4, 'height_ratio': 5, 'preview_css': '4 / 5'},
    'square_1_1': {'label': 'Square 1:1', 'width_ratio': 1, 'height_ratio': 1, 'preview_css': '1 / 1'},
    'landscape_16_9': {'label': 'Landscape 16:9', 'width_ratio': 16, 'height_ratio': 9, 'preview_css': '16 / 9'},
}

QUALITY_PRESETS = {
    'fast_720': {
        'label': 'Fast 720p',
        'short_edge': 720,
        'fps': 24,
        'raw_bitrate': '5M',
        'final_bitrate': '7M',
        'audio_bitrate': '128k',
        'encode_preset': 'medium',
    },
    'hd_1080': {
        'label': 'HD 1080p',
        'short_edge': 1080,
        'fps': 30,
        'raw_bitrate': '10M',
        'final_bitrate': '12M',
        'audio_bitrate': '192k',
        'encode_preset': 'slow',
    },
    'ultra_1440': {
        'label': 'Ultra 1440p',
        'short_edge': 1440,
        'fps': 30,
        'raw_bitrate': '16M',
        'final_bitrate': '18M',
        'audio_bitrate': '192k',
        'encode_preset': 'slow',
    },
}


def sanitize_name(topic):
    name = re.sub(r'[^\w\s-]', '', topic.lower())
    return re.sub(r'\s+', '_', name.strip())[:40]


def update_job(job_id, step_num, step_name, message, progress, done=False):
    job = jobs[job_id]
    job['current_step'] = step_name
    job['current_message'] = message
    job['progress'] = progress
    job['status'] = 'running'
    if done:
        job['completed_steps'].append({
            'step': step_num,
            'name': step_name,
            'message': message
        })


def mark_job_cancelled(job, message='Generation stopped.'):
    job['status'] = 'cancelled'
    job['current_message'] = message
    job['error'] = None


def ensure_not_cancelled(job):
    if job.get('cancel_requested'):
        mark_job_cancelled(job)
        raise RuntimeError('__JOB_CANCELLED__')


def clamp_int(value, default, min_value, max_value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = default
    return max(min_value, min(max_value, value))


def clamp_duration_seconds(value):
    value = clamp_int(value, 40, 5, 60)
    return max(5, min(60, round(value / 5) * 5))


def even_int(value):
    value = int(round(value))
    return value if value % 2 == 0 else value + 1


def edge_rate(value):
    value = clamp_int(value, -12, -40, 20)
    sign = '+' if value >= 0 else ''
    return f'{sign}{value}%'


def rate_percent_to_multiplier(rate_text):
    try:
        percent = int(str(rate_text).replace('%', ''))
    except ValueError:
        percent = 0
    return max(0.6, 1 + (percent / 100))


def estimate_target_word_count(duration_seconds, rate_text):
    words_per_second = 2.4 * rate_percent_to_multiplier(rate_text)
    return max(14, int(round(duration_seconds * words_per_second)))


def fit_preview_text_to_duration(preview_text, duration_seconds, rate_text):
    words = preview_text.split()
    if not words:
        words = DEFAULT_PREVIEW_TEXT.split()

    target_words = estimate_target_word_count(duration_seconds, rate_text)
    expanded_words = []
    while len(expanded_words) < target_words:
        expanded_words.extend(words)
    fitted = " ".join(expanded_words[:target_words])
    return fitted


def generate_script_via_subprocess(topic, options):
    """Run script generation in an isolated Python process with a hard timeout."""
    script_path = os.path.join(SCRIPTS_DIR, 'generate_script_json.py')
    command = [
        sys.executable,
        script_path,
        "--topic",
        topic,
        "--duration",
        str(options['duration_seconds']),
        f"--voice-rate={options['voice_rate']}",
        f"--vibe-label={options['vibe_label']}",
        f"--vibe-script-style={options['vibe_script_style']}",
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    completed = subprocess.run(
        command,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        capture_output=True,
        text=True,
        encoding='utf-8',
        timeout=SCRIPT_GENERATION_TIMEOUT_SECONDS,
        creationflags=creationflags,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or '').strip()
        stdout = (completed.stdout or '').strip()
        raise RuntimeError(
            "Script generation subprocess failed: "
            + (stderr or stdout or f"exit code {completed.returncode}")
        )

    stdout = (completed.stdout or '').strip()
    match = re.search(r"\{.*\}", stdout, re.DOTALL)
    if not match:
        raise RuntimeError("Script generation subprocess returned invalid JSON output.")
    return json.loads(match.group())


def _topic_keywords(text):
    return set(re.findall(r'[a-z0-9]+', str(text or '').lower()))


def pick_smart_voice(topic, vibe):
    vibe_key = vibe if vibe in SMART_VOICE_BY_VIBE else 'informative'
    keywords = _topic_keywords(topic)
    if vibe_key != 'auto' and vibe_key in SMART_VOICE_BY_VIBE:
        if vibe_key not in {'future_tech', 'sci_fi'}:
            return SMART_VOICE_BY_VIBE[vibe_key]
    if {'ai', 'tech', 'robot', 'future', 'software', 'startup'} & keywords:
        return 'female_clear', 'Modern tech topics work better with a sharper voice.'
    if {'mystery', 'dark', 'secret', 'hidden', 'crime'} & keywords:
        return 'male_british', 'Suspense-driven topics benefit from a more dramatic tone.'
    if {'money', 'wealth', 'business', 'income', 'rich', 'luxury'} & keywords:
        return 'male_deep', 'Authority-heavy topics work better with a deeper voice.'
    return SMART_VOICE_BY_VIBE.get(vibe_key, ('male_calm', 'A balanced clear voice is the safest fit.'))


def resolve_subtitle_style(style_key, vibe):
    if style_key not in SUBTITLE_STYLE_PRESETS:
        style_key = 'auto_smart'
    if style_key == 'auto_smart':
        style_key = SMART_SUBTITLE_STYLE_BY_VIBE.get(vibe, 'clean_white')
    style = SUBTITLE_STYLE_PRESETS[style_key]
    return style_key, style


def resolve_subtitle_position(position_key, vibe):
    if position_key not in SUBTITLE_POSITION_PRESETS:
        position_key = 'auto_smart'
    if position_key == 'auto_smart':
        position_key = SMART_SUBTITLE_POSITION_BY_VIBE.get(vibe, 'lower_third')
    position = SUBTITLE_POSITION_PRESETS[position_key]
    return position_key, position


def resolve_video_profile(aspect_key, quality_key):
    if aspect_key not in ASPECT_RATIO_PRESETS:
        aspect_key = 'vertical_9_16'
    if quality_key not in QUALITY_PRESETS:
        quality_key = 'hd_1080'

    aspect = ASPECT_RATIO_PRESETS[aspect_key]
    quality = QUALITY_PRESETS[quality_key]
    width_ratio = aspect['width_ratio']
    height_ratio = aspect['height_ratio']
    short_edge = quality['short_edge']

    if width_ratio >= height_ratio:
        height = even_int(short_edge)
        width = even_int(height * (width_ratio / height_ratio))
    else:
        width = even_int(short_edge)
        height = even_int(width * (height_ratio / width_ratio))

    return aspect_key, quality_key, {
        'aspect_ratio_label': aspect['label'],
        'aspect_ratio_css': aspect['preview_css'],
        'quality_label': quality['label'],
        'resolution_width': width,
        'resolution_height': height,
        'resolution_label': f'{width}x{height}',
        'fps': quality['fps'],
        'raw_bitrate': quality['raw_bitrate'],
        'final_bitrate': quality['final_bitrate'],
        'audio_bitrate': quality['audio_bitrate'],
        'encode_preset': quality['encode_preset'],
    }


def parse_options(data):
    options = data.get('options') or {}
    topic = data.get('topic', '')
    voice_preset = options.get('voice_preset', 'auto_smart')
    if voice_preset not in VOICE_PRESETS:
        voice_preset = 'auto_smart'
    vibe = options.get('vibe', 'auto')
    if vibe not in VIBE_PRESETS:
        vibe = 'auto'

    video_source = options.get('video_source', 'pexels')
    if video_source not in {'pexels', 'local'}:
        video_source = 'pexels'

    if voice_preset == 'auto_smart':
        resolved_voice_preset, voice_reason = pick_smart_voice(topic, vibe)
        voice_requested_label = VOICE_PRESETS['auto_smart']['label']
    else:
        resolved_voice_preset = voice_preset
        voice_reason = 'Manual voice selection.'
        voice_requested_label = VOICE_PRESETS[voice_preset]['label']

    style_key, style = resolve_subtitle_style(options.get('subtitle_style_preset', 'auto_smart'), vibe)
    position_key, position = resolve_subtitle_position(options.get('subtitle_position_preset', 'auto_smart'), vibe)
    aspect_key, quality_key, video_profile = resolve_video_profile(
        options.get('aspect_ratio_preset', 'vertical_9_16'),
        options.get('quality_preset', 'hd_1080'),
    )
    highlight_mode = str(options.get('subtitle_highlight_mode') or style.get('highlight_mode', 'keywords')).strip().lower()
    if highlight_mode not in HIGHLIGHT_MODE_LABELS:
        highlight_mode = style.get('highlight_mode', 'keywords')

    return {
        'smart_preset': str(options.get('smart_preset', 'auto_topic')).strip() or 'auto_topic',
        'voice_preset': resolved_voice_preset,
        'voice_requested_preset': voice_preset,
        'voice_requested_label': voice_requested_label,
        'voice_label': VOICE_PRESETS[resolved_voice_preset]['label'],
        'voice': VOICE_PRESETS[resolved_voice_preset]['voice'],
        'voice_reason': voice_reason,
        'vibe': vibe,
        'vibe_label': VIBE_PRESETS[vibe]['label'],
        'vibe_script_style': VIBE_PRESETS[vibe]['script_style'],
        'vibe_seo_style': VIBE_PRESETS[vibe]['seo_style'],
        'vibe_visual_terms': VIBE_PRESETS[vibe]['visual_terms'],
        'voice_rate': edge_rate(options.get('voice_rate')),
        'duration_seconds': clamp_duration_seconds(options.get('duration_seconds')),
        'video_source': video_source,
        'aspect_ratio_preset': aspect_key,
        'aspect_ratio_label': video_profile['aspect_ratio_label'],
        'aspect_ratio_css': video_profile['aspect_ratio_css'],
        'quality_preset': quality_key,
        'quality_label': video_profile['quality_label'],
        'resolution_width': video_profile['resolution_width'],
        'resolution_height': video_profile['resolution_height'],
        'resolution_label': video_profile['resolution_label'],
        'fps': video_profile['fps'],
        'raw_bitrate': video_profile['raw_bitrate'],
        'final_bitrate': video_profile['final_bitrate'],
        'audio_bitrate': video_profile['audio_bitrate'],
        'encode_preset': video_profile['encode_preset'],
        'visual_query': str(options.get('visual_query', '')).strip(),
        'subtitles_enabled': bool(options.get('subtitles_enabled', True)),
        'subtitle_font_size': clamp_int(options.get('subtitle_font_size'), 65, 36, 90),
        'subtitle_words_per_group': clamp_int(options.get('subtitle_words_per_group'), 3, 1, 6),
        'subtitle_style_preset': style_key,
        'subtitle_style_label': style['label'],
        'subtitle_font_color': style['font_color'],
        'subtitle_highlight_color': style['highlight_color'],
        'subtitle_stroke_color': style['stroke_color'],
        'subtitle_highlight_mode': highlight_mode,
        'subtitle_highlight_mode_label': HIGHLIGHT_MODE_LABELS[highlight_mode],
        'subtitle_position_preset': position_key,
        'subtitle_position_label': position['label'],
        'subtitle_position_anchor': position['anchor'],
    }


def normalize_preview_text(value):
    text = re.sub(r'\s+', ' ', str(value or '')).strip()
    if not text:
        return DEFAULT_PREVIEW_TEXT
    return text[:280]


# ── Routes ───────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.get_json(silent=True) or {}
    data.pop('preview_text', None)
    topic = data.get('topic', '').strip()
    if not topic:
        return jsonify({'error': 'Topic is required'}), 400
    options = parse_options(data)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        'status': 'starting',
        'topic': topic,
        'options': options,
        'cancel_requested': False,
        'progress': 0,
        'current_step': 'Initializing...',
        'current_message': '',
        'completed_steps': [],
        'result': None,
        'error': None,
    }

    thread = threading.Thread(target=run_pipeline, args=(job_id, topic, options), daemon=True)
    thread.start()

    return jsonify({'job_id': job_id})


@app.route('/api/status/<job_id>')
def api_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)


@app.route('/api/cancel/<job_id>', methods=['POST'])
def api_cancel(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    job['cancel_requested'] = True
    if job.get('status') in {'starting', 'running'}:
        job['current_message'] = 'Stopping after the current step...'
    return jsonify({'ok': True, 'status': job.get('status')})


@app.route('/api/preview', methods=['POST'])
def api_preview():
    data = request.get_json(silent=True) or {}
    options = parse_options(data)
    preview_text = normalize_preview_text(data.get('preview_text') or data.get('topic'))
    target_duration_seconds = options['duration_seconds']
    fitted_preview_text = fit_preview_text_to_duration(
        preview_text,
        target_duration_seconds,
        options['voice_rate'],
    )

    config = load_config()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(base_dir, 'temp')
    preview_dir = os.path.join(temp_dir, 'preview')
    os.makedirs(preview_dir, exist_ok=True)

    config.setdefault('paths', {})['temp'] = temp_dir
    config.setdefault('subtitles', {})['enabled'] = True
    config['subtitles']['font_size'] = options['subtitle_font_size']
    config['subtitles']['words_per_group'] = options['subtitle_words_per_group']
    config['subtitles']['font_color'] = options['subtitle_font_color']
    config['subtitles']['highlight_color'] = options['subtitle_highlight_color']
    config['subtitles']['stroke_color'] = options['subtitle_stroke_color']
    config['subtitles']['highlight_mode'] = options['subtitle_highlight_mode']
    config['subtitles']['position_anchor'] = options['subtitle_position_anchor']
    config.setdefault('video', {})['resolution_width'] = options['resolution_width']
    config['video']['resolution_height'] = options['resolution_height']
    config['video']['fps'] = options['fps']

    cache_payload = json.dumps({
        'text': fitted_preview_text,
        'voice': options['voice'],
        'rate': options['voice_rate'],
        'duration_seconds': target_duration_seconds,
        'subtitle_font_size': options['subtitle_font_size'],
        'subtitle_words_per_group': options['subtitle_words_per_group'],
    }, sort_keys=True)
    cache_key = hashlib.md5(cache_payload.encode('utf-8')).hexdigest()[:16]
    audio_filename = f'{cache_key}.mp3'
    timing_filename = f'{cache_key}.json'
    audio_path = os.path.join(preview_dir, audio_filename)
    timing_path = os.path.join(preview_dir, timing_filename)

    from voice_generator import VoiceGenerator
    from subtitle_generator import SubtitleGenerator
    from moviepy.editor import AudioFileClip

    word_timings = None
    if os.path.exists(timing_path):
        with open(timing_path, 'r', encoding='utf-8') as f:
            word_timings = json.load(f)

    if not os.path.exists(audio_path) or word_timings is None:
        voice_gen = VoiceGenerator(config)
        _, word_timings = voice_gen.generate_voiceover_with_timing(
            fitted_preview_text,
            audio_path,
            voice_override=options['voice'],
            rate_override=options['voice_rate'],
        )
        with open(timing_path, 'w', encoding='utf-8') as f:
            json.dump(word_timings or [], f, ensure_ascii=False)

    clip = AudioFileClip(audio_path)
    duration = clip.duration
    clip.close()

    subtitle_gen = SubtitleGenerator(config)
    subtitle_data = subtitle_gen.generate_subtitle_data(
        fitted_preview_text,
        duration,
        word_timings=word_timings,
    )

    return jsonify({
        'audio_url': f'/preview-media/{audio_filename}',
        'duration': round(duration, 2),
        'subtitle_data': subtitle_data,
        'preview_text': preview_text,
        'target_duration_seconds': target_duration_seconds,
        'voice': options['voice'],
        'voice_label': options['voice_label'],
        'voice_reason': options['voice_reason'],
        'voice_rate': options['voice_rate'],
        'subtitle_font_size': options['subtitle_font_size'],
        'subtitle_words_per_group': options['subtitle_words_per_group'],
        'subtitle_style_label': options['subtitle_style_label'],
        'subtitle_position_label': options['subtitle_position_label'],
        'subtitle_position_anchor': options['subtitle_position_anchor'],
        'subtitle_highlight_mode': options['subtitle_highlight_mode'],
        'subtitle_highlight_mode_label': options['subtitle_highlight_mode_label'],
        'aspect_ratio_label': options['aspect_ratio_label'],
        'aspect_ratio_css': options['aspect_ratio_css'],
        'quality_label': options['quality_label'],
        'resolution_label': options['resolution_label'],
        'subtitle_primary_color': options['subtitle_font_color'],
        'subtitle_highlight_color': options['subtitle_highlight_color'],
    })


@app.route('/api/history')
def api_history():
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    videos = []
    if os.path.exists(output_dir):
        for folder in sorted(os.listdir(output_dir), reverse=True)[:20]:
            folder_path = os.path.join(output_dir, folder)
            if not os.path.isdir(folder_path):
                continue
            meta_path = os.path.join(folder_path, 'metadata.json')
            title = folder
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    title = meta.get('title', folder)
                except Exception:
                    pass
            videos.append({
                'folder': folder,
                'title': title,
                'path': folder_path,
                'video_url': f'/media/{folder}/final.mp4',
                'thumbnail_url': f'/media/{folder}/thumbnail.png',
            })
    return jsonify(videos)


@app.route('/media/<folder>/<filename>')
def media(folder, filename):
    safe_folder = os.path.basename(folder)
    if filename not in {'final.mp4', 'thumbnail.png', 'voiceover.mp3'}:
        return jsonify({'error': 'File not available'}), 404
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', safe_folder)
    if not os.path.isdir(output_dir):
        return jsonify({'error': 'Output folder not found'}), 404
    return send_from_directory(output_dir, filename)


@app.route('/preview-media/<filename>')
def preview_media(filename):
    if not re.fullmatch(r'[a-f0-9]{16}\.mp3', filename):
        return jsonify({'error': 'File not available'}), 404
    preview_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp', 'preview')
    if not os.path.isdir(preview_dir):
        return jsonify({'error': 'Preview folder not found'}), 404
    return send_from_directory(preview_dir, filename)


# ── Pipeline ─────────────────────────────────────────────────────────────

def run_pipeline(job_id, topic, options):
    job = jobs[job_id]
    try:
        config = load_config()
        ensure_not_cancelled(job)

        # Setup output directories
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{sanitize_name(topic)}_{timestamp}"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(base_dir, 'output', folder_name)
        temp_dir = os.path.join(base_dir, 'temp')
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        config.setdefault('paths', {})['temp'] = temp_dir
        config.setdefault('subtitles', {})['enabled'] = options['subtitles_enabled']
        config['subtitles']['font_size'] = options['subtitle_font_size']
        config['subtitles']['words_per_group'] = options['subtitle_words_per_group']
        config['subtitles']['font_color'] = options['subtitle_font_color']
        config['subtitles']['highlight_color'] = options['subtitle_highlight_color']
        config['subtitles']['stroke_color'] = options['subtitle_stroke_color']
        config['subtitles']['highlight_mode'] = options['subtitle_highlight_mode']
        config['subtitles']['position_anchor'] = options['subtitle_position_anchor']
        config.setdefault('video', {})['max_duration_seconds'] = options['duration_seconds']
        config['video']['resolution_width'] = options['resolution_width']
        config['video']['resolution_height'] = options['resolution_height']
        config['video']['fps'] = options['fps']
        config['video']['raw_bitrate'] = options['raw_bitrate']
        config['video']['final_bitrate'] = options['final_bitrate']
        config['video']['audio_bitrate'] = options['audio_bitrate']
        config['video']['encode_preset'] = options['encode_preset']

        with open(os.path.join(output_dir, 'effective_options.json'), 'w', encoding='utf-8') as f:
            json.dump(options, f, indent=2, ensure_ascii=False)

        video_topic = options['visual_query'] or topic
        if options['vibe_visual_terms']:
            video_topic = f"{video_topic} {options['vibe_visual_terms']}".strip()
        if options['video_source'] == 'local':
            config.setdefault('pexels', {})['api_key'] = ''
        ensure_not_cancelled(job)

        # ── Step 1: Script ───────────────────────────────────────────
        update_job(job_id, 1, 'Script', 'Generating script with AI provider fallback...', 5)
        script_data = generate_script_via_subprocess(topic, options)
        ensure_not_cancelled(job)
        full_script = script_data['full_script']
        mood = script_data.get('mood', 'informative')
        visual_plan = script_data.get('visual_plan', [])
        word_count = len(full_script.split())

        with open(os.path.join(output_dir, 'script.txt'), 'w', encoding='utf-8') as f:
            f.write(f"TOPIC: {topic}\nMOOD: {mood}\nHOOK: {script_data.get('hook','')}\n")
            f.write(f"BODY: {script_data.get('body','')}\nCTA: {script_data.get('cta','')}\n")
            f.write(f"VISUAL_PLAN: {json.dumps(visual_plan, ensure_ascii=False)}\n")
            f.write(f"\nFULL SCRIPT:\n{full_script}\n")

        update_job(job_id, 1, 'Script', f'{word_count} words, mood: {mood}', 15, done=True)

        # ── Step 2: SEO Metadata ─────────────────────────────────────
        update_job(job_id, 2, 'SEO Metadata', 'Generating title, tags, description...', 20)
        from seo_generator import SEOGenerator
        seo_gen = SEOGenerator(config)
        seo_data = seo_gen.generate_metadata(
            topic,
            full_script,
            vibe_label=options['vibe_label'],
            vibe_seo_style=options['vibe_seo_style'],
        )
        ensure_not_cancelled(job)

        with open(os.path.join(output_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(seo_data, f, indent=2, ensure_ascii=False)

        update_job(job_id, 2, 'SEO Metadata', seo_data.get('title', 'Done'), 30, done=True)

        # ── Step 3: Voiceover ────────────────────────────────────────
        from voice_generator import VoiceGenerator
        voice_gen = VoiceGenerator(config)
        voice_used = options['voice']
        update_job(job_id, 3, 'Voiceover', f"Generating {options['voice_label']} at {options['voice_rate']}...", 35)

        voice_path = os.path.join(output_dir, 'voiceover.mp3')
        _, word_timings = voice_gen.generate_voiceover_with_timing(
            full_script,
            voice_path,
            mood=mood,
            voice_override=voice_used,
            rate_override=options['voice_rate'],
        )
        ensure_not_cancelled(job)
        with open(os.path.join(output_dir, 'word_timings.json'), 'w', encoding='utf-8') as f:
            json.dump(word_timings or [], f, ensure_ascii=False)

        from moviepy.editor import AudioFileClip
        ac = AudioFileClip(voice_path)
        audio_duration = ac.duration
        ac.close()

        from subtitle_generator import SubtitleGenerator
        subtitle_gen = SubtitleGenerator(config)
        subtitle_data = subtitle_gen.generate_subtitle_data(
            full_script,
            audio_duration,
            word_timings=word_timings,
        )
        with open(os.path.join(output_dir, 'subtitle_data.json'), 'w', encoding='utf-8') as f:
            json.dump(subtitle_data, f, ensure_ascii=False)

        update_job(job_id, 3, 'Voiceover', f'{audio_duration:.1f}s with {voice_used}', 45, done=True)

        # ── Step 4: Video ────────────────────────────────────────────
        update_job(job_id, 4, 'Video', f'Generating {options["video_source"]} visuals for "{video_topic}"...', 50)
        from video_generator import VideoGenerator
        video_gen = VideoGenerator(config)
        raw_path = os.path.join(temp_dir, f"raw_{sanitize_name(topic)}.mp4")
        video_gen.generate_video(
            video_topic,
            raw_path,
            duration=audio_duration,
            visual_plan=visual_plan,
        )
        ensure_not_cancelled(job)

        update_job(job_id, 4, 'Video', 'Clips ready', 65, done=True)

        # ── Step 5: Merge ────────────────────────────────────────────
        update_job(job_id, 5, 'Merge', 'Merging video + audio + subtitles...', 68)
        from video_merger import VideoMerger
        merger = VideoMerger(config)
        final_path = os.path.join(output_dir, 'final.mp4')
        merger.merge(
            raw_path,
            voice_path,
            final_path,
            script_text=full_script,
            enable_subs=options['subtitles_enabled'],
            subtitle_data=subtitle_data,
            hook_text=script_data.get('hook'),
            cta_text=script_data.get('cta'),
        )
        ensure_not_cancelled(job)

        update_job(job_id, 5, 'Merge', 'Video assembled', 85, done=True)

        # ── Step 6: Thumbnail ────────────────────────────────────────
        update_job(job_id, 6, 'Thumbnail', 'Creating thumbnail...', 88)
        from thumbnail_generator import ThumbnailGenerator
        thumb_gen = ThumbnailGenerator(config)
        thumb_path = os.path.join(output_dir, 'thumbnail.png')
        thumb_gen.generate_thumbnail(thumb_path, seo_data)
        ensure_not_cancelled(job)

        update_job(job_id, 6, 'Thumbnail', 'Ready', 92, done=True)

        # ── Step 7: Google Sheets ────────────────────────────────────
        update_job(job_id, 7, 'Sheets Log', 'Logging to Google Sheets...', 95)
        from sheets_logger import SheetsLogger
        logger = SheetsLogger(config)
        logged = logger.log_video({
            'topic': topic,
            'title': seo_data.get('title', ''),
            'description': seo_data.get('description', ''),
            'tags': seo_data.get('tags', []),
            'hashtags': seo_data.get('hashtags', []),
            'category': seo_data.get('category', ''),
            'voice': voice_used,
            'voice_label': options['voice_label'],
            'voice_reason': options['voice_reason'],
            'vibe': options['vibe'],
            'vibe_label': options['vibe_label'],
            'voice_rate': options['voice_rate'],
            'requested_duration_seconds': options['duration_seconds'],
            'video_source': options['video_source'],
            'aspect_ratio': options['aspect_ratio_label'],
            'quality': options['quality_label'],
            'resolution': options['resolution_label'],
            'visual_query': video_topic,
            'subtitles_enabled': options['subtitles_enabled'],
            'duration': round(audio_duration, 1),
            'script': full_script,
            'thumbnail_text': seo_data.get('thumbnail_text', ''),
            'video_path': os.path.abspath(final_path),
            'thumbnail_path': os.path.abspath(thumb_path),
            'thumbnail_url': '',
            'upload_status': 'Pending',
        })
        sheet_msg = 'Logged to Google Sheets' if logged else 'Sheets not configured (skipped)'
        update_job(job_id, 7, 'Sheets Log', sheet_msg, 100, done=True)

        # ── Done ─────────────────────────────────────────────────────
        job['status'] = 'complete'
        job['progress'] = 100
        job['result'] = {
            'output_dir': output_dir,
            'folder': folder_name,
            'video_path': os.path.abspath(final_path),
            'thumb_path': os.path.abspath(thumb_path),
            'video_url': f'/media/{folder_name}/final.mp4',
            'thumbnail_url': f'/media/{folder_name}/thumbnail.png',
            'audio_url': f'/media/{folder_name}/voiceover.mp3',
            'title': seo_data.get('title', topic),
            'description': seo_data.get('description', ''),
            'tags': seo_data.get('tags', []),
            'hashtags': seo_data.get('hashtags', []),
            'category': seo_data.get('category', ''),
            'thumbnail_text': seo_data.get('thumbnail_text', ''),
            'duration': round(audio_duration, 1),
            'voice': voice_used,
            'voice_label': options['voice_label'],
            'voice_reason': options['voice_reason'],
            'vibe': options['vibe'],
            'vibe_label': options['vibe_label'],
            'voice_rate': options['voice_rate'],
            'requested_duration_seconds': options['duration_seconds'],
            'video_source': options['video_source'],
            'aspect_ratio_label': options['aspect_ratio_label'],
            'quality_label': options['quality_label'],
            'resolution_label': options['resolution_label'],
            'visual_query': video_topic,
            'subtitles_enabled': options['subtitles_enabled'],
            'subtitle_style_label': options['subtitle_style_label'],
            'subtitle_position_label': options['subtitle_position_label'],
            'subtitle_highlight_mode_label': options['subtitle_highlight_mode_label'],
            'mood': mood,
            'word_count': word_count,
        }

    except Exception as e:
        if str(e) == '__JOB_CANCELLED__':
            return
        import traceback
        traceback.print_exc()
        job['status'] = 'error'
        job['error'] = str(e)


# ── Entry Point ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = 5000
    print()
    print("=" * 50)
    print("  AI FACELESS STUDIO")
    print(f"  http://localhost:{port}")
    print("=" * 50)
    print()
    webbrowser.open(f'http://localhost:{port}')
    app.run(host='0.0.0.0', port=port, debug=False)
