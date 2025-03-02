import requests
import os
import shutil
import datetime
import re

ARTIFACTORY_URL = "https://artifactory.com"
REPO_KEY = "gcds"
FOLDER_PATH = "sss7/date"
API_KEY = "your_api_key_here" 
BASE_DOWNLOAD_DIR = "C:/download"  # Directorio base de descargas
TIME_WINDOW_MINUTES = 5  # Rango de 5 minutos para considerar las últimas ejecuciones

headers = {
    "X-JFrog-Art-Api": API_KEY
}
def list_files_in_folder(url, headers):
    response = requests.get(url, headers=headers, verify=False)  # Disable SSL verification
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to list files: {response.status_code} - {response.text}")
        return None

def parse_folder_datetime(folder_name):
    match = re.match(r"(\d{2}-\d{2}-\d{4} \d{2}-\d{2}-\d{2}\.\d+)", folder_name)
    if match:
        return datetime.datetime.strptime(match.group(1), "%m-%d-%Y %H-%M-%S.%f")
    return None

def get_latest_execution_folders(folder_list):
    timestamps = []
    folder_map = {}
    
    print("Detected folders:")
    for folder in folder_list:
        folder_name = folder['uri'].strip('/')
        dt = parse_folder_datetime(folder_name)
        if dt:
            print(f" - {folder_name} -> {dt}")
            timestamps.append(dt)
            folder_map[dt] = folder_name
    
    if not timestamps:
        print("No valid folders found!")
        return []
    
    timestamps.sort(reverse=True)
    
    # Identify the latest execution group (last three contiguous timestamps)
    latest_group = [folder_map[timestamps[0]]]
    for i in range(1, len(timestamps)):
        if (timestamps[i-1] - timestamps[i]).total_seconds() <= 60:  # Within 1 min gap
            latest_group.append(folder_map[timestamps[i]])
        if len(latest_group) == 3:
            break
    
    print(f"Selected latest execution group: {latest_group}")
    return latest_group

def download_folder(base_url, folder_path, local_dir, headers):
    folder_url = f"{base_url}/artifactory/api/storage/{REPO_KEY}/{folder_path}"
    folder_content = list_files_in_folder(folder_url, headers)
    
    if folder_content and 'children' in folder_content:
        latest_folders = get_latest_execution_folders(folder_content['children'])
        
        for item in folder_content['children']:
            item_name = item['uri'].strip('/')
            if item['folder'] and item_name in latest_folders:
                new_local_dir = os.path.join(local_dir, item_name)
                os.makedirs(new_local_dir, exist_ok=True)  # Create nested folders
                download_folder(base_url, f"{folder_path}/{item_name}", new_local_dir, headers)
            elif not item['folder']:
                file_url = f"{base_url}/artifactory/{REPO_KEY}/{folder_path}/{item_name}"
                local_file_path = os.path.join(local_dir, item_name)
                download_file(file_url, local_file_path, headers)

def download_file(file_url, local_path, headers):
    response = requests.get(file_url, headers=headers, verify=False)  # Disable SSL verification
    if response.status_code == 200:
        with open(local_path, 'wb') as f:
            f.write(response.content)
        print(f"Downloaded: {local_path}")
    else:
        print(f"Failed to download: {file_url} - {response.status_code}")

def delete_directory(directory):
    if os.path.exists(directory):
        print(f"Folder to be deleted: {directory}")
        input("Press Enter to continue with deletion...")
        shutil.rmtree(directory)
        print(f"Deleted: {directory}")
    else:
        print(f"Directory does not exist: {directory}")

def main():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    DOWNLOAD_DIR = os.path.join(BASE_DOWNLOAD_DIR, timestamp)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)  # Asegurar que el directorio existe
    
    try:
        # Descargar solo las carpetas de la última ejecución dentro del rango de tiempo
        download_folder(ARTIFACTORY_URL, FOLDER_PATH, DOWNLOAD_DIR, headers)
        print("Download completed successfully!")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        delete_directory(DOWNLOAD_DIR)
        print("Cleanup completed.")

if __name__ == "__main__":
    main()
