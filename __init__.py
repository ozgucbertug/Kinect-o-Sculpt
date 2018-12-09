from multiprocessing import Process, Queue

from kinectRuntime import KinectRuntime as kinect
from openGLRuntime import OpenGLRuntime as openGL

def kinectRun(kToM, kToGL):
    kinectScreen = kinect(kToM, kToGL)
    kinectScreen.run()

def openGLRun(kToGL, verts):
    openGLScreen = openGL(kToGL, verts)
    openGLScreen.run()

def run():
    globalRunning = True
    openGLRunning = False

    kToM = Queue()
    kToGL = Queue()

    kinectProcess = Process(target=kinectRun, args = (kToM, kToGL,))
    kinectProcess.start()
    
    while globalRunning == True:

        kinectToMain = kToM.get()
        verts = kinectToMain[len(kinectToMain) - 1]
        if kinectToMain[1] == True and len(verts) != 0:
            if openGLRunning == False:
                openGLRunning = True
                openGLProcess = Process(target=openGLRun, args = (kToGL, verts,))
                openGLProcess.start()

        else:
            if openGLRunning == True:
                openGLRunning = False
                openGLProcess.terminate()

        if kinectToMain[0] == True:
            kinectProcess.terminate()
            if openGLRunning == True:
                openGLProcess.terminate()
            globalRunning = False

def main():
    
    runProcess = Process(target=run, args = ())

    runProcess.start()
    runProcess.join()
    print("bye!")

if __name__ == '__main__':
    main()
