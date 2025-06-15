'''
This script deletes projects within a specified ID range using the Label Studio API.

Usage:
    python scripts/delete_projects.py --start_id <START_ID> --end_id <END_ID> --token <YOUR_TOKEN>

Example:
    python scripts/delete_projects.py --start_id 10 --end_id 20 --token your_api_token_here
'''

import argparse
import subprocess
import sys

def delete_project(project_id, token, base_url='http://127.0.0.1:8080'):
    """Deletes a single project by its ID."""
    url = f'{base_url}/api/projects/{project_id}'
    command = [
        'curl',
        '-H',
        f'Authorization: Token {token}',
        '-X',
        'DELETE',
        '-I',
        url
    ]
    print(f'Deleting project {project_id}...')
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print(f'Successfully sent delete request for project {project_id}.\nResponse:\n{result.stdout}{result.stderr}')
    except subprocess.CalledProcessError as e:
        print(f'Error deleting project {project_id}: {e}\nStdout: {e.stdout}\nStderr: {e.stderr}')
    except FileNotFoundError:
        print("Error: 'curl' command not found. Please ensure curl is installed and in your PATH.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Delete projects within a specified ID range.')
    parser.add_argument('--start_id', type=int, required=True, help='The starting project ID to delete (inclusive).')
    parser.add_argument('--end_id', type=int, required=True, help='The ending project ID to delete (inclusive).')
    parser.add_argument('--token', type=str, required=True, help='Your Label Studio API token.')
    parser.add_argument('--base_url', type=str, default='http://127.0.0.1:8080', help='Base URL of your Label Studio instance.')

    args = parser.parse_args()

    if args.start_id > args.end_id:
        print("Error: --start_id cannot be greater than --end_id.")
        sys.exit(1)

    print(f'Attempting to delete projects from ID {args.start_id} to {args.end_id}...')
    for project_id in range(args.start_id, args.end_id + 1):
        delete_project(project_id, args.token, args.base_url)
    print("Deletion process completed.")

if __name__ == '__main__':
    main() 