import json
import os
from datetime import datetime

class quanly_log:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        self.temp_file = os.path.join(self.log_dir, "traffic_temp.json")
        self.data_list = [] 
        
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        if os.path.exists(self.temp_file):
            try:
                with open(self.temp_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        self.data_list = content
            except:
                self.data_list = []

    def update_storage(self, ai_results):
        now = datetime.now()
        
        # CHỈ LƯU SỐ LIỆU 
        storage_entry = {
            "time": now.strftime("%H:%M:%S"),
            "ket_ornot": ai_results.get("cnn_status"),
            "xe_local": ai_results.get("xe_local", 0),
            "counts": ai_results.get("counts", [0, 0, 0, 0, 0])
        }

        self.data_list.append(storage_entry)

        try:
            if len(self.data_list) >= 50:
                report_name = os.path.join(self.log_dir, f"report_{now.strftime('%Y%m%d_%H%M%S')}.json")
                with open(report_name, 'w', encoding='utf-8') as f:
                    json.dump(self.data_list, f, indent=4, ensure_ascii=False)
                if os.path.exists(self.temp_file): os.remove(self.temp_file)
                self.data_list = [] 
            else:
                with open(self.temp_file, 'w', encoding='utf-8') as f:
                    json.dump(self.data_list, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Lỗi lưu file: {e}")