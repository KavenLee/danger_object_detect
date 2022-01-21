import requests
from requests.auth import HTTPDigestAuth
import cv2
import numpy as np
from urllib.error import HTTPError
import os
import json
import base64
from uuid import uuid4
import struct
from datetime import datetime
from config import Config
from threading import Timer
from time import time
from rect import Rectangle,GetIntersectionRatio
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

global save_flag,box_flag,min_ratio,roi_coordinate,not_danger_box_flag

# original image save flag
save_flag = 0

# Roi Box visirble/invisirble
box_flag = 1

# Roi Box intersection minimum ratio
min_ratio=5

# Roi Box coordinate from PLC
roi_coordinate=list()

# Roi box outline Object Box visirble/invisirble flag 
not_danger_box_flag=1

def img_down():
    try:
        conf_data=Config.instance()

        url = 'http://'+conf_data.cctv_ip_addr+'/stw-cgi/video.cgi'
        uid = conf_data.cctv_id
        passwd = conf_data.cctv_passwd
        headers = {'Content-Type': 'image/jpeg'}
        payload = {'msubmenu': 'snapshot', 'action': 'view'}

        r = requests.get(url, params=payload, headers=headers, auth=HTTPDigestAuth(uid, passwd),stream=True)
        
        '''
        # ---------------------------------------------
        # Retry Parameters
        retries=3
        backoff_factor=3
        status_forcelist=(100)

        # Session 생성 후 Retry 적용
        sess=requests.Session()
        
        # sess.auth=(uid,passwd
        # sess.headers.update(headers)

        retry=Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist
        )
        adapter=HTTPAdapter(max_retries=retry)
        sess.mount('http://',adapter=adapter)
        sess.mount('https://',adapter=adapter)
        # ---------------------------------------------
        
        r= sess.get(url=url,params=payload)
        '''


        # Web access is Success
        if r.status_code == 200:
            
            # Get Image
            
            print('Web Access Success.')     
            
            #i = Image.open(BytesIO(r.content))
            
            image = np.asarray(bytearray(r.content), dtype="uint8")
            image = cv2.imdecode(image, cv2.IMREAD_COLOR)

            # Image convert
            src=convert_img(image)
            
            # Image Save
            if save_flag == 1:
                #original_img_down(image) # 원본 이미지 저장
                original_img_down(src) # 변경 이미지 저장
            
            return src
        else:
            print('CCTV image download is failed. => Status Code:' + str(r.status_code))
            return None
    except HTTPError as e:
        err = e.read()
        code = e.getcode()
        print("Error : {} , ErrorCode : {}".format(err, code))
        return None
    except OSError:
        if conf_data.cctv_reboot == 1:
            os.system('sudo reboot')

        print('CCTV is Daed.')
        return None


# darknet ready for yolo detect
def net_ready():
    
    global cv_net_yolo, outlayer_names

    try:
        # weights file,config file Ready
        home=os.path.dirname(os.path.realpath(__file__))
        weights_path=os.path.join(home,'yolov3_best.weights')
        config_path=os.path.join(home,'yolov3.cfg')
        
        # YOLO Inference network Model Loading
        cv_net_yolo=cv2.dnn.readNetFromDarknet(config_path,weights_path)


        # detected Object filltering
        
        #전체 Darknet layer에서 13x13 grid, 26x26, 52x52 grid에서 detect된 Output layer만 filtering
        layer_names = cv_net_yolo.getLayerNames()
        # layer_names : ['conv_0', 'bn_0', 'relu_1', 'conv_1', 'bn_1', 'relu_2', 'conv_ ....
        
              
        outlayer_names=[layer_names[i[0]-1] for i in cv_net_yolo.getUnconnectedOutLayers()]
        # cv_net_yolo.getUnconnectedOutLayers() : [[200], [227], [254]]
        

        # Using GPU
        cv_net_yolo.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
        cv_net_yolo.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
        
        print('Darknet Ready Success.')

    except Exception as e:
        print("Darknet Ready Failed...")
        print(e)
    
        

