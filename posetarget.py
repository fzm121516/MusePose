import argparse
import os
import glob
import random
import subprocess
import yaml
import multiprocessing
from functools import partial
import json

# --------------- Arguments ---------------
parser = argparse.ArgumentParser(description='Test Images')
parser.add_argument('--videos-dir', type=str, required=True)
parser.add_argument('--original-videos-png-dir', type=str, required=True)
parser.add_argument('--target-videos-dir', type=str, required=True)
parser.add_argument('--result-dir', type=str, required=True)
parser.add_argument('--random-seed', type=int, default=42, help='Random seed for reproducibility')
parser.add_argument('--gpu', type=int, default=0, help='GPU device id to use')
parser.add_argument('--num-processes', type=int, default=16, help='Number of parallel processes to use')
parser.add_argument('--video-map-file', type=str, required=True, help='JSON file mapping video names to mp4 files')
parser.add_argument('--gait-id-range', type=int, nargs=2, default=[75, 86],
                    help='Range of gait IDs to include (inclusive)')
args = parser.parse_args()

# Set the random seed
random.seed(args.random_seed)

# Load Video List
video_list = sorted(glob.glob(os.path.join(args.videos_dir, '**', '*.avi'), recursive=True))

num_video = len(video_list)
print("Found ", num_video, " videos")

# Load video map from JSON file
with open(args.video_map_file, 'r') as f:
    video_map = json.load(f)


# Function to run pose_align.py with specified arguments
def run_pose_align(imgfn_refer, vidfn, outfn_align_pose_video, gpu_id):
    command = [
        'python', 'mypose.py',
        '--imgfn_refer', imgfn_refer,
        '--vidfn', vidfn,
        '--outfn_align_pose_video', outfn_align_pose_video,
        '--gpu', str(gpu_id)
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running pose_align.py: {result.stderr}")
    else:
        print(f"Successfully ran pose_align.py: {result.stdout}")


# Dictionary to store the test cases for the YAML file
manager = multiprocessing.Manager()
test_cases = manager.dict()

# Allowed gait types
allowed_gait_types = ['nm-05', 'nm-06', 'bg-01', 'bg-02', 'cl-01', 'cl-02']


# Process each video
def process_video(video_path, test_cases, args):
    video_name_with_ext = os.path.basename(video_path)
    video_name = os.path.splitext(video_name_with_ext)[0]
    print(f"Processing video: {video_name}")

    # Parse the filename to create directory structure
    parts = video_name.split('-')
    if len(parts) == 4:
        gait_id = parts[0]
        gait_type = f"{parts[1]}-{parts[2]}"
        gait_view = parts[3]
    else:
        print(f"Unexpected filename format: {video_name}")
        return

    # Check if gait_type is in allowed_gait_types
    if gait_type not in allowed_gait_types:
        print(f"Gait type {gait_type} not in allowed list, skipping.")
        return

    # Check if gait_id is within the specified range
    try:
        gait_id_num = int(gait_id)
        if gait_id_num < args.gait_id_range[0] or gait_id_num > args.gait_id_range[1]:
            print(
                f"Gait ID {gait_id} not in the allowed range ({args.gait_id_range[0]}-{args.gait_id_range[1]}), skipping.")
            return
    except ValueError:
        print(f"Invalid Gait ID {gait_id}, skipping.")
        return

    original_videos_png_dir = os.path.join(
        args.original_videos_png_dir,
        os.path.relpath(video_path, args.videos_dir).rsplit(os.sep, 1)[0]
    )
    imgfn_refer = os.path.join(original_videos_png_dir, video_name + '.png')

    target_videos_dir = os.path.join(args.target_videos_dir, gait_view)

    # Use the video map to find the corresponding mp4 file
    if video_name in video_map:
        mapped_video_name = video_map[video_name]['max_distance']
        vidfn = os.path.join(target_videos_dir, mapped_video_name + '.mp4')
        if not os.path.exists(vidfn):
            print(f"Mapped .mp4 file does not exist: {vidfn}, skipping.")
            return
        print(f"Selected .mp4 file: {vidfn}")
    else:
        print(f"No mapping found for video: {video_name}, skipping.")
        return

    result_dir = os.path.join(args.result_dir, os.path.relpath(video_path, args.videos_dir).rsplit(os.sep, 1)[0])
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    outfn_align_pose_video = os.path.join(result_dir, video_name + '.mp4')

    # Run the pose_align.py script with the specified arguments
    run_pose_align(imgfn_refer, vidfn, outfn_align_pose_video, args.gpu)

    # Add to test cases dictionary
    if imgfn_refer not in test_cases:
        test_cases[imgfn_refer] = []
    test_cases[imgfn_refer].append(outfn_align_pose_video)

    print(f"Added {outfn_align_pose_video} to test_cases[{imgfn_refer}]")


# Create a pool of workers and process videos in parallel
pool = multiprocessing.Pool(processes=args.num_processes)
partial_process_video = partial(process_video, test_cases=test_cases, args=args)
pool.map(partial_process_video, video_list)

# Wait for all processes to finish
pool.close()
pool.join()
