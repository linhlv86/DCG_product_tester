# tasks/task_example_gpio.py
import time
import random

# Mô tả của task này, sẽ hiển thị trên giao diện người dùng
DESCRIPTION = "Kiểm tra kết nối và trạng thái của các chân GPIO."

# Danh sách các hạng mục kiểm tra mô phỏng
ITEMS = [
    {"id": "power", "name": "Kiểm tra nguồn"},
    {"id": "signal", "name": "Kiểm tra tín hiệu GPIO"},
    {"id": "led", "name": "Kiểm tra LED"}
]

def test_task():
    """
    Hàm này chứa logic test thực tế cho GPIO.
    Nó phải trả về một tuple (boolean_result, message_string):
    - boolean_result: True nếu test Pass, False nếu test Fail.
    - message_string: Một chuỗi thông báo chi tiết về kết quả.
    """
    print(f"[{time.strftime('%H:%M:%S')}] Running GPIO test...")
    time.sleep(1.5) # Giả lập thời gian thực hiện test (ví dụ: 1.5 giây)

    try:
        # --- PHẦN TƯƠNG TÁC PHẦN CỨNG THỰC TẾ (CHỈ CHẠY TRÊN ORANGE PI CM4) ---
        # Để tránh lỗi khi chạy trên PC (nơi không có thư viện GPIO),
        # chúng ta sẽ sử dụng một khối try-except để giả định rằng thư viện phần cứng không được tìm thấy.
        try:
            # Uncomment và thay thế bằng code GPIO thực tế của Orange Pi CM4
            # Ví dụ:
            # import OPi.GPIO as GPIO # hoặc RPi.GPIO nếu tương thích
            # GPIO.setmode(GPIO.BOARD) # hoặc GPIO.BCM tùy theo cách bạn muốn đánh số chân
            # GPIO.setup(7, GPIO.OUT)  # Cấu hình chân 7 là output
            # GPIO.output(7, GPIO.HIGH) # Bật đèn LED hoặc relay
            # time.sleep(0.5)
            # GPIO.output(7, GPIO.LOW)  # Tắt đèn LED
            # return True, "Real GPIO test: LED blinked successfully on pin 7."

            # TRÊN PC, chúng ta sẽ ép nó vào khối except ImportError để chạy phần mô phỏng:
            raise ImportError("Simulating no actual GPIO library on PC.")

        except ImportError:
            # --- PHẦN LOGIC MÔ PHỎNG (SẼ CHẠY KHI THƯ VIỆN PHẦN CỨNG THẬT KHÔNG CÓ) ---
            print(f"[{time.strftime('%H:%M:%S')}] Simulating GPIO test result on PC.")
            # Mô phỏng từng hạng mục kiểm tra
            results = []
            # Hạng mục 1: Kiểm tra nguồn
            power_ok = random.choice([True, True, False])
            results.append({"id": "power", "name": "Kiểm tra nguồn", "pass": power_ok, "message": "Nguồn OK" if power_ok else "Nguồn yếu"})
            # Hạng mục 2: Kiểm tra tín hiệu GPIO
            signal_ok = random.choice([True, False])
            results.append({"id": "signal", "name": "Kiểm tra tín hiệu GPIO", "pass": signal_ok, "message": "Tín hiệu tốt" if signal_ok else "Tín hiệu lỗi"})
            # Hạng mục 3: Kiểm tra LED
            led_ok = random.choice([True, False])
            results.append({"id": "led", "name": "Kiểm tra LED", "pass": led_ok, "message": "LED sáng" if led_ok else "LED không sáng"})
            # Tổng kết
            all_pass = all(item["pass"] for item in results)
            summary = "Tất cả các hạng mục đạt yêu cầu." if all_pass else "Có hạng mục không đạt."
            # Chuyển đổi results sang detail_results đúng format
            detail_results = []
            for item in results:
                detail_results.append({
                    'item': item['name'],
                    'result': 'PASS' if item['pass'] else 'FAIL',
                    'detail': item['message'],
                    'passed': item['pass']
                })
            return 'Passed' if all_pass else 'Failed', summary, detail_results
        except Exception as e:
            # Bắt bất kỳ lỗi nào khác có thể xảy ra trong quá trình test phần cứng thật
            return False, f"Real GPIO test encountered an error: {str(e)}"

    except Exception as e:
        # Bắt lỗi tổng quát nếu có vấn đề gì xảy ra trong hàm test_task (ngoài phần cứng)
        return False, f"Unexpected error during GPIO test execution: {str(e)}"