# yolo img detect
def detect_img(src):

    try:
        # size trans to (416,416) and BGR to RGB
        # scalefactor *******
        '''
        Yolov3 416는 416 x 416 Input을 받는다. 원본 이미지 배열을 사이즈 (416, 416)으로, BGR을 RGB로 변환하여 배열 입력
        blobFromImage를 사용해서 CNN에 넣어야할 이미지 전처리를 쉽게 한다.
        DarkNet에서는 scalefactor를 꼭 처리해줘야한다.
        '''
        out = cv2.dnn.blobFromImage(src,scalefactor=1/255.0,size=(416,416), swapRB=True,crop=False)

        # Image Input(Image Setting)
        cv_net_yolo.setInput(out)

        # return Results
        # inference를 돌려서 원하는 layer의 Feature Map 정보만 뽑아 낸다.
        cv_outs = cv_net_yolo.forward(outlayer_names)
        print('Detected completed.')

        return cv_outs

    except Exception as e:
        print("Detected Failed...")
        print(e)
        return None



# Detected Results Processing
def detected_processing(src,cv_outs):

    # bounding box predict
    '''
    blobFromImage 로 인해 resize 된 이미지 기반으로 bounding box위치가 예측 되므로
    이를 다시 원복 하기 위해 원본 이미지의 shape 필요.
    '''
    rows = src.shape[0]
    cols = src.shape[1]

    conf_threshold = 0.5
    nms_threshold = 0.4  # This values to increments box disappear

    class_ids = []
    confidences = []
    boxes = []

    result_list=[]
        
    try:
        for ix, output in enumerate(cv_outs):

            for jx, detection in enumerate(output):
                # class score는 detetection배열에서 5번째 이후 위치에 있는 값. 즉 6번쨰~85번째 까지의 값
                #scores = detection[5:]
                scores = detection[5]
                #print('scores : ', type(scores),scores,detection[5:])

                #if scores == 0:
                #    break
               
               # scores배열에서 가장 높은 값을 가지는 값이 class confidence, 그리고 그때의 위치 인덱스가 class id
                #class_id = np.argmax(scores)
                class_id = 0
                
                # 5번쨰 값은 objectness score이다. 객체인지 아닌지의 확률이다. 6번쨰~85번째 까지의 값이 그 객체일 확률 값이다. 
                #confidence = scores[class_id]
                confidence = scores

                if confidence > conf_threshold:
                    # detection은 scale된 좌상단, 우하단 좌표를 반환하는 것이 아니라, detection object의 중심좌표와 너비/높이를 반환
                    # 원본 이미지에 맞게 scale 적용 및 좌상단, 우하단 좌표 계산
                    center_x = int(detection[0] * cols)
                    center_y = int(detection[1] * rows)
                    width = int(detection[2] * cols)
                    height = int(detection[3] * rows)
                    left = int(center_x - width / 2)
                    top = int(center_y - height / 2)
                    
                    # 3개의 개별 output layer별로 Detect된 Object들에 대한 class id, confidence, 좌표정보를 모두 수집
                    class_ids.append(class_id)
                    confidences.append(float(confidence))

                    boxes.append([left, top, width, height])

        #print('==================finished')
        # ----------------------------------image Noise remove-------------------
        '''
        이 index의 box만 살아남았음을 의미한다. (Non-Maximum Suppression) 
        중복되는 박스들을 없애준다. 다른 박스들과 비교했을 때, 교집합이 되는 부분이 
        정해진 threshold보다 적을 시 제거한다.
        '''
        try:
            if boxes is not None and confidences is not None:
                idxs = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)
                 
                if type(idxs) is not tuple:
                    # Image에 Box를 그리기 위해 필요한 값들을 저장하여 return
                    result_list.append(idxs)
                    result_list.append(boxes)
                    result_list.append(class_ids)
                    result_list.append(confidences)
        except Exception as e:
            print('=============Idxs processing Failed......')
            print(e)
        
        # ROI Box draw
        if box_flag==1:
            # Modbus에 찍힌 roi 값으로 box 를 그린다.
            cv2.rectangle(src,(roi_coordinate[0],roi_coordinate[1]),(roi_coordinate[2],roi_coordinate[3]),
                color=(255,255,255),thickness=2)

        # return draw_img,idxs,boxes,class_ids,confidences
        return result_list

    except Exception as e:
        print('Detected Results Prcoessing Failed.')
        print(e)
        return None


