from flask import Flask, render_template, request, send_file, jsonify, session
import os
import shutil
import zipfile
import uuid
import time
from flask_socketio import SocketIO, emit, join_room
from concurrent.futures import ThreadPoolExecutor
import threading
from bs4 import BeautifulSoup
import re
import requests
from urllib.parse import urljoin, urlparse
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import subprocess
import logging


app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
socketio = SocketIO(app)



logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@socketio.on('start_copying')
def start_copying(message):
    website_url = message.get('websiteUrl')
    if website_url:
        logging.info(f"Starting copying process for website: {website_url}")
    else:
        logging.error("Invalid start_copying message received: Missing websiteUrl")


def get_absolute_url(base_url, url):
    return urljoin(base_url, url)


def extract_filename_from_content_disposition(content_disposition):
    filename_match = re.search(r'filename=["\']?([^"\';]*)["\']?', content_disposition)
    if filename_match:
        return filename_match.group(1)
    return None


def download_file_wget(url, folder_name, total_links, progress_callback):
    completed_links = 0

    try:
        process = subprocess.Popen(['req/wget.exe', '-r', '-np', '-P', folder_name, '--show-progress', url], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        total_bytes = None
        downloaded_bytes = 0

        while True:
            output = process.stderr.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                match = re.search(r'\((\d+)%\)', output)
                if match:
                    progress = int(match.group(1))
                    progress_callback(progress)

                completed_links += 1
                progress = int((completed_links / total_links) * 100)
                progress_callback(progress)

        rc = process.poll()
        return rc == 0, None
    except Exception as e:
        return False, str(e)


def download_file_requests(url, folder_name, headers=None):
    retry_count = 3
    for _ in range(retry_count):
        try:
            res = requests.get(url, stream=True, timeout=10, headers=headers)
            if res.status_code == 200:
                parsed_url = urlparse(url)
                if 'Content-Disposition' in res.headers:
                    file_name = extract_filename_from_content_disposition(res.headers['Content-Disposition'])
                elif parsed_url.path:
                    file_name = os.path.basename(parsed_url.path)
                else:
                    file_name = 'file_' + str(uuid.uuid4())

                file_path = os.path.join(folder_name, file_name)
                if not os.path.exists(os.path.dirname(file_path)):
                    os.makedirs(os.path.dirname(file_path))

                with open(file_path, 'wb') as f:
                    shutil.copyfileobj(res.raw, f)
                return True, file_name
            else:
                return False, f'HTTP error: {res.status_code}'
        except requests.RequestException as e:
            if _ < retry_count - 1:
                time.sleep(5)
    return False, f'Failed after {retry_count} retries'


def fetch_website_content(website_url, headers=None):
    try:
        response = requests.get(website_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        return None


def copy_website_content(soup, website_url, folder_name, depth, max_depth, headers, executor, progress_callback):
    if depth > max_depth:
        return

    links = [link['href'] for link in soup.find_all('a', href=True)]
    total_links = len(links)
    completed_links = 0

    for link in links:
        href = get_absolute_url(website_url, link)
        if href.startswith('http'):
            success, _ = download_file_requests(href, folder_name, headers)
            if success:
                completed_links += 1
                progress = int((completed_links / total_links) * 100)
                progress_callback(progress)


def handle_dynamic_content(url):
    options = FirefoxOptions()
    options.headless = True
    service = FirefoxService(executable_path=os.path.join(os.path.dirname(__file__), 'req', 'geckodriver.exe'))
    driver = webdriver.Firefox(service=service, options=options)
    driver.get(url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    page_source = driver.page_source
    driver.quit()
    return page_source


@app.route('/')
def index():
    session_id = str(uuid.uuid4())
    session['session_id'] = session_id
    return render_template('index.html', session_id=session_id)


@app.route('/copy-website-requests', methods=['POST'])
def copy_website_requests():
    website_url = request.form.get('websiteUrl')
    if not website_url:
        return jsonify({'error': 'URL is required'}), 400

    if 'session_id' not in session:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    else:
        session_id = session['session_id']

    folder_name = os.path.join(app.root_path, 'copied_website', session_id)

    try:
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        elif not os.path.isdir(folder_name):
            return jsonify({'error': 'Folder name already exists as a file'}), 500

        try:
            website_content = handle_dynamic_content(website_url)
        except Exception as e:
            website_content = fetch_website_content(website_url)

        if website_content:
            soup = BeautifulSoup(website_content, 'html.parser')

            def progress_callback(progress):
                socketio.emit('progress_update', {'progress': progress}, room=session['session_id'])

            with ThreadPoolExecutor(max_workers=10) as executor:
                copy_website_content(soup, website_url, folder_name, 1, max_depth=3, headers={}, executor=executor, progress_callback=progress_callback)

            zip_file_path = os.path.join(folder_name, 'copied_website.zip')
            with zipfile.ZipFile(zip_file_path, 'w') as zipf:
                for root, dirs, files in os.walk(folder_name):
                    for file in files:
                        zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), folder_name))

            def delete_folder():
                time.sleep(10800)
                shutil.rmtree(folder_name)
                logging.info(f"Folder '{folder_name}' deleted after timeout.")

            threading.Thread(target=delete_folder).start()

            return render_template('download.html', zip_file_path=zip_file_path)
        else:
            return jsonify({'error': 'Failed to fetch website content'}), 500

    except Exception as e:
        logging.error(f"Failed to copy website: {str(e)}")
        return jsonify({'error': f'Failed to copy website: {str(e)}'}), 500


