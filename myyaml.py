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
parser.add_argument('--yaml-file', type=str, default='./myconfig/test.yaml', help='Output YAML file path')
parser.add_argument('--random-seed', type=int, default=42, help='Random seed for reproducibility')
parser.add_argument('--gpu', type=int, default=0, help='GPU device id to use')
parser.add_argument('--min-gait-id', type=int, default=75, help='Minimum Gait ID')
parser.add_argument('--max-gait-id', type=int, default=124, help='Maximum Gait ID')
args = parser.parse_args()

# Set the random seed
random.seed(args.random_seed)

# Load Video List
video_list = sorted([*glob.glob(os.path.join(args.videos_dir, '**', '*.avi'), recursive=True)])

num_video = len(video_list)
print("Found ", num_video, " videos")

# Dictionary to store the test cases for the YAML file
test_cases = {}

# Allowed gait types
allowed_gait_types = ['nm-05', 'nm-06', 'bg-01', 'bg-02', 'cl-01', 'cl-02']

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
        gait_id = parts[0]
        gait_type = f"{parts[1]}-{parts[2]}"
        gait_view = parts[3]  # Combine the second and third parts
    else:  # If the filename format is not as expected, skip this file
        print(f"Unexpected filename format: {video_name}")
        continue

    # Check if gait_type is in allowed_gait_types
    if gait_type not in allowed_gait_types:
        print(f"Gait type {gait_type} not in allowed list, skipping.")
        continue

    # Check if gait_id is within the specified range
    try:
        gait_id_num = int(gait_id)
        if gait_id_num < args.min_gait_id or gait_id_num > args.max_gait_id:
            print(f"Gait ID {gait_id} not in the allowed range ({args.min_gait_id}-{args.max_gait_id}), skipping.")
            continue
    except ValueError:
        print(f"Invalid Gait ID {gait_id}, skipping.")
        continue

    original_videos_png_dir = os.path.join(
        args.original_videos_png_dir,
        os.path.relpath(video_path, args.videos_dir).rsplit(os.sep, 1)[0]
    )
    # Append video_name and .png to original_videos_dir
    imgfn_refer = os.path.join(original_videos_png_dir, video_name + '.png')

    result_dir = os.path.join(
        args.result_dir,
        os.path.relpath(video_path, args.videos_dir).rsplit(os.sep, 1)[0]
    )
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    outfn_align_pose_video = os.path.join(result_dir, video_name + '.mp4')

    # Check if outfn_align_pose_video already exists
    if os.path.exists(outfn_align_pose_video):
        print(f"{outfn_align_pose_video} exists")
        # Add to test cases dictionary
        if imgfn_refer not in test_cases:
            test_cases[imgfn_refer] = []
        test_cases[imgfn_refer].append(outfn_align_pose_video)

        # Ensure the directory for the YAML file exists
        yaml_dir = os.path.dirname(args.yaml_file)
        if not os.path.exists(yaml_dir):
            os.makedirs(yaml_dir)

        # Write current test case to YAML file
        with open(args.yaml_file, 'w') as yaml_file:
            yaml.dump({'test_cases': test_cases}, yaml_file, default_flow_style=False)

print(f"YAML file created at {args.yaml_file}")
