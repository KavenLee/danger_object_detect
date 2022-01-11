from pymodbus.version import version
from pymodbus.server.asynchronous import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from threading import Thread,Event
import process
from time import sleep,time
from config import Config
from twisted.internet import reactor
from queue import Queue


# Holding Register, Input Register Address
hr_adr=200
ir_adr=100

# CCTV Start/Stop Address
cctv_flag_adr=200

# ROI Box 좌표 값들을 Json에 Save/Load/Apply Address
roi_flag_adr=201

# Modbus에 입력된 ROI 좌표값들을 JSON으로 저장하기 위한 값
roi_flag_save=100
# JSON에 저장된 ROI 좌표값들을 Modbus로 불러오기 위한 값
roi_flag_load=101
# Modbus에 입력된 ROI 좌표값들을 저장하지는 않고 화면에 표시하기 위한 값
roi_flag_apply=102

# ROI BOX 좌표 시작점
roi_data_adr=202 # ROI Left 
roi_data_top=203 # ROI Top
roi_data_right=204 # ROI Right
roi_data_bottom=205 # ROI Bottom

# ROI BOX를 그릴지 말지에 대한 값을 입력하기 위한 Address
# Default 1, 그리지 않으려면 0
roi_box_flag_adr=206

# 학습을 위한 Image 수집을 위해 Flag를 주기 위한 Address
# Default 0, 수집을 하려면 1
img_save_flag_adr=207

# ROI BOX 를 벗어난 Object들을 그릴지 말지에 대한 Flag를 위한 Address
# Default 1, 보지 않으려면 0
danger_box_adr=208

# CCTV Object Detection Program이 작동중인 것을 표시해주는 값을 입력하기 위한 Address
cctv_alive_adr=101

# ROI BOX 에서 Object 가 Detect가 됐을때 그것을 표시 하기 위한 Address
detected_signal_adr=102

# Object가 계속 Detect되고 있다는것을 알려주기 위한 Address
detected_sum_adr=103

# Detect 가 완료된 Image를 Json 으로 저장하고 그 Json 파일의 이름을 UUID(GUID)로 변환하고
# 그 UUID 를 알려주기 위한 Address
uuid_set_adr=112




class CustomDataBlock(ModbusSequentialDataBlock):
    """ A datablock that stores the new value in memory
    and performs a custom action after it has been stored.

    """

    def setValues(self, address, value):
        """ Sets the requested values of the datastore
        :param address: The starting address
        :param values: The new values to be set
        """
        
        super(CustomDataBlock, self).setValues(address, value)
        
        # whatever you want to do with the written value is done here,
        # however make sure not to do too much work here or it will
        # block the server, espectially if the server is being written
        # to very quickly
        #print("wrote {} to {}".format(value, address))
        
        
        # address 200: cctv start(1)/stop(0)
        if address ==cctv_flag_adr and len(value)>0:
            if value[0] == 0 or value[0] ==1:
                start_detect(value[0])
            
        # address 201 : roi data load(101)/save(100) flag       
        if address == roi_flag_adr and len(value)>0:
            if value[0] == roi_flag_save or value[0] ==roi_flag_load or value[0] == roi_flag_apply:
                set_roi(value[0])
            
                
        # address 202,203,204,205 : roi data update
        #if (address == roi_data_adr or address== roi_data_top or address== roi_data_right or \
        #    address==roi_data_bottom) and len(value)>0:
        #    Update_Roi()
        
        
        # address 206 : cctv roi box visirble
        if address==roi_box_flag_adr and len(value)>0:
            if value[0] == 0 or value[0] ==1:
                box_visirble(value[0])

        
        # address 207 : cctv image save flag
        if address==img_save_flag_adr and len(value)>0:
            if value[0] == 0 or value[0] ==1:
                img_save_flag(value[0])

        # address 208 : Danger Object Box visirble/invisirble
        if address == danger_box_adr and len(value)>0:
            if value[0] ==0 or value[0] ==1:
                DangerObjectVisirble(value[0])


    def getValues(self, address, count):
        return super().getValues(address,count)


# CCTV Start flag detect
def start_detect(value):
    '''
    PLC에서 0 or 1 을 한번만 입력하는 것이 아닌 계속해서 입력하기 때문에
    System이 계속 시작과 종료를 반복하므로 한번 입력되면 그것을 기준으로
    판단하기 위해 입력된 값을 저장하기 위한 변수선언
    '''
    if not hasattr(start_detect,'start_flag'):
        start_detect.start_flag = 0 
    
    if start_detect.start_flag == value:
        return

    start_detect.start_flag=value
    
    if value ==0:
        cctvEvent.clear()
        imgQueue.queue.clear()
        #ir.setValues(detected_sum_adr,[0])
        #ir.setValues(detected_signal_adr,[0])
        print("CCTV detector is stopped.")
    else:
        cctvEvent.set()
        
        print('CCTV detector is started.')
    

