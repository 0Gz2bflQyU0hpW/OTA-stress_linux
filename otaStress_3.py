#!/usr/bin/dev python
# -*- coding:utf-8 -*-
import sys
import os
import re
import time
import requests
import logging
import threading
import exceptions
import ConfigParser
import subprocess
import serial
import serial.tools.list_ports
import signal
import json
import psutil
import traceback
from uiautomator import Device

# read config parameter
cf = ConfigParser.ConfigParser()
cf.read("config.ini")
device_id = cf.get("configure", "device_id")
ser_num = cf.get("configure", "ser_num")
base_version = cf.get("configure", "base_version")
udisk_version = cf.get("configure", "udisk_version")
formate_data = cf.get("configure", "format_data")
target_version = cf.get("configure", "target_version")
email_receiver = cf.get("configure", "email_receiver")

#flag
adb_flag = "adb connected fail"
boot_flag = "Boot fail"
udisk_flag = "Udisk flash fail"
enter_system_flag = "Enter system fail"
network_error_flag = "Network connection fail"

# connect to device
tv = Device(device_id)

#check_timeout thread lock
check_timeout_lock = threading.Lock()

class monitor_adb(object):
   
    def run_adb(self,adb_command,timeout):
        print (time.strftime("%Y-%m-%d %H:%M:%S"), "adb -s %s %s" % (device_id, adb_command), timeout)
        self.p_cmd = subprocess.Popen("adb -s %s %s" %(device_id,adb_command),shell=True,
                                 stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.p_cmd_pid = self.p_cmd.pid
        check_timeout_thread = threading.Thread(target = self.check_command_timeout,args = (timeout,)).start()
        out,err = self.p_cmd.stdout.readlines(),self.p_cmd.stderr.readlines()
        if err != []:
            print ("warning:" + str(err))
            return out,err

    def check_command_timeout(self, timeout):
        check_timeout_lock.acquire()
        t = 0.0
        while self.p_cmd.poll() == None:
            time.sleep(0.1)
            if t >= timeout:
                try:
                    print("check adb command timeout,kill it now")
                    self.kill_timeout_pid()
                except:
                    pass
                break
            t += 0.1
        check_timeout_lock.release()

    def kill_timeout_pid(self):
        sig = signal.SIGKILL
        p = psutil.Process(self.p_cmd_pid)
        p_children = p.children(recursive=True)
        for _p in p_children:
            os.kill(_p.pid,sig)
        print("timeout process killed")

def install_apk(apk_path):
    apk_version_error = "failure [install_failed_version_downgrade]"
    out , err = _monitor_adb.run_adb("install %s" % apk_path,60)
    result = str(out+err).lower()

    if "success" in result:
        print("apk installt is successfully")
    elif apk_version_error in result:
        print("apk install Failed,Reason:installing apk version is not match the test equipment")
    else:
        print("unkonow error : " + result)

def install_uiautomator():
    logger.info("install app-uiautomator apk")
    os.system("adb -s " + device_id + " shell pm uninstall com.github.uiautomator")
    time.sleep(5)
    os.system("adb -s " + device_id + " shell pm uninstall com.github.uiautomator.test")
    time.sleep(5)
    install_apk('./app-uiautomator.apk')
    time.sleep(5)
    install_apk('./app-uiautomator-test.apk')
    time.sleep(5)
    os.system("adb -s " + device_id + " push bundle.jar /data/local/tmp")
    time.sleep(2)
    os.system("adb -s " + device_id + " push uiautomator-stub.jar /data/local/tmp")
    time.sleep(2)

def info():
    base = str(base_version).split(".")[-1]
    udisk = str(udisk_version).split(".")[-1]
    target = str(target_version).split(".")[-1]
    email = str(email_receiver).split("@")[-2]
    return  (base,udisk,target,email)

def getnowtime():
    now = int(round(time.time() * 1000))
    now02 = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now / 1000))
    return now02

def adb_cmd(cmd):
    command = os.system(cmd)
    time.sleep(3)

    if command == 0:
        return True
    else:
        logger.info("Please Check adb command format")
        return False

def ser_get():
    ser_list = list(serial.tools.list_ports.comports())
    print(ser_list)
    for port in ser_list:
        if str(port).find('USB') != -1 and str(port[0]).find(ser_num) != -1:
            logger.info("Check current can be used port is " + ser_num)
            return ser_num
            break
    else:
        logger.info("Can not check the serial port you connected")

def ser_open():
    ser.port = ser_get()
    ser.baudrate = int(115200)
    ser.bytesize = int(8)
    ser.stopbits = int(1)
    ser.parity = 'N'
    try:
        ser.open()
        logger.info("port can be opened")
        return True
    except:
        logger.info("port can not be opened")
        return None