# detected box draw in image
def img_redraw(draw_img,result_list):

    #--------------------- image redraw with bounding box--------------------------
        

    # bounding box color setting
    green = (0, 255, 0)
    red = (0, 0, 255)

    # Object Detected Results Return
    if not hasattr(img_redraw,'result'):
        result=False

    try:                    
        # detected box writing txt file open.
        if save_flag==1:
            test_file=open('/home/cctv/dev/image/'+test_img_title+'.txt','w',encoding='utf8')
        
        if box_flag == 1:
        
            conf_data=Config.instance()
        
            '''
            result_list[0]=idxs
            result_list[1]=boxes
            result_list[2]=class_ids
            result_list[3]=confidences
            '''
            for i in result_list[0].flatten():
                box = result_list[1][i]
                left = box[0]
                top = box[1]
                width = box[2]
                height = box[3]
                
                #caption = "{}".format(labels_to_names_seq[result_list[2][i]])
                caption =  'person'
                
                # Detected Bounding Box in Image Save for Train
                if save_flag==1:
                    test_file.write(str(left)+' '+str(top)+' '+str(left+width)+' '+str(top+height)+' '+str(result_list[3][i])+'\n')
                
                # Interserction ROI,Object 
                
                # Modbus에 찍힌값으로 roi를 판별
                #roi=Rectangle(roi_coordinate[0],roi_coordinate[1],roi_coordinate[2],roi_coordinate[3])
                # config json 에 저장된 값으로 roi 판별
                roi=Rectangle(conf_data.cctv_roi_left,conf_data.cctv_roi_top,conf_data.cctv_roi_right,conf_data.cctv_roi_bottom)
                obj=Rectangle(left,top,left+width,top+height)
                #overlap_result=GetIntersectionRatio(roi,obj)
                overlap_result=GetIntersectionRatio(obj,roi)
                
                # ROI 와 Object가 최소 얼만큼 겹쳐야 하는지 판단
                if overlap_result>min_ratio:

                    # return result
                    result = True

                    # Detected Box Draw in Image
                    cv2.rectangle(draw_img, (int(left), int(top)), (int(left + width), int(top + height)),
                                color=red, thickness=2)
                    cv2.putText(draw_img, caption, (int(left), int(top - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, green, 1)
                else:
                    if not_danger_box_flag ==1:
                        cv2.rectangle(draw_img,(left,top),(left+width,top+height),color=green,thickness=2)
                        cv2.putText(draw_img,caption,(left,top-5),cv2.FONT_HERSHEY_SIMPLEX,0.5,red,1)
                
                print(caption)
                             
        if save_flag==1:
            test_file.close()
        
        del conf_data
        return result, draw_img

    except Exception as e:
        print("Drawing Result is Nothing...")
        print(e)
        return None,None



# data save
def set_json(result,img):

    print('Write Started json file.')
        
    # converting to gray (1 channel)
    #img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
    try:
        # Image를 Json 파일에 저장하기 위한 Encoding
        _,buffer=cv2.imencode('.png', img)
        img_text=base64.b64encode(buffer).decode('utf8')

        time=datetime.now()

        status={"Time":time.strftime('%Y-%m-%d %H:%M:%S.%f'),
                "ErrorCode":0,
                "Detected": result,
                "Base64Image":img_text
                }
                
        # JSON 파일의 제목을 위한 UUID 생성
        name=uuid4()

        json_dir=os.path.join('/home/cctv/dev/python','file')
        if os.path.isdir(json_dir) is False:
            os.mkdir(json_dir)

        with open(os.path.join(json_dir,str(name)+'.json'),'w') as f:
            json.dump(status,f)
    
        print('Finished json.')
    
        return name

    except Exception as e:
        print("Json Write Failed...")
        print(e)
        return None



# img file name trans for modbus 
def uuid_trans(name):
    try:
        # little endian
        tr_name=name.bytes_le

        cnt=int(len(tr_name)/2)

        byt2short=struct.unpack('<'+'H'*cnt,tr_name)

    
        return byt2short

    except Exception as e:
        print("UUID Trans Failed...")
        print(e)
        return None



# json file delete
def file_delete(num):
    try:
        file_json=[i for i in os.listdir('/home/cctv/dev/python/file/') if '.json' in i]
        file_json.sort(key=lambda f: os.stat(os.path.join('/home/cctv/dev/python/file',f)).st_mtime)
        
        for i,f in enumerate(file_json):
            if i == len(file_json)-num:
                break
            else:
                os.remove(os.path.join('/home/cctv/dev/python/file',f))
                
        # Timer Set, 2초마다 실행.
        timer=Timer(2,file_delete,[num])
        timer.start()

    except Exception as e:
        print("Json File Delete Failed...")
        print(e)



# original img down for training
def original_img_down(image):               
    test_img=datetime.now()
    
    global test_img_title
    test_img_title=test_img.strftime('%Y-%m-%d %H:%M:%S.%f')
    
    cv2.imwrite('/home/cctv/dev/image/'+test_img_title+'.png',image)



# trans img for training and detected
def convert_img(img):
    h,w=img.shape[:2]
    w-=1800 # 우에서 900만큼 자른 값
    x=900 # 좌에서 900만큼 자르기 위해 시작점을 900으로 설정
    y=0 # 높이는 그대로 표현
    
    #print(img.shape)
    
    # Crop (x, y, w, h): (900, 0, 2296, 1792)
    src=img[y:y+h,x:x+w]

    try:
        # Resize 50%
        src=cv2.resize(src, dsize=(0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)

        # Convert to grayscale
        dst = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)  # for converting to gray
        dst = cv2.cvtColor(dst, cv2.COLOR_GRAY2BGR)  # for converting to 3 channel (DNN에서 3채널만 사용 가능)

        return dst
    except Exception as e:
        print('Image Convert Error !')
        print(e)



# -------------- Test Code ----------------
# img file index process for test
def next_file(path):
    if not hasattr(next_file, "idx"):
        next_file.idx = 0

    if not hasattr(next_file, "files"):
        next_file.files = os.listdir(path)

    next_file.idx += 1
    if (next_file.idx >= len(next_file.files)):
        next_file.idx = 0

    if next_file.idx >= 0 and next_file.idx < len(next_file.files):
        return next_file.files[next_file.idx]
    else:
        return None

# img file convert to test
def img_cvt(file):
    file_img=cv2.imread('/home/cctv/dev/python/img/'+file,cv2.IMREAD_COLOR)
    h,w=file_img.shape[:2]
    w-=1800
    x=900
    y=0
    # Crop (x, y, w, h): (900, 0, 2296, 1792)
    src=file_img[y:y+h,x:x+w]

    file_img=cv2.resize(src, dsize=(0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    file_img = cv2.cvtColor(file_img, cv2.COLOR_BGR2GRAY)
    file_img=cv2.cvtColor(file_img,cv2.COLOR_GRAY2BGR)
    return file_img

# -----------------------------------------



# --------------- Main ----------------
def main(img):

    detected_result=False # Detected Result
    
    start=time()
    
    if img is not None:
    
        #img=img_down()
        #img_file=next_file('/home/cctv/dev/python/img')
        #img=img_cvt(img_file)
        print('===================================================')
        #print('Image Getting Elapsed:',time()-start)

        # Detect Image
        unit_time = time()
        out_results=detect_img(img)
        #print('cv_outs length : ',len(out_results))
        #print('cv_outs : ',out_results)
        print('Yolo Detecting Elapsed:',time()-unit_time)

        # Detected Results Process
        unit_time = time()
        result_list=detected_processing(img,out_results)
        print('Result Processing Elapsed:',time()-unit_time)
        
        if result_list:
            # Draw using Detected Results
            unit_time = time()
            detected_result,img=img_redraw(img,result_list)
            print('Drawing Elapsed:',time()-unit_time)

        # json file create
        unit_time = time()
        name=set_json(detected_result,img)
        print('Generating JSON Elapsed:',time()-unit_time)

        # uuid trans for modbus
        name2short=uuid_trans(name)
        print('Total Elapsed:',time()-start)
        return name2short, 2 if detected_result else 1
    else:
        return None,100



if __name__=='__main__':
    main()