# ROI Box value save / load
def set_roi(value):
    
    conf_data=Config.instance()
    set_data=[]
    
    if value == roi_flag_save:    
        set_data=hr.getValues(roi_data_adr,4)
        conf_data.cctv_roi_left=set_data[0]
        conf_data.cctv_roi_top=set_data[1]
        conf_data.cctv_roi_right=set_data[2]
        conf_data.cctv_roi_bottom=set_data[3]
        conf_data.save('/home/cctv/dev/python/config.json')
        conf_data.load('/home/cctv/dev/python/config.json')
        print('ROI Save & Apply.')
    elif value == roi_flag_load:
        conf_data.load('/home/cctv/dev/python/config.json')
        set_data.append(conf_data.cctv_roi_left)
        set_data.append(conf_data.cctv_roi_top)
        set_data.append(conf_data.cctv_roi_right)
        set_data.append(conf_data.cctv_roi_bottom)
        hr.setValues(roi_data_adr,set_data)
        print('ROI Load.')
    elif value == roi_flag_apply:
        print('ROI Apply.')
    

    Update_Roi()
    hr.setValues(roi_flag_adr,[0])
        
    del set_data,conf_data


# ROI Box Visirble / Invisirble
def box_visirble(value):
    '''
    PLC에서 0 or 1 을 한번만 입력하는 것이 아닌 계속해서 입력하기 때문에
    System이 계속 시작과 종료를 반복하므로 한번 입력되면 그것을 기준으로
    판단하기 위해 입력된 값을 저장하기 위한 변수선언
    '''
    if not hasattr(box_visirble,'flag'):
        box_visirble.flag=1
    
    if box_visirble.flag==value:
        return

    box_visirble.flag=value

    if value == 1:
        process.box_flag=1
        print('roi box visirble.')
    elif value ==0:
        process.box_flag=0
        print('roi box invisirble.')


# Image save / don't save
def img_save_flag(value):
    '''
    PLC에서 0 or 1 을 한번만 입력하는 것이 아닌 계속해서 입력하기 때문에
    System이 계속 시작과 종료를 반복하므로 한번 입력되면 그것을 기준으로
    판단하기 위해 입력된 값을 저장하기 위한 변수선언
    '''
    if not hasattr(img_save_flag,'flag'):
        img_save_flag.flag=0

    if img_save_flag.flag == value:
        return

    img_save_flag.flag=value
    
    if value == 1:
        process.save_flag=1
        print('save flag on.')
    elif value == 0:
        process.save_flag=0
        print('save flag off.')


# ROI BOX Data Update
# ROI BOX data를 저장하는 것과 별개로 실시간 값을 받아 화면에 보여주기위한 method
def Update_Roi():
    process.roi_coordinate=hr.getValues(roi_data_adr,4)


# Danger Object Box visirble/invisirble
def DangerObjectVisirble(value):
    '''
    PLC에서 0 or 1 을 한번만 입력하는 것이 아닌 계속해서 입력하기 때문에
    System이 계속 시작과 종료를 반복하므로 한번 입력되면 그것을 기준으로
    판단하기 위해 입력된 값을 저장하기 위한 변수선언
    '''
    if not hasattr(DangerObjectVisirble,'flag'):
        DangerObjectVisirble.flag=0
    
    if DangerObjectVisirble.flag==value:
        return
    
    if value==1:
        print('Not Danger Object Visirble.')
    elif value==0:
        print('Not Danger Object Invisirble.')
    
    DangerObjectVisirble.flag=value
    process.not_danger_box_flag=value



# CCTV Start Signal
# CCTV 가 시작 될때 Modbus에 필요한 값들을 미리 한번 적기 위한 method
def readySignal():
    try:
        print('Ready!')
        conf_data = Config.instance()
        result = conf_data.load('/home/cctv/dev/python/config.json')
        roi_data=[]
        if result is True:
            roi_data.append(conf_data.cctv_roi_left)
            roi_data.append(conf_data.cctv_roi_top)
            roi_data.append(conf_data.cctv_roi_right)
            roi_data.append(conf_data.cctv_roi_bottom)
       
        hr.setValues(roi_data_adr,roi_data)
        hr.setValues(roi_box_flag_adr,[process.box_flag])
        hr.setValues(img_save_flag_adr,[process.save_flag])
        ir.setValues(ir_adr,[1])
        process.roi_coordinate=roi_data
        hr.setValues(danger_box_adr,[process.not_danger_box_flag])
        
        del roi_data,conf_data
        
    except:
        print('Configure JSON Load Failed.')


