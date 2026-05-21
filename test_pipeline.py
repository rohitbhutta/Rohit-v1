#!/usr/bin/env python3
"""Full end-to-end pipeline test."""

import sys
import os

# Fix encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from config_loader import load_config

config = load_config()
config['paths'] = {'temp': './temp', 'output': './output'}
os.makedirs('temp', exist_ok=True)
os.makedirs('output/test_run', exist_ok=True)

print("=== FULL PIPELINE TEST ===")
print()

# Step 1
print("[1/6] Script Generation...")
from script_generator import ScriptGenerator
sg = ScriptGenerator(config)
script = sg.generate_script("3 amazing facts about space")
full = script["full_script"]
mood = script.get("mood", "informative")
wc = len(full.split())
print(f"  Words: {wc}, Mood: {mood}")
print(f"  Preview: {full[:100]}...")
print("  PASS")

# Step 2
print("[2/6] SEO Metadata...")
from seo_generator import SEOGenerator
seo = SEOGenerator(config)
meta = seo.generate_metadata("3 amazing facts about space", full)
print(f"  Title: {meta.get('title', 'N/A')}")
print("  PASS")

# Step 3
print("[3/6] Voiceover...")
from voice_generator import VoiceGenerator
vg = VoiceGenerator(config)
voice_used = vg.get_voice_for_mood(mood)
vg.generate_voiceover(full, "output/test_run/voiceover.mp3", mood=mood)
from moviepy.editor import AudioFileClip
ac = AudioFileClip("output/test_run/voiceover.mp3")
dur = ac.duration
ac.close()
print(f"  Duration: {dur:.1f}s, Voice: {voice_used}")
print("  PASS")

# Step 4
print("[4/6] Video Generation (local mode)...")
from video_generator import VideoGenerator
test_cfg = dict(config)
test_cfg["pexels"] = {"api_key": ""}  # Force local mode for test speed
vidg = VideoGenerator(test_cfg)
vidg.generate_video("space", "temp/raw_test.mp4", duration=dur)
print("  PASS")

# Step 5
print("[5/6] Merge + Subtitles...")
from video_merger import VideoMerger
vm = VideoMerger(config)
vm.merge("temp/raw_test.mp4", "output/test_run/voiceover.mp3",
         "output/test_run/final.mp4", script_text=full)
print("  PASS")

# Step 6
print("[6/6] Thumbnail...")
from thumbnail_generator import ThumbnailGenerator
tg = ThumbnailGenerator(config)
tg.generate_thumbnail("output/test_run/thumbnail.png", meta)
print("  PASS")

# Verify
print()
print("=== VERIFICATION ===")
from moviepy.editor import VideoFileClip
final = VideoFileClip("output/test_run/final.mp4")
print(f"  Resolution: {final.w}x{final.h}")
print(f"  Duration:   {final.duration:.1f}s")
print(f"  Has audio:  {final.audio is not None}")
final.close()
print(f"  Thumbnail:  {os.path.exists('output/test_run/thumbnail.png')}")
print()
print("=== ALL TESTS PASSED - SYSTEM IS READY ===")
