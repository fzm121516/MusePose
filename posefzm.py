import argparse
import os
import glob
import random  # For random selection
import subprocess  # For running another Python script
import yaml  # For creating the YAML file


# --------------- Arguments ---------------
parser = argparse.ArgumentParser(description='Test Images')
parser.add_argument('--videos-dir', type=str, required=True)
parser.add_argument('--original-videos-png-dir', type=str, required=True)
parser.add_argument('--target-videos-dir', type=str, required=True)
parser.add_argument('--result-dir', type=str, required=True)
parser.add_argument('--yaml-file', type=str, default='./myconfig/test1.yaml', help='Output YAML file path')
parser.add_argument('--random-seed', type=int, default=42, help='Random seed for reproducibility')
args = parser.parse_args()

# Set the random seed
random.seed(args.random_seed)

# Load Video List
video_list = sorted([*glob.glob(os.path.join(args.videos_dir, '**', '*.avi'), recursive=True)])

num_video = len(video_list)
print("Found ", num_video, " videos")


# Function to run pose_align.py with specified arguments
def run_pose_align(imgfn_refer, vidfn, outfn_align_pose_video):
    command = [
        'python', 'pose_align.py',
        '--imgfn_refer', imgfn_refer,
        '--vidfn', vidfn,
        '--outfn_align_pose_video', outfn_align_pose_video
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running pose_align.py: {result.stderr}")
    else:
        print(f"Successfully ran pose_align.py: {result.stdout}")


# Dictionary to store the test cases for the YAML file
test_cases = {}

# Process each video
for i in range(num_video):
    video_path = video_list[i]
    video_name_with_ext = os.path.basename(video_path)
    video_name = os.path.splitext(video_name_with_ext)[0]
    print(i, '/', num_video, video_name)

    # Parse the filename to create directory structure
    parts = video_name.split('-')  # Split filename by '-'
    print(f"Filename parts: {parts}")  # Print the parts of the filename
    if len(parts) == 4:  # If the number of parts is 4, the filename format is correct
        gait_type = os.path.join(f"{parts[1]}-{parts[2]}")
        gait_view = os.path.join(parts[3])  # Combine the second and third parts
    else:  # If the filename format is not as expected, skip this file
        print(f"Unexpected filename format: {video_name}")
        continue

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
        continue
    # Randomly select one .mp4 file
    selected_mp4 = random.choice(mp4_files)
    print(f"Selected .mp4 file: {selected_mp4}")
    vidfn = os.path.join(target_videos_dir, selected_mp4)
    # You can add further processing for the selected_mp4 file here

    result_dir = os.path.join(
        args.result_dir,
        os.path.relpath(video_path, args.videos_dir).rsplit(os.sep, 1)[0]
    )
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    outfn_align_pose_video = os.path.join(result_dir, video_name + '.mp4')

    # Run the pose_align.py script with the specified arguments
    run_pose_align(imgfn_refer, vidfn, outfn_align_pose_video)

    # Add to test cases dictionary
    if imgfn_refer not in test_cases:
        test_cases[imgfn_refer] = []
    test_cases[imgfn_refer].append(outfn_align_pose_video)

# Write test cases to YAML file
with open(args.yaml_file, 'w') as yaml_file:
    yaml.dump({'test_cases': test_cases}, yaml_file, default_flow_style=False)

print(f"YAML file created at {args.yaml_file}")