def ser_close():
    logger.info("closed port.....")
    try:
        ser.close()
    except:
        pass

def check_ser():
    strdata = ''
    if ser.isOpen():
        pass
    else:
        ser_open()

def get_currentSystemVersion():
    adb_usb()
    currentSystemVersion = os.popen("adb -s " + device_id + " shell getprop ro.build.software.version").read().rstrip()
    time.sleep(5)
    return currentSystemVersion

def get_product_name():
    adb_usb()
    product_name = os.popen("adb -s " + device_id + " shell getprop ro.build.product").read().rstrip()
    return product_name

def get_settingsBtn(btn):
    adb_usb()
    for i in range(10):
        os.popen(
            "adb -s " + device_id + " shell am start -n com.android.tv.settings/com.android.tv.settings.MainSettings")
        time.sleep(3)
        if tv(text=btn).exists:
            return True
    else:
        logger.info("Can not find settings button in Android TV home page,please check MiTV condition.....")

def isBootComplete():
    logger.info("Current is isBootComplete function")
    for count_sleep in range(30):
        bootFlag = os.popen("adb -s " + device_id + " shell getprop dev.bootcomplete").read().rstrip()
        time.sleep(5)
        if bootFlag != '1':
            logger.info("is boot mode,please waitting")
            time.sleep(60)
        else:
            logger.info("Device boot mode complete")
            break
    else:
        logger.info("Device boot not complete,please check device condition")
        return False

def adb_usb():
    logger.info("adb monitor start")
    os.popen("adb devices")
    time.sleep(5)
    for count in range(0, 500):
        time.sleep(1)
        if os.popen("adb -s " + device_id + " get-state").read().find("device") != -1:
            logger.info("device connected seccessfull")
            time.sleep(3)
            logger.info("make device root")
            os.popen("adb -s " + device_id + " root")
            time.sleep(3)
            break
        elif os.popen("adb -s " + device_id + " get-state").read().find("recovery") != -1:
            logger.info("Device is in flash mode,please wait.... ")
            time.sleep(60)
        else:
            time.sleep(5)
        if count == 499:
            logger.info("try 500 times, device maybe is off or stopping recovery mode")
            return False

def get_mboot_flag():
    product_name = get_product_name()
    if product_name.find("tarzan") != -1 or product_name.find("croods") != -1:
        key_word = " M7632 "
    elif product_name.find("machuca")!= -1 or product_name.find("nino")!= -1:
        key_word = " M7322 "
    else:
        logger.info("Current product is not adapted .....")
        sys.exit()
    return key_word

def cu_flash():
    global ismboot
    get_data = ''
    check_ser()
    ser.write('\n\n')
    time.sleep(0.5)
    ser.write("reboot" + '\n')
    while True:
        ser.write('\n')
        time.sleep(0.01)
        if ismboot.find('Yes') != -1:
            ser.write("cu")
            time.sleep(0.01)
            ser.write('\n')
            logger.info("input cu command successfully")
            break
    logger.info("Device is executing CU flash")
    time.sleep(30)
    boot = isBootComplete()
    if boot == False:
        return boot_flag
    else:
        pass

    ismboot = "No"
    time.sleep(1)
    read_meminfo()
    time.sleep(5)
    adb  = adb_usb()
    if adb == False:
        return adb_flag
    else:
        pass

def is_cu_flash():
    cu_result = cu_flash()
    if cu_result == adb_flag or cu_result == boot_flag:
        return cu_result

    cu_version = get_currentSystemVersion()
    if cu_version.find(base_version) != -1:
        logger.info("####  Current version is " + cu_version + " CU Flash succesfully  ####")
        time.sleep(3)
        return True
    else:
        logger.info("####  CU Flash is failed  ####")
        return False

