# app.py
import os
import threading
import time
from datetime import datetime
import importlib.util # Để tải module động an toàn hơn

from flask import Flask, render_template, jsonify, request, g
from flask_socketio import SocketIO

# --- Cấu hình ứng dụng ---
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'this-is-a-very-secret-key-for-dev'
    TASK_FOLDER = 'tasks' # Tên thư mục chứa các file task test

# --- Khởi tạo Flask App và SocketIO ---
# Flask sẽ tự động tìm thư mục 'static' và 'templates' trong cùng cấp với file app.py
app = Flask(__name__)
app.config.from_object(Config) # Áp dụng cấu hình

# Khởi tạo SocketIO và liên kết với ứng dụng Flask.
# async_mode='eventlet' là cần thiết để SocketIO hoạt động hiệu quả với nhiều kết nối đồng thời.
socketio = SocketIO(app, async_mode='eventlet')

# --- Biến toàn cục để quản lý trạng thái của các task và logs ---
# task_results: Một dictionary lưu trữ trạng thái hiện tại của mỗi task
#   Ví dụ: {'Example Gpio': {'status': 'Pending', 'message': '...'}}
task_results = {}
# task_logs: Một danh sách lưu trữ tất cả các dòng log để hiển thị trên console frontend
task_logs = []
# Biến cờ để kiểm soát xem chế độ Auto Test có đang chạy hay không
auto_test_running = False

# --- Các hàm hỗ trợ để tải và chạy Task ---
def load_tasks():
    print("[DEBUG] Start loading tasks from folder.")
    tasks = []
    # Lấy đường dẫn tuyệt đối đến thư mục chứa các task
    # os.path.dirname(__file__) là đường dẫn của file app.py
    # os.path.join sẽ nối với tên thư mục 'tasks'
    task_dir = os.path.join(os.path.dirname(__file__), app.config['TASK_FOLDER'])

    if not os.path.exists(task_dir):
        print(f"Error: Task folder '{task_dir}' not found. Please create it.")
        return []

    # Lặp qua tất cả các file trong thư mục tasks
    for filename in os.listdir(task_dir):
        # Chỉ xử lý các file có tên bắt đầu bằng 'task_' và kết thúc bằng '.py'
        # và không phải là chính file __init__.py (nếu có)
        if filename.startswith('task_') and filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3] # Cắt bỏ phần mở rộng .py để lấy tên module
            print(f"[DEBUG] loading module: {module_name}")
            try:
                # Tạo một spec (đặc tả) để tải module từ đường dẫn file
                spec = importlib.util.spec_from_file_location(module_name, os.path.join(task_dir, filename))
                module = importlib.util.module_from_spec(spec)
                # Tải và thực thi module
                spec.loader.exec_module(module)

                # Mỗi file task phải có một hàm tên là 'test_task'
                if hasattr(module, 'test_task'):
                    #print(f"[DEBUG] Đã tìm thấy hàm test_task trong {filename}")
                    tasks.append({
                        'id': module_name, # ID duy nhất cho task (ví dụ: task_example_gpio)
                        # Tên hiển thị trên giao diện (ví dụ: "Example Gpio")
                        'name': module_name.replace('task_', '').replace('_', ' ').title(),
                        # Mô tả từ module, hoặc mặc định
                        'description': getattr(module, 'DESCRIPTION', 'No description provided.'),
                        'function': module.test_task # Tham chiếu đến hàm test_task
                    })
                else:
                    print(f"[WARNING] Task file '{filename}' there is no function 'test_task'.")
            except Exception as e:
                print(f"[ERROR] Error when loading task {filename}: {e}")
    print(f"[DEBUG] Finished load {len(tasks)} task.")
    # Sắp xếp các task theo tên để hiển thị nhất quán trên giao diện
    return sorted(tasks, key=lambda x: x['name'])

