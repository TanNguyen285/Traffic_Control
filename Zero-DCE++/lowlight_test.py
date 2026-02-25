import torch
import torch.nn as nn
import torchvision
import os
import model
import numpy as np
from PIL import Image
import glob
import time

def lowlight(image_path, output_root):
    os.environ['CUDA_VISIBLE_DEVICES']='0'
    scale_factor = 12
    
    # 1. Load ảnh
    data_lowlight = Image.open(image_path)
    data_lowlight = (np.asarray(data_lowlight)/255.0)
    data_lowlight = torch.from_numpy(data_lowlight).float()

    h = (data_lowlight.shape[0]//scale_factor)*scale_factor
    w = (data_lowlight.shape[1]//scale_factor)*scale_factor
    data_lowlight = data_lowlight[0:h, 0:w, :]
    data_lowlight = data_lowlight.permute(2, 0, 1)
    data_lowlight = data_lowlight.cuda().unsqueeze(0)

    # 2. Load Model (Nên mang ra ngoài vòng lặp nếu xử lý nhiều ảnh để nhanh hơn)
    DCE_net = model.enhance_net_nopool(scale_factor).cuda()
    model_path = 'Zero-DCE_extension-main/Zero-DCE++/snapshots_Zero_DCE++/Epoch99.pth'
    DCE_net.load_state_dict(torch.load(model_path, weights_only=True))
    
    # 3. Chạy Inference
    start = time.time()
    enhanced_image, _ = DCE_net(data_lowlight)
    end_time = (time.time() - start)

    # 4. XỬ LÝ LƯU FILE RA NGOÀI
    # Lấy tên file gốc (VD: 101_0_.png)
    file_name = os.path.basename(image_path)
    
    # Tạo đường dẫn lưu file mới trong thư mục output_root
    result_path = os.path.join(output_root, file_name)
    
    # Tạo thư mục nếu chưa có
    if not os.path.exists(output_root):
        os.makedirs(output_root)

    torchvision.utils.save_image(enhanced_image, result_path)
    return end_time

if __name__ == '__main__':
    with torch.no_grad():
        # Đường dẫn ảnh đầu vào
        input_path = 'Zero-DCE_extension-main/Zero-DCE++/data/test_data/'
        
        # ĐƯỜNG DẪN LƯU NGOÀI (Bạn có thể sửa thành 'D:/KetQua_DCE' hoặc bất cứ đâu)
        output_external = 'C:/Users/LagCT/Desktop/DCE_Results_Output' 

        # Lấy danh sách ảnh
        test_list = glob.glob(os.path.join(input_path, "**/*.*"), recursive=True)
        image_extensions = ('.png', '.jpg', '.jpeg')
        test_list = [f for f in test_list if f.lower().endswith(image_extensions)]

        print(f"Tim thay {len(test_list)} anh. Bat dau xu ly...")

        sum_time = 0
        for image in test_list:
            print(f"Dang xu ly: {os.path.basename(image)}")
            sum_time += lowlight(image, output_external)

        print("-" * 30)
        print(f"Hoan thanh! Anh da duoc luu tai: {output_external}")
        print(f"Tong thoi gian: {sum_time:.4f}s")