def is_formatedata():
    flage = str(formate_data)
    pattern = ".{4}-.{4}"

    adb_usb()
    product_name = os.popen("adb -s " + device_id + " shell getprop ro.build.product").read().rstrip()
    updatefile_name = "xiaomi_update-" + str(product_name)

    usb_path0 = os.popen("adb -s " + device_id + " shell ls /storage/").read().rstrip()
    usb_name = re.search(pattern,usb_path0).group()
    usb_path = "/storage/"+usb_name

    if flage.find('1') != -1 :
        os.popen("adb -s " + device_id + " pull " + str(usb_path) + "/" + str(updatefile_name) + " " + os.getcwd())

        with open(updatefile_name,"r") as f:
            lines = f.readlines()
        with open("tmp.txt","w") as f1:
            for line in lines:
                f1.write(line.replace("--format_data","").strip())
        f.close()
        f1.close()

        with open("tmp.txt","r+") as f2:
            tmp_data = f2.read()
        with open(updatefile_name,"w") as f3:
                f3.write(tmp_data)
        f3.close()
        os.remove("tmp.txt")

        os.popen("adb -s " + device_id + " push " + os.getcwd() + "\\" + updatefile_name + " " + usb_path)
        time.sleep(10)
    elif flage.find('0') != -1:
        logger.info("Start Udisk ota is format data.....")
    else:
        logger.info("format data value is error in Config.ini")
        sys.exit()

def udisk_flash():
    is_formatedata()
    time.sleep(5)
    logger.info("Device start udisk ota ,reboot recovery .....")
    os.popen("adb -s " + device_id + " shell reboot recovery")
    time.sleep(15)

    _adb = adb_usb()
    if _adb == False:
        return adb_flag
    else:
        pass
    time.sleep(120)
    read_meminfo()
    time.sleep(1)

def is_enter_system(btn):
    time.sleep(20)
    btn_exist = get_settingsBtn(btn)
    if (btn_exist):
        logger.info("Find " + btn + " button,enter TV system successfully....")
        return True
    else:
        return False

def is_usdisk_flash(btn,i):
    udisk_result = udisk_flash()
    if udisk_result == adb_flag:
        return adb_flag

    udisk_ota_version = get_currentSystemVersion()
    if udisk_ota_version.find(udisk_version) != -1:
        logger.info("####  udisk ota is successfully,current version is " + udisk_version + "  ####")
        if is_enter_system(btn):
            return True
        else:
            return enter_system_flag
    else:
        logger.info("#### udisk ota is failed ####")
        return False

def ota_UpdateLog(f2):
    logger.info("Get system update failed log , please wait....")

    adb_usb()
    update_log = 'ota_UpdateFail'

    if os.path.isdir(str(result_dir)):
        os.mkdir(os.path.join(result_dir, update_log + str(f2)))
        os.popen(
            "adb -s " + device_id + " pull /data/misc/logd " + str(result_dir) + "/" + update_log + str(f2) + "/logd")
        time.sleep(5)
        # os.popen("adb -s " + device_id + " bugreport > " + str(result_dir) + "/" + update_log +str(f2) + "/bugreport.txt")
        time.sleep(5)
        os.popen("adb -s " + device_id + " pull /cache/recovery " + str(result_dir) + "/" + update_log + str(
            f2) + "/recovery")
        time.sleep(5)

def online_Update():
    logger.info("Start System update online.....")
    btn_id = "com.google.android.gms:id/action_button"

    for updatePage in range(30):
        adb_cmd("adb -s " + device_id + " shell am start -n com.google.android.gms/.update.SystemUpdatePanoActivity")
        time.sleep(10)
        try:
            if tv(resourceId=btn_id).exists:
                action_btn = tv(resourceId=btn_id)
                action_btn_text = action_btn.info[u'text']
                if action_btn_text in ["Check for update", "Retry download"]:
                    print("click update button")
                    action_btn.click()
                    time.sleep(60)
                    logger.info("Check the latest version ")
                elif action_btn_text in ["Download","Retry download"]:
                    print("click download button")
                    action_btn.click()
                    logger.info("Find the latest version,downloading")
                    time.sleep(120)
                elif action_btn_text in ["Pause"]:
                    logger.info("The version is now being downloaded. ")
                    time.sleep(120)
                elif action_btn_text in ["Restart now"]:
                    action_btn.click()
                    logger.info("The download is complete and restart the update system.")
                    time.sleep(120)

                    online_adb = adb_usb()
                    time.sleep(10)
                    read_meminfo()
                    time.sleep(1)
                    if online_adb == False:
                        return adb_flag
                    else:
                        return True
                else:
                    time.sleep(3)
                    logger.info("unknow button:%s" % action_btn_text)
                    continue
            else:
                logger.info("can not find upgrade button.")
        except:
            rpc_err = traceback.format_exc()
            if "RPC server not started!" in rpc_err:
                try:
                    tv.server.stop()
                    time.sleep(5)
                    tv.server.start()
                except:
                    pass
            else:
                logger.info("following EXCEPTION:\n")
                logger.info(rpc_err)
    else:
        time.sleep(5)
        logger.info("OTA package check failed,Restart MiTV now.....")
        os.popen("adb -s " + device_id + " shell reboot")
        adb_usb()
        time.sleep(10)