def execute_single_task(task):
    global task_results, task_logs
    task_name = task['name']
    task_id = task['id']

    # Cập nhật trạng thái ban đầu
    task_results[task_name] = {'status': 'Running', 'message': 'Running test...', 'details': []}
    log_message = f"[{datetime.now().strftime('%H:%M:%S')}] Starting run: {task_name}"
    #print('DEBUG]Emit task_status_update:', {task_name: task_results[task_name]})
    socketio.emit('task_status_update', {task_name: task_results[task_name]}, namespace='/')
    task_logs.append(log_message)

    try:
        # Hàm test_task trả về (overall_status, overall_message, detail_results)
        overall_status, overall_message, detail_results = task['function']()

        # Cập nhật kết quả
        task_results[task_name]['status'] = overall_status
        task_results[task_name]['message'] = overall_message
        task_results[task_name]['details'] = detail_results

    except Exception as e:
        task_results[task_name]['status'] = 'Failed'
        task_results[task_name]['message'] = f"An error occurred: {str(e)}"
        task_results[task_name]['details'] = []

    log_message = f"[{datetime.now().strftime('%H:%M:%S')}] Task: {task_name} finished with status: {task_results[task_name]['status']} - {task_results[task_name]['message']}"
    task_logs.append(log_message)
    #print('DEBUG]Emit task_status_update:', {task_name: task_results[task_name]})
    socketio.emit('task_status_update', {task_name: task_results[task_name]}, namespace='/')
    socketio.emit('console_log_update', {'log': log_message}, namespace='/')
    print(f"[DEBUG] Task {task_name} executed with status: {task_results[task_name]['status']}")
  
def execute_all_tasks():
    print("[DEBUG] Bắt đầu Auto Test cho tất cả các task.")
    """
    Thực thi tất cả các task theo chế độ tự động.
    Quản lý biến cờ auto_test_running và gửi thông báo qua SocketIO.
    """
    global auto_test_running, task_results, task_logs
    tasks = app.config['LOADED_TASKS'] # Lấy danh sách task từ cấu hình ứng dụng
    task_logs.clear()  # Xóa log cũ
    log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] [INFO] --- Auto Test Started ---"
    task_logs.append(log_entry)
    socketio.emit('console_log_update', {'log': log_entry}, namespace='/')

    # Reset tất cả các task về trạng thái "Pending" khi bắt đầu auto test
    for task in tasks:
        task_results[task['name']] = {'status': 'Pending', 'message': ''}
    # Gửi cập nhật trạng thái toàn bộ bảng tới client để reset giao diện
    socketio.emit('full_task_status_update', task_results, namespace='/')

    # Chạy từng task một
    for task in tasks:
        print(f"[DEBUG] Running (auto): {task['name']} ")
        execute_single_task(task)
        # time.sleep(0.5) # Giả lập một chút độ trễ giữa các task

    log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] [INFO] --- Auto Test Finished ---"
    task_logs.append(log_entry)
    socketio.emit('console_log_update', {'log': log_entry}, namespace='/')

    auto_test_running = False # Đặt lại cờ khi hoàn thành
    # Gửi sự kiện tới client để thông báo auto test đã kết thúc (và kích hoạt lại các nút)
    socketio.emit('auto_test_finished', namespace='/')

    print("[DEBUG] Auto test done.")


# --- Flask Routes ---
@app.before_request
def load_global_tasks():
    print(f"[DEBUG] before_request: Kiểm tra và load tasks nếu cần.")
    """
    Hàm này được chạy trước mỗi yêu cầu HTTP tới ứng dụng Flask.
    Nó đảm bảo rằng danh sách các task được tải một lần và lưu vào app.config
    để có thể truy cập dễ dàng bởi các route và trong templates qua `g.tasks`.
    """
    # Chỉ load tasks một lần khi app mới khởi động
    if 'LOADED_TASKS' not in app.config:
        print("[DEBUG] load tasks")
        app.config['LOADED_TASKS'] = load_tasks()
        print(f"[DEBUG] Đã load {len(app.config['LOADED_TASKS'])} tasks.")

        # Khởi tạo task_results lần đầu với trạng thái "Pending" cho tất cả các task
        for task in app.config['LOADED_TASKS']:
            task_results[task['name']] = {'status': 'Pending', 'message': ''}
    
    g.tasks = app.config['LOADED_TASKS'] # Lưu vào g để truy cập trong templates
    print(f"[DEBUG]  {len(g.tasks)} task.")


@app.route('/')
def dashboard():
    print("[DEBUG] Truy cập dashboard, render danh sách task.")
    """Route cho trang Dashboard chính."""
    # Truyền danh sách task và kết quả hiện tại của chúng tới template
    return render_template('dashboard.html', tasks=g.tasks, task_results=task_results)  # tasks là list, mỗi task có .result và .summary