@app.route('/copy-website-wget', methods=['POST'])
def copy_website_wget():
    website_url = request.form.get('websiteUrl')
    if not website_url:
        return jsonify({'error': 'URL is required'}), 400

    if 'session_id' not in session:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    else:
        session_id = session['session_id']

    folder_name = os.path.join(app.root_path, 'copied_website', session_id)

    try:
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        elif not os.path.isdir(folder_name):
            return jsonify({'error': 'Folder name already exists as a file'}), 500

        try:
            website_content = handle_dynamic_content(website_url)
        except Exception as e:
            website_content = fetch_website_content(website_url)

        if website_content:
            soup = BeautifulSoup(website_content, 'html.parser')
            links = [link['href'] for link in soup.find_all('a', href=True)]
            total_links = len(links)

            def progress_callback(progress):
                socketio.emit('progress_update', {'progress': progress}, room=session['session_id'])

            success, stderr = download_file_wget(website_url, folder_name, total_links, progress_callback)
            if success:
                zip_file_path = os.path.join(folder_name, 'copied_website.zip')
                with zipfile.ZipFile(zip_file_path, 'w') as zipf:
                    for root, dirs, files in os.walk(folder_name):
                        for file in files:
                            zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), folder_name))

                def delete_folder():
                    time.sleep(10800)
                    shutil.rmtree(folder_name)
                    logging.info(f"Folder '{folder_name}' deleted after timeout.")

                threading.Thread(target=delete_folder).start()

                return render_template('download.html', zip_file_path=zip_file_path)
            else:
                logging.error(f'Failed to copy website using wget: {stderr}')
                return jsonify({'error': f'Failed to copy website using wget: {stderr}'}), 500
        else:
            return jsonify({'error': 'Failed to fetch website content'}), 500

    except Exception as e:
        logging.error(f'Failed to copy website using wget: {str(e)}')
        return jsonify({'error': f'Failed to copy website using wget: {str(e)}'}), 500


@app.route('/download/<path:filename>')
def download(filename):
    return send_file(filename, as_attachment=True)


@socketio.on('connect')
def handle_connect():
    session_id = session.get('session_id')
    if session_id:
        join_room(session_id)


if __name__ == '__main__':
    socketio.run(app, debug=False)