def is_online_Update():
    online_update_result = online_Update()
    for __a in range(5):
        if online_update_result == True:
            return True
        elif online_update_result ==adb_flag:
            logger.info("Check device fail ,after OTA package download finished and restart devices....")
            return adb_flag
        else:
            logger.info("OTA package check failed,Please check MiTV network connection....")
            return network_error_flag

def read_meminfo():
    print("Reading memory data with using serial tool,waitting.... ")
    with open('mem_command.txt', 'r') as mem_f:
        mem_lines = mem_f.readlines()
        for line in mem_lines:
            check_ser()
            ser.write('\n')
            time.sleep(0.5)
            ser.write('su' + '\n')
            time.sleep(0.5)
            ser.write(line)
            time.sleep(15)
        mem_f.close()
    print ("Reading data with using serial tool finish")

def read_ser_data(mboot_flag):
    global ismboot
    check_ser()
    while True:
        try:
            if ser.inWaiting() != 0:
                recv = ser.readline()
                if recv.find(mboot_flag) != -1:
                    ismboot = 'Yes'
                yield recv
        except exceptions as e:
            logger.info(e)

def write_ser_data(mboot_flag):
    logger.info("Write serial data")
    while True:
        read_ser_log = read_ser_data(mboot_flag).next()
        with open(ser_log, 'a+') as f:
            try:
                f.write(read_ser_log)
            except Exception as e:
                print(e)
        f.close()

def sendEmail():
    to_list = str(email_receiver).split(',')
    cc_list = ['xiaopanpan@xiaomi.com']

    # Charset.add_charset('utf-8', Charset.QP, Charset.QP)
    # html格式的文件名称一定不能为index,否则会报错
    product_name = get_product_name()
    html_content = open(result_dir + '/' + str(device_id) + "_switch-version.html", 'rb').read()
    subject = "[" + str(product_name) + "] OTA Stress report"
    to_list = ', '.join(to_list)
    cc_list = ', '.join(cc_list)

    msg = {
        "token": "9XWtdUAF8Y@xiaomi.com",
        "subject": subject,
        "tos": to_list,
        "content": html_content,
        "html": True,
        "ccs": cc_list
    }
    files = {'attachFiles': ('report.html', html_content)}
    for i in range(3):
        send = requests.post('https://t.mioffice.cn/mailapi/mail', data=msg, files=files)
        send_result = send.json()
        if send_result["status"] == 'success':
            logger.info(json.dumps(send_result, encoding='utf-8', ensure_ascii=False, indent=4))
            break
        else:
            time.sleep(10)
    else:
        logger.info("Report mail send failed 3 times.")
        logger.info(json.dumps(send_result, encoding='utf-8', ensure_ascii=False, indent=4))