# Modbus Server
def run_async_server(hr,ir):

    # --------------------------------------------------------------

    store=ModbusSlaveContext(hr=hr,ir=ir,zero_mode=True)
    context= ModbusServerContext(slaves=store,single=True)

    identity = ModbusDeviceIdentification()
    identity.VendorName = 'APPSO'
    identity.ProductCode = 'AP'
    identity.VendorUrl = 'http://appso.co.kr/'
    identity.ProductName = 'Person Detector'
    identity.ModelName = 'Person Detector'
    identity.MajorMinorRevision = version.short()
    
    StartTcpServer(context, identity=identity, address=("0.0.0.0", 502),defer_reactor_run=True)

    # CCTV 시작 전에 필요한 값들을 Modbus에 미리 적기 위한 method
    readySignal()
    
    # 위의 method를 한번 하고 StartTcpServer 를 실행하기 위한 reactor
    reactor.run()


# CCTV Image Download Thread
def GetCctvImage():
    now = time()
    while True:
        cctvEvent.wait()
        
        #img_file=process.next_file('/home/cctv/dev/python/img')
        #img=process.img_cvt(img_file)
        #imgQueue.put(img)
        #sleep(0.1)

        if ((time() - now) > 0.1):
            imgQueue.put(process.img_down())
        
            while imgQueue.qsize() > 5:
                imgQueue.get()
            
            now = time()


# CCTV Data Processing
def cctv_detect_thread():
    while True:
        
        # Modbus 200 address 값에 따라 실행을 하기 위해 Event를 잠시 멈춤
        #cctvEvent.wait()
        data=None
        detected=0
        # process에서 Object Detection 완료한 후 UUID와 Detect 되었는지에 대한 값
        
        data,detected=process.main(imgQueue.get())
        
        # uuid 가 없다면 0 을 modbus에 입력
        if data is None:
            data=[0]
        else:
            data=list(data)

        # object detect 가 연속해서 되고 있으면 그것을 표시하기 위한 변수선언
        count=0
        
        # object detect 가 되었다면 1 씩 증가하기
        if detected == 2:
            count=1
            i=ir.getValues(detected_sum_adr,1).pop()
            if i == 100:
                count=101
            else:
                count+=i
        
        # 작동 flag 가 0이 되면 초기화 시키기
        if hr.getValues(hr_adr,1) == [0]:
            detected=0
            count=0
            
        ir.setValues(uuid_set_adr,data)
        ir.setValues(detected_signal_adr,[detected])
        ir.setValues(detected_sum_adr,[count])

        sleep(0.01)
        
        del data


# CCTV alive signal 
# cctv object detection program이 작동중인것을 표시하기위한 별도의 Thread에서 작동
# 값을 1씩 증가
def alive_thread():
    i=0
    while True:
        sleep(1)
        ir.setValues(cctv_alive_adr,[i])
        i+=1



def main():
    # input registers,holding registers 에 값 들을 입력 및 삭제를 위해 global 선언
    global cctvEvent,ir,hr,imgQueue
    
    imgQueue=Queue()
    cctvEvent = Event()
    
    # json file delete
    del_thread=Thread(target=process.file_delete,args=[3])
    del_thread.setDaemon(True)
    del_thread.start()
    
    # cctv image download thread
    imgDownThread=Thread(target=GetCctvImage)
    imgDownThread.setDaemon(True)
    imgDownThread.start()
    
    # cctv 에서 Object Detect 되었을 경우 실행하는 Process
    cctvThread = Thread(target=cctv_detect_thread)
    cctvThread.setDaemon(True)
    cctvThread.start()

    # 첫 실행시 시간이 소요되어 미리 한번 실행.
    process.net_ready()
    process.main('/home/cctv/dev/python/t.png')
    #process.main(imgQueue.get())
    
    # cctv 작동중인 것을 나타내기 위한 신호를 주기위한 Thread.
    aliveThread=Thread(target=alive_thread)
    aliveThread.setDaemon(True)
    aliveThread.start()
    
    
    # create data block for holding registers and input registers
    hr = CustomDataBlock(hr_adr, [0] * 16)
    ir = ModbusSequentialDataBlock(ir_adr, [0] * 20)

    print("Modbus slave is started...")
    run_async_server(hr=hr, ir=ir)
    


if __name__=='__main__':
    main()
