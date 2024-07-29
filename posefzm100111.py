import argparse
import os
import glob
import random  # For random selection
import subprocess  # For running another Python script
import yaml  # For creating the YAML file
import multiprocessing  # For parallel processing
from functools import partial

# --------------- Arguments ---------------
parser = argparse.ArgumentParser(description='Test Images')
parser.add_argument('--videos-dir', type=str, required=True)
parser.add_argument('--original-videos-png-dir', type=str, required=True)
parser.add_argument('--target-videos-dir', type=str, required=True)
parser.add_argument('--result-dir', type=str, required=True)
parser.add_argument('--yaml-file', type=str, default='./myconfig/test.yaml', help='Output YAML file path')
parser.add_argument('--random-seed', type=int, default=42, help='Random seed for reproducibility')
parser.add_argument('--gpu', type=int, default=2, help='GPU device id to use')
parser.add_argument('--num-processes', type=int, default=8, help='Number of parallel processes to use')
args = parser.parse_args()

# Set the random seed
random.seed(args.random_seed)

# Load Video List
video_list = sorted([*glob.glob(os.path.join(args.videos_dir, '**', '*.avi'), recursive=True)])

num_video = len(video_list)
print("Found ", num_video, " videos")


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
    parts = video_name.split('-')  # Split filename by '-'
    if len(parts) == 4:  # If the number of parts is 4, the filename format is correct
        gait_id = parts[0]
        gait_type = f"{parts[1]}-{parts[2]}"
        gait_view = parts[3]  # Combine the second and third parts
    else:  # If the filename format is not as expected, skip this file
        print(f"Unexpected filename format: {video_name}")
        return

    # Check if gait_type is in allowed_gait_types
    if gait_type not in allowed_gait_types:
        print(f"Gait type {gait_type} not in allowed list, skipping.")
        return

    # Check if gait_id is within the range 075 to 124
    try:
        gait_id_num = int(gait_id)
        if gait_id_num < 100 or gait_id_num > 111:
            print(f"Gait ID {gait_id} not in the allowed range (100-111), skipping.")
            return
    except ValueError:
        print(f"Invalid Gait ID {gait_id}, skipping.")
        return

    original_videos_png_dir = os.path.join(
        args.original_videos_png_dir,
        os.path.relpath(video_path, args.videos_dir).rsplit(os.sep, 1)[0]
    )
    # Append video_name and .png to original_videos_dir
    imgfn_refer = os.path.join(original_videos_png_dir, video_name + '.png')

    target_videos_dir = os.path.join(
        args.target_videos_dir,
        gait_view
    )
    # Find all .mp4 files in target_videos_dir
    mp4_files = glob.glob(os.path.join(target_videos_dir, '**', '*.mp4'), recursive=True)
    if not mp4_files:
        print(f"No .mp4 files found in {target_videos_dir}")
        return
    # Randomly select one .mp4 file
    selected_mp4 = random.choice(mp4_files)
    print(f"Selected .mp4 file: {selected_mp4}")
    vidfn = os.path.join(target_videos_dir, selected_mp4)

    result_dir = os.path.join(
        args.result_dir,
        os.path.relpath(video_path, args.videos_dir).rsplit(os.sep, 1)[0]
    )
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    outfn_align_pose_video = os.path.join(result_dir, video_name + '.mp4')

    # Run the pose_align.py script with the specified arguments
    run_pose_align(imgfn_refer, vidfn, outfn_align_pose_video, args.gpu)

    # Add to test cases dictionary
    if imgfn_refer not in test_cases:
        test_cases[imgfn_refer] = []
    test_cases[imgfn_refer].append(outfn_align_pose_video)


# Ensure the directory for the YAML file exists
yaml_dir = os.path.dirname(args.yaml_file)
if not os.path.exists(yaml_dir):
    os.makedirs(yaml_dir)

# Create a pool of workers and process videos in parallel
pool = multiprocessing.Pool(processes=args.num_processes)
partial_process_video = partial(process_video, test_cases=test_cases, args=args)
pool.map(partial_process_video, video_list)

# Write test cases to YAML file
with open(args.yaml_file, 'w') as yaml_file:
    yaml.dump({'test_cases': dict(test_cases)}, yaml_file, default_flow_style=False)

print(f"YAML file created at {args.yaml_file}")