def start():
    data = info()
    now_time = getnowtime()
    report = open(result_dir + '/' + str(device_id) + "_switch-version.html", 'w')
    report.write("<html><body><p>Product："+ str(get_product_name()) + "</p><p> Tester：" + str(data[3]) + "</p><p>StartTime："+ str(now_time) +
                 "</p><table border=1 cellspacing='0px' cellpadding='0px' width='760px'><tr height='35px'><td align='center'>Times</td> <td align='center'>cu_version:" + str(data[0]) + "</td> <td align='center'>udisk_version:" + str(data[1])+ "</td> <td align='center'>ota_version:" + str(data[2]) + "</td><td align='center'>comment</td></tr>\n")
    report.close()

    for i in range(1,300):
        result_dict={ }
        btn = 'Network & Internet'

        result_dict["times"] = i
        report = open(result_dir + '/' + str(device_id) + "_switch-version.html", 'a+')
        report.write("<tr height='35px'><td align='center'>" + str(result_dict['times'])+ "</td>")

        system_version = get_currentSystemVersion()
        if (system_version.find(base_version) != -1):
            logger.info(
                "####  Current version is base_version:" + system_version + " ,Start Udisk flash  ####\n")
            logger.info ("Time:" + str(getnowtime()))
            time.sleep(5)
            result_dict["cu_result"]="pass"
            report.write("<td align='center'>"+str(result_dict["cu_result"])+"</td>")

        else:
            if (system_version.find(target_version) != -1):
                logger.info(
                    "####  Current version is target version " + system_version + " ,Start CU Flash  ####")
            else:
                logger.info(
                    "####  Current version is " + system_version + ",Start CU Flash  ####")
            logger.info("Time:" + str(getnowtime()))
            time.sleep(3)

            #cu flash
            _cu = is_cu_flash()
            if _cu==True:
                result_dict["cu_result"]="Pass"
                report.write("<td align='center'>"+str(result_dict["cu_result"])+"</td>")
            elif _cu == adb_flag or _cu == boot_flag:
                result_dict["cu_result"] = "Fail"
                result_dict["udisk_result"] = None
                result_dict["ota_result"] = None
                result_dict["comment"] = adb_flag
                report.write("<td align='center'>" + str(result_dict["cu_result"]) + "</td> <td align='center'>" + str(result_dict["udisk_result"]) + "</td> <td align='center'>" + str(result_dict["ota_result"]) + "</td><td align='center'>" + str(result_dict["comment"])+ "</td></tr></table></body></html>")
                report.close()
                sendEmail()
                sys.exit()
            else:
                result_dict["cu_result"] = "Fail"
                result_dict["udisk_result"] = None
                result_dict["ota_result"] = None
                result_dict["comment"] = "unknow error"
                report.write("<td align='center'>"+str(result_dict["cu_result"])+"</td> <td align='center'>"+str(result_dict["udisk_result"])+"</td> <td align='center'>" + str(result_dict["ota_result"])+"</td></tr> </table></body></html>")
                report.close()
                sendEmail()
                sys.exit()

        # Udisk flash
        _udisk = is_usdisk_flash(btn,i)
        if _udisk==True:
            result_dict["udisk_result"]="Pass"
            report.write("<td align='center'>" + str(result_dict["udisk_result"]) + "</td>" )
        elif _udisk==adb_flag or _udisk==enter_system_flag:
            result_dict["udisk_result"] = "Fail"
            result_dict["ota_result"] = None
            result_dict["comment"] = _udisk
            report.write("<td align='center'>"+str(result_dict["udisk_result"])+"</td> <td align='center'>" + str(result_dict["ota_result"])+ "</td><td align='center'>" + str(result_dict["comment"]) +"</td></tr></table></body></html>")
            report.close()
            sendEmail()
            sys.exit()
        else:
            result_dict["udisk_result"] = "Fail"
            result_dict["ota_result"] = None
            result_dict["comment"] = "unkonw error"
            report.write("<td align='center'>" + str(result_dict["udisk_result"]) + "</td> <td align='center'>" + str(result_dict["ota_result"]) + "</td><td align='center'>" + str(result_dict["comment"]) + "</td></tr></table></body></html>")
            report.close()
            sendEmail()
            sys.exit()

        time.sleep(60)
        install_uiautomator()
        time.sleep(5)

        #system update
        _update = is_online_Update()
        if _update==True:
            enter_system = is_enter_system(btn)
            if enter_system == True:
                result_dict["ota_result"] = "Pass"
                result_dict["comment"] = None
                report.write("<td align='center'>" + str(result_dict["ota_result"]) + "</td><td align='center'>"+ str(result_dict["comment"]) + "</td></tr>")
            else:
                result_dict["ota_result"] = "Fail"
                result_dict["comment"] = enter_system_flag
                report.write("<td align='center'>" + str(result_dict["ota_result"]) + "</td><td align='center'>" + str(result_dict["comment"]) + "</td></tr></table></body></html>")
                report.close()
                sendEmail()
                sys.exit()
        elif _update == network_error_flag or _update == adb_flag:
            result_dict["ota_result"] = "Fail"
            result_dict["comment"] = _update
            report.write("<td align='center'>" + str(result_dict["ota_result"]) + "</td><td align='center'>" + str(result_dict["comment"]) + "</td></tr></table></body></html>")
            report.close()
            sendEmail()
            sys.exit()

    report = open(result_dir + '/' + str(device_id) + "_switch-version.html", 'a+')
    report.write("</table></body></html>")
    report.close()
    sendEmail()

if __name__ == '__main__':
    #Settings ota stress log print
    logfile = "log_" + time.strftime("%Y%m%d%H%M%S") + ".txt"
    os.mkdir(os.getcwd() + "/testResult_" + time.strftime("%Y%m%d%H%M%S"))
    result_dir = str(os.getcwd() + "/testResult_" + time.strftime("%Y%m%d%H%M%S"))
    ser_log = result_dir + "/" + device_id + "serial_log.log"

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(str(result_dir) + "/mitv_otaScripts_" + logfile)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)

    logger.addHandler(handler)
    logger.addHandler(console)

    #main function
    ismboot = 'No'
    _monitor_adb = monitor_adb()
    mboot_flag = get_mboot_flag()
    ser = serial.Serial(ser_num,115200, timeout=5)
    t = threading.Thread(target = write_ser_data,args = (mboot_flag,)).start()
    start()
   




































































