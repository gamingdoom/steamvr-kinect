from openni import nite2 as nt
from openni import openni2
from sys import platform
import socket
import sys
import time
import math
from scipy.spatial.transform import Rotation as R

def main():

    roles = ["TrackerRole_Waist", "TrackerRole_RightFoot", "TrackerRole_LeftFoot"]

    initSteamVR(roles)

    nt.initialize("lib")
    openni2.initialize()

    dev = openni2.Device.open_any()

    userTracker = nt.UserTracker(dev)

    while True:
        frame = userTracker.read_frame()

        if frame.users:
            for user in frame.users:
                if user.is_new():
                    print("New human detected! Calibrating...")
                    userTracker.start_skeleton_tracking(user.id)
                elif user.skeleton.state == nt.SkeletonState.NITE_SKELETON_TRACKED:
                    lFoot = user.skeleton.joints[nt.JointType.NITE_JOINT_LEFT_FOOT]
                    rFoot = user.skeleton.joints[nt.JointType.NITE_JOINT_RIGHT_FOOT]

                    lHip = user.skeleton.joints[nt.JointType.NITE_JOINT_RIGHT_HIP]
                    rHip = user.skeleton.joints[nt.JointType.NITE_JOINT_LEFT_HIP]

                    head = user.skeleton.joints[nt.JointType.NITE_JOINT_HEAD]
                    
                    # Average left and right hip
                    waist = nt.c_api.NiteSkeletonJoint()

                    waist.position = nt.Point3f(*tuple((left + right)/2 for left, right in zip((lHip.position.x, lHip.position.y, lHip.position.z), (rHip.position.x, rHip.position.y, rHip.position.z))))
                    waist.orientation = lHip.orientation

                    updatePose(waist, rFoot, lFoot, head)

                    
    nt.unload()
    openni2.unload()

def updatePose(waist, rFoot, lFoot, head):
    getDevicePose = sendToSteamVR("getdevicepose 0")

    hmdPos = [float(getDevicePose[3]), float(getDevicePose[4]), float(getDevicePose[5])]

    steamvrHeadPos = [pos - offset for pos, offset in zip(hmdPos, [0, 0, 0])]
    
    offset = tuple(h - svrh for h, svrh in zip((head.position.x * 0.001, head.position.y * 0.001, head.position.z * -0.001), steamvrHeadPos))

    rFoot.orientation = waist.orientation
    lFoot.orientation = waist.orientation

    for joint, id, extraOffset in [(rFoot, 2, [0, -0.5, 0]), (lFoot, 1, [0, -0.5, 0]), (waist, 0, [0, -0.25, 0])]:
        loc = (joint.position.x, joint.position.y, joint.position.z)
        loc = tuple(n * 0.001 for n in loc)
        loc = tuple(l - o for l, o in zip(loc, offset))
        loc = tuple(l + o for l, o in zip(loc, extraOffset))
        
        joint.orientation.w = joint.orientation.w if joint.orientation.w != 0 else 1
        # Rotate 180°
        #rotQuat = R.as_quat((joint.orientation.w, joint.orientation.x, joint.orientation.y, joint.orientation.z)) * R.from_euler("XYZ", (math.radians(180), 0, 0), degrees=True)
        rotQuat = (joint.orientation.w, joint.orientation.x, joint.orientation.y, joint.orientation.z)

        sendToSteamVR(f"updatepose {id} {loc[0]} {loc[1]} {loc[2] * -1} {rotQuat[0]} {rotQuat[1]} {rotQuat[2]} {rotQuat[3]} 0.02 0.8")# 0.8")


# Inspired by https://github.com/ju1ce/Mediapipe-VR-Fullbody-Tracking/blob/main/bin/backends.py
def initSteamVR(roles):
    if sendToSteamVR("numtrackers"):
        print(sendToSteamVR("numtrackers"))

        # Smoothing (smoothing, additional smoothing)
        sendToSteamVR(f"settings 50 0.5 0.9")
                      
        for i, role in enumerate(roles):
            print(sendToSteamVR(f"addtracker MPTracker{i} {role}"))

        
    else:
        print("Couldn't connect to SteamVR. Exiting")
        exit(1)

    return

# From https://github.com/ju1ce/Mediapipe-VR-Fullbody-Tracking/blob/main/bin/helpers.py
def sendToPipe(text):
    if platform.startswith('win32'):
        pipe = open(r'\\.\pipe\ApriltagPipeIn', 'rb+', buffering=0)
        some_data = str.encode(text)
        some_data += b'\0'
        pipe.write(some_data)
        resp = pipe.read(1024)
        pipe.close()
    elif platform.startswith('linux'):
        client = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        client.connect("/tmp/ApriltagPipeIn")
        some_data = text.encode('utf-8')
        some_data += b'\0'
        client.send(some_data)
        resp = client.recv(1024)
        client.close()
    else:
        print(f"Unsuported platform {sys.platform}")
        raise Exception
    return resp

# From https://github.com/ju1ce/Mediapipe-VR-Fullbody-Tracking/blob/main/bin/helpers.py
def sendToSteamVR_(text):
    #Function to send a string to my steamvr driver through a named pipe.
    #open pipe -> send string -> read string -> close pipe
    #sometimes, something along that pipeline fails for no reason, which is why the try catch is needed.
    #returns an array containing the values returned by the driver.
    try:
        resp = sendToPipe(text)
    except:
        return ["error"]

    string = resp.decode("utf-8")
    array = string.split(" ")
    
    return array

# From https://github.com/ju1ce/Mediapipe-VR-Fullbody-Tracking/blob/main/bin/helpers.py
# See https://github.com/ju1ce/Simple-OpenVR-Bridge-Driver for commands
def sendToSteamVR(text, num_tries=10, wait_time=0.1):
    # wrapped function sendToSteamVR that detects failed connections
    ret = sendToSteamVR_(text)
    i = 0
    while "error" in ret:
        print("INFO: Error while connecting to SteamVR. Retrying...")
        time.sleep(wait_time)
        ret = sendToSteamVR_(text)
        i += 1
        if i >= num_tries:
            return None # probably better to throw error here and exit the program (assert?)
    
    return ret

if __name__ == "__main__":
    main()