@app.route('/task/<task_name_encoded>')
def show_task(task_name_encoded):
    print(f"[DEBUG] Truy cập trang chi tiết task: {task_name_encoded}")
    """Route cho trang chi tiết của từng task."""
    # Giải mã tên task từ URL (ví dụ: "Example%20Gpio" thành "Example Gpio")
    # Sử dụng request.args.get('name') để tương thích nếu tên được truyền qua query parameter
    task_name = request.args.get('name', task_name_encoded.replace('%20', ' '))
    # Tìm thông tin task trong danh sách các task đã tải
    task_info = next((task for task in g.tasks if task['name'] == task_name), None)
    if task_info:
        print(f"[DEBUG] found: {task_info['name']}")
        # Render template task.html và truyền thông tin task và kết quả hiện tại của nó
        return render_template('task.html', task=task_info, result=task_results.get(task_name, {'status': 'Pending', 'message': ''}))
    print(f"[WARNING]{task_name} not found in loaded tasks.")
    return "Task not found", 404 # Trả về lỗi 404 nếu không tìm thấy task

@app.route('/run_task/<task_name_encoded>', methods=['POST'])
def run_task_route(task_name_encoded):
    print(f"[DEBUG] Run task: {task_name_encoded}")
    """API endpoint để chạy một task cụ thể (được gọi qua AJAX POST từ frontend)."""
    task_name = request.args.get('name', task_name_encoded.replace('%20', ' '))
    task_to_run = next((task for task in g.tasks if task['name'] == task_name), None)
    if task_to_run:
        print(f"[DEBUG] Starting run:[{task_name}]")
        # Chạy task trong một luồng riêng biệt để không làm block ứng dụng chính
        thread = threading.Thread(target=execute_single_task, args=(task_to_run,))
        thread.daemon = True # Đặt luồng là daemon để nó tự kết thúc khi ứng dụng chính tắt
        thread.start()
        return jsonify(success=True, message=f"Task '{task_name}' started in background.")
    print(f"[WARNING] Task not found: {task_name}")
    return jsonify(success=False, message="Task not found."), 404

@app.route('/run_all_tasks', methods=['POST'])
def run_all_tasks_route():
    print("[DEBUG] Automatic run all tasks requested.")

    global auto_test_running # Sử dụng biến cờ toàn cục
    if auto_test_running:
        print("[WARNING] Auto test running.")
        return jsonify(success=False, message="Auto test is already running.")

    auto_test_running = True
    # Gửi sự kiện tới client để thông báo auto test đã bắt đầu (và vô hiệu hóa các nút)
    socketio.emit('auto_test_started', namespace='/')

    # Chạy tất cả các task trong một luồng riêng
    thread = threading.Thread(target=execute_all_tasks)
    thread.daemon = True
    thread.start()
    print("[DEBUG] o test started in background.")
    return jsonify(success=True, message="Auto test started in background.")

@app.route('/test_items/<task_name>')
def get_test_items(task_name):
    # Tìm module task
    task = next((t for t in g.tasks if t['name'] == task_name), None)
    if not task:
        return jsonify({"success": False, "message": "Task not found"}), 404
    # Lấy danh sách hạng mục từ module
    items = getattr(task['function'].__module__, 'ITEMS', [])
    return jsonify({"success": True, "items": items})

# --- SocketIO Event Handlers ---
@socketio.on('connect')
def handle_connect():
    print(f"[DEBUG] Client connected: {request.sid}")
    """Xử lý sự kiện khi một client kết nối tới SocketIO server."""
    # Gửi trạng thái hiện tại của tất cả tasks cho client vừa kết nối
    socketio.emit('full_task_status_update', task_results, namespace='/')
    # Gửi toàn bộ lịch sử log cho client vừa kết nối
    socketio.emit('initial_log', {'log': "\n".join(task_logs)}, namespace='/')
    # Nếu auto test đang chạy, thông báo cho client mới để vô hiệu hóa nút
    if auto_test_running:
        socketio.emit('auto_test_started', namespace='/')

@socketio.on('disconnect')
def handle_disconnect():
    print(f"[DEBUG] Client disconnected: {request.sid}")
    """Xử lý sự kiện khi một client ngắt kết nối."""
    # Không cần xử lý gì đặc biệt ở đây, nhưng có thể ghi log hoặc thực hiện các hành động khác nếu cần