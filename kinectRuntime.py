from pykinect2 import PyKinectV2, PyKinectRuntime
from pykinect2.PyKinectV2 import *

import pygame
from pygame.locals import *

import ctypes
import _ctypes
import sys
import os
import math
import time
import datetime
import copy
import random

class KinectRuntime(object):

    def __init__(self, toMain, toGL):
        pygame.init()

        user32 = ctypes.windll.user32        
        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)
        self.width = self.screen_width//2
        self.height = self.screen_height//2
        
        self.frameColor = (231,76,60)
        self.frameColorBlink = (192,57,43)
        self.cursorColor = (39, 174, 96, 200)
        self.cursorColorClosed = (18, 232, 109, 100)
        self.buttonColor = (150,150,150,150)
        self.buttonColorHover = (150,255,150,200)
        self.buttonColorSelect = (255,255,255)
        
        self.sliderColor = (150,150,150)
        self.sliderColorHover = (150,255,150)

        self.buttonWidth = 300
        self.buttonHeight = self.buttonWidth//2
        self.sliderHeight = 150
        self.sliderWidth = self.sliderHeight//3
        self.exitTimer = None
        self.buttonTimers = {"exitButton":None, "settingsButton":None, "button1":None, "button2":None}

        self.cdFinished = False
        self.cdCount = ""
        self.cdTimeStart = None
        self.cdTimeEnd = None

        self.timeSliderRange = (5,15)
        self.timeSlider = 10
        self.timeSliderPos = self.screen_width//2
        self.sectionSliderRange = (1,5)
        self.sectionSlider = 3
        self.sectionSliderPos = self.screen_width//2

        self.lHandPos = (0,self.screen_height//2)
        self.rHandPos = (self.screen_width, self.screen_height//2)
        self.lHandClosed = False
        self.rHandClosed = False

        self.trackedPos = []
        self.verts = []
        self.saved = False
        self.saveCounter = 0

        self.dotR = 40
        self.isRecording = False
        self.startRec = False
        self.runOpenGL = False
        self.startCD = False
        self.states = ["welcome", "settings", "main", "record", "invalid", "preview"]
        self.curState = self.states[0]

        self.gui = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        self.cursor = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        self.alphaSrf = pygame.Surface((self.screen_width, self.screen_height))
        self.alphaSrf.fill((255,255,255))
        self.alphaSrf.set_alpha(150)

        self.tipText = ['Keep your body markers in the frame at all times.',
                   'Larger spaces make better canvas!',
                   "Just don't think about it and let yourself go!",
                   'Higher section per second value makes a higher resolution sculpture',
                   "Don't forget that your feets are also recorded, make use of them!",
                   "Don't forget to save your sculpture!",
                   "Dance to your favorite song and see what happens!",
                  ]
        self.tipIndex = None
        
        self.timeStart = None
        self.timeEnd = None
        self.recTimeStart = None
        self.recTimeEnd = None
        self.gTimer = time.time()
        self.dt = 0

        self.toMain = toMain
        self.toGL = toGL
        self.rotation = [0,0]
        self.rotationStart = None

        # List of pyKinect joints to be recorded.
        self.targetJoints = [PyKinectV2.JointType_Head,
                             PyKinectV2.JointType_ShoulderLeft,
                             PyKinectV2.JointType_ElbowLeft,
                             PyKinectV2.JointType_HandLeft,
                             PyKinectV2.JointType_HipLeft,
                             PyKinectV2.JointType_KneeLeft,
                             PyKinectV2.JointType_FootLeft,
                             PyKinectV2.JointType_FootRight,
                             PyKinectV2.JointType_KneeRight,
                             PyKinectV2.JointType_HipRight,
                             PyKinectV2.JointType_HandRight,
                             PyKinectV2.JointType_ElbowRight,
                             PyKinectV2.JointType_ShoulderRight]

        # Used to manage how fast the screen updates
        self._clock = pygame.time.Clock()

        
        os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"
        self._screen = pygame.display.set_mode((self.screen_width,self.screen_height), pygame.HWSURFACE|pygame.DOUBLEBUF|pygame.NOFRAME, 32)
        pygame.display.set_caption('ocapunam-TP // Kinect')
        
        # Loop until the user clicks the close button.
        self._done = False

        # Kinect runtime object, we want color and body frames 
        self._kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Color | PyKinectV2.FrameSourceTypes_Body)

        # back buffer surface for getting Kinect color frames, 32bit color, width and height equal to the Kinect color frame size
        self.colorFrame = pygame.Surface((self._kinect.color_frame_desc.Width, self._kinect.color_frame_desc.Height), 0, 32)

        # Here we will store skeleton data 
        self._bodies = None
        self.joints = None
        self.colorJoints = None


        # check if user hands are closer than given maximum distance,
        # if so, start a timer.
    def handsTogether(self,maxDistance=200):
        if self.distance(self.lHandPos,self.rHandPos) < maxDistance:
            if self.timeStart == None:
                self.timeStart = time.time()
            return True
        else:
            self.timeStart = None
            self.timeEnd = None
            return False

        
        # check if user has been holding their gesture for given amount of time.
    def startRecording(self, timeWindow=3):
        if self.handsTogether() == True and\
           self.timeStart != None and\
           self.isRecording == False:
            self.timeEnd = time.time()
            if (self.timeEnd - self.timeStart) > timeWindow:
                self.timeStart = None
                self.timeEnd = None
                self.startCD = True
                self.startRec = True
 
    
    def countdown(self, timeWindow=3):
        if self.cdTimeStart == None:
            self.cdTimeStart = time.time()
        self.cdTimeEnd = time.time()
        dt = math.floor(self.cdTimeEnd - self.cdTimeStart)
        curCount = timeWindow - dt
        if curCount <= 0:
            self.cdCount = "Go!"
            if curCount < 0:
                self.cdFinished = True
                self.cdTimeStart = None
                self.cdTimeEnd = None
        else:
            self.cdCount = str(curCount)


    def writeCSV(self):
        now = datetime.datetime.now() 
        dateFormat = '%d%d%d-%d%d_' % (now.year, now.month, now.day, now.hour, now.minute)

        fileName = dateFormat + 'kinect-o-sculpt_save' + str(self.saveCounter) + '.csv'
        csvFile = open(fileName, 'w')
        with csvFile as output:
            for section in self.verts:
                temp = ''
                for joint in section:
                    for pos in joint:
                        temp += str(pos) + ','
                output.write(temp[:-1] + '\n')
                self.saved = True
                self.saveCounter += 1

    def textObject(self, text, font, color):
        textSrf = font.render(text, True, color)
        return textSrf, textSrf.get_rect()

    def drawText(self, text, center, fontSize, color, font = 'OpenSans-Regular.ttf'):
        largeText = pygame.font.Font(font, fontSize)
        textSrf, textRect = self.textObject(text, largeText, color)
        textRect.center = center
        self.gui.blit(textSrf, textRect)

    def remap(self, value, sourceRange, targetRange):
        leftSpan = sourceRange[1] - sourceRange[0]
        rightSpan = targetRange[1] - targetRange[0]

        valueScaled = float(value - sourceRange[0]) / float(leftSpan)

        return targetRange[0] + (valueScaled * rightSpan)

    def record(self, timeWindow = 10, sectionPerSec = 2):
        
        self.recTimeEnd = time.time()
        validRecord = True

        dTime = math.floor(self.recTimeEnd-self.recTimeStart)
        sectionCount = (dTime+1)*sectionPerSec

        if sectionCount > len(self.trackedPos):
            tempRec = []
            for i in range(len(self.targetJoints)):
                curJoint = self.joints[self.targetJoints[i]]
                if curJoint.TrackingState == PyKinectV2.TrackingState_Tracked:
                    curPos = (curJoint.Position.x,
                                 curJoint.Position.y,
                                 curJoint.Position.z)
                    tempRec.append(curPos)
                else:
                    validRecord = False
            if validRecord == True:
                self.trackedPos.append(tempRec)
        if dTime >= timeWindow:
            self.isRecording = False
            if len(self.trackedPos) < (timeWindow * sectionPerSec):
                self.trackedPos = []
                self.runOpenGL = False

            else:
                self.verts = self.trackedPos
                self.runOpenGL = True
                self.trackedPos = []
                self.recTimeStart = None
               
    def distance(self, pos1, pos2):
        return(int(math.sqrt(abs(pos1[0] - pos2[0])**2 + abs(pos1[1] - pos2[1])**2)))

    def drawRecordFrame(self):

        color = self.frameColor
        if math.floor(self.dt)%2 == 1:
            color = self.frameColorBlink
        pygame.draw.rect(self.gui, color, [0,0,self.screen_width,self.screen_height],50)

    def drawSection(self):

        for i in range(len(self.targetJoints)):

                jointA = self.targetJoints[i-1]
                jointB = self.targetJoints[i]
                if self.joints[jointA].TrackingState == PyKinectV2.TrackingState_Tracked and\
                   self.joints[jointB].TrackingState == PyKinectV2.TrackingState_Tracked:
                    pygame.draw.line(self.gui,(120,120,120),
                                     (self.colorJoints[jointA].x, self.colorJoints[jointA].y),
                                     (self.colorJoints[jointB].x, self.colorJoints[jointB].y),
                                     10)
                    pygame.draw.circle(self.gui, self.frameColor,
                                      (int(self.colorJoints[jointA].x), int(self.colorJoints[jointA].y)),
                                       int(self.dotR/self.joints[jointA].Position.z))

    def rectHover(self, rect, joint):
        if (rect[0]) < joint[0] < ((rect[0] + rect[2])) and\
           (rect[1]) < joint[1] < ((rect[1] + rect[3])):
            return True
        return False


    def rectClick(self, rect):
        if (self.rectHover(rect, self.rHandPos) and self.rHandClosed) or\
           (self.rectHover(rect, self.lHandPos) and self.lHandClosed):
            return True
        return False

 
    def circleHover(self, circle, radius, joint):
        if self.distance(circle, joint) <= radius:
            return True
        else:
            return False 

    def circleClick(self, circle, radius):
        if (self.circleHover(circle, radius, self.rHandPos) and self.rHandClosed) or\
           (self.circleHover(circle, radius, self.lHandPos) and self.lHandClosed):
            return True
        else:
            return False

    def circleSelect(self, circle, radius, timer, timeWindow = 1):
        if self.circleClick(circle, radius) == True:
            if self.buttonTimers[timer] == None:
                self.buttonTimers[timer] = time.time()
            timeEnd = time.time()

            dt = timeEnd - self.buttonTimers[timer]
            if dt > 0:
                tempAngle = math.pi * 2 * (dt/timeWindow)
                pygame.draw.arc(self.gui,self.buttonColorSelect,(circle[0]-radius, circle[1]-radius,radius*2,radius*2),math.pi/2,math.pi/2 + tempAngle,10)
                #pygame.draw.circle(self.gui, self.buttonColorSelect, circle, radius)
            if dt > timeWindow:
                self.buttonTimers[timer] = None
                return True
        else:
            self.buttonTimers[timer] = None
        return False
    
    def rectSlide(self,rect,sliderPos,offset):
        tempRect = copy.copy(rect)
        tempRect[0] -= self.sliderWidth*2
        tempRect[2] += self.sliderWidth*4
        if self.rectHover(tempRect, self.rHandPos):
            if self.rHandClosed:
                if self.rHandPos[0] < offset:
                    sliderPos = offset
                elif self.rHandPos[0] > self.screen_width - offset:
                    sliderPos = self.screen_width - offset
                else:
                    sliderPos = self.rHandPos[0]
        elif self.rectHover(tempRect, self.lHandPos):
            if self.lHandClosed:
                if self.lHandPos[0] < offset:
                    sliderPos = offset
                elif self.lHandPos[0] > self.screen_width - offset:
                    sliderPos = self.screen_width - offset
                else:
                    sliderPos = self.lHandPos[0]        
        return(sliderPos)

    def rotateGL(self):
        if self.rHandClosed:
            if self.rotationStart == None:
                self.rotationStart = (self.rHandPos[0],self.rHandPos[1])
            self.rotation[0] += (self.rotationStart[0] - self.rHandPos[0])
            self.rotation[1] += (self.rotationStart[1] - self.rHandPos[1])
            self.rotationStart = (self.rHandPos[0],self.rHandPos[1])
        elif self.lHandClosed:
            if self.rotationStart == None:
                self.rotationStart = (self.lHandPos[0],self.lHandPos[1])
            self.rotation[0] += (self.rotationStart[0] - self.lHandPos[0])
            self.rotation[1] += (self.rotationStart[1] - self.lHandPos[1])
            self.rotationStart = (self.lHandPos[0],self.lHandPos[1])
        else:
            self.rotationStart = None

    def drawCursor(self):
        if self.joints != None:
            if self.joints[PyKinectV2.JointType_HandRight].TrackingState == PyKinectV2.TrackingState_Tracked:
                rColor = self.cursorColor
                if self.rHandClosed:
                    rColor = self.cursorColorClosed
                pygame.draw.circle(self.cursor, rColor, self.rHandPos, int(self.dotR/self.joints[PyKinectV2.JointType_HandRight].Position.z))
            if self.joints[PyKinectV2.JointType_HandLeft].TrackingState == PyKinectV2.TrackingState_Tracked:
                lColor = self.cursorColor
                if self.lHandClosed:
                    lColor = self.cursorColorClosed
                pygame.draw.circle(self.cursor, lColor, self.lHandPos, int(self.dotR/self.joints[PyKinectV2.JointType_HandLeft].Position.z))
    
    def exitButton(self):

        ratio = self.screen_height/self.screen_width
        offset = 350
        cButton = (self.screen_width - offset, int(offset*ratio))
        rButton = 50


        if self.circleHover(cButton, rButton, self.lHandPos) or\
           self.circleHover(cButton, rButton, self.rHandPos):
            color = self.frameColorBlink
        else:
            color = self.frameColor
        
        pygame.draw.circle(self.gui, color, cButton, rButton)

        if self.circleSelect(cButton, rButton, "exitButton"):
                self._done = True
        self.drawText("X", cButton, 60, (255,255,255))

    def settingsButton(self):

        ratio = self.screen_height/self.screen_width
        offset = 350
        cButton = (offset, int(offset*ratio))
        rButton = 50


        if self.circleHover(cButton, rButton, self.lHandPos) or\
           self.circleHover(cButton, rButton, self.rHandPos):
            color = self.buttonColorHover
        else:
            color = self.buttonColor
        
        pygame.draw.circle(self.gui, color, cButton, rButton)

        if self.circleSelect(cButton, rButton, "settingsButton"):
            self.curState = self.states[1]
            
        self.drawText('⚙', cButton, 60, (255,255,255), 'Symbola.ttf')

    def welcomeState(self):
        self.gui = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        self.cursor = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)

        
        cButton = (self.screen_width//2, self.screen_height//2)
        rButton = 200


        if self.circleHover(cButton, rButton, self.lHandPos) or\
           self.circleHover(cButton, rButton, self.rHandPos):
            color = self.buttonColorHover
        else:
            color = self.buttonColor
        
        pygame.draw.circle(self.gui, color, cButton, rButton)

        if self.circleSelect(cButton, rButton, "button1"):
                self.curState = self.states[1]
        self.drawText("Start", cButton, 60, (255,255,255))

        textOffset = (self.screen_height//2 - rButton)//2
        textPos = (self.screen_width//2, textOffset)

        self.drawText("Kinect-o-Sculpture", textPos, 150, (255,255,255))
        self.drawCursor()
    
    def settingsState(self):
        self.gui = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        self.cursor = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)

        self.exitButton()
        self.drawCursor()

        sliderLineYOffset = self.sliderHeight*3//2
        sliderLineXOffset = 400
        cButton = (self.screen_width//2, self.screen_height//2)
        rButton = 100


        if self.circleHover(cButton, rButton, self.lHandPos) or\
           self.circleHover(cButton, rButton, self.rHandPos):
            color = self.buttonColorHover
        else:
            color = self.buttonColor
        
        pygame.draw.circle(self.gui, color, cButton, rButton)

        if self.circleSelect(cButton, rButton, "button1"):
                self.curState = self.states[2]


        pygame.draw.line(self.gui,self.sliderColor,
                        (sliderLineXOffset, self.screen_height//2 - sliderLineYOffset),
                        (self.screen_width - sliderLineXOffset, self.screen_height//2 - sliderLineYOffset),
                        10)
        pygame.draw.line(self.gui,self.sliderColor,
                        (sliderLineXOffset, self.screen_height//2 + sliderLineYOffset),
                        (self.screen_width - sliderLineXOffset, self.screen_height//2 + sliderLineYOffset),
                        10)
        
        sliderRange = (sliderLineXOffset, self.screen_width - sliderLineXOffset)


        tSlider = [self.timeSliderPos - self.sliderWidth//2,
                   self.screen_height//2 - sliderLineYOffset - self.sliderHeight//2,
                   self.sliderWidth, self.sliderHeight]
        tBBox = copy.copy(tSlider)
        tBBox[0] -= self.sliderWidth*2
        tBBox[2] += self.sliderWidth*4

        if self.rectClick(tBBox):
            color = self.buttonColorHover
        else:
            color = self.buttonColor

        self.timeSliderPos = self.rectSlide(tSlider, self.timeSliderPos, sliderLineXOffset)
        self.timeSlider = round(self.remap(self.timeSliderPos,sliderRange, self.timeSliderRange))

        pygame.draw.rect(self.gui,color,tSlider)

        bSlider = [self.sectionSliderPos - self.sliderWidth//2,
                   self.screen_height//2 + sliderLineYOffset - self.sliderHeight//2,
                   self.sliderWidth, self.sliderHeight]

        bBBox = copy.copy(bSlider)
        bBBox[0] -= self.sliderWidth*2
        bBBox[2] += self.sliderWidth*4
        
        if self.rectClick(bBBox):
            color = self.buttonColorHover
        else:
            color = self.buttonColor

        self.sectionSliderPos = self.rectSlide(bSlider, self.sectionSliderPos, sliderLineXOffset)
        self.sectionSlider = round(self.remap(self.sectionSliderPos,sliderRange, self.sectionSliderRange))
        
        pygame.draw.rect(self.gui,color,bSlider)
        
        
        textOffset = 100

        topTextPos = (self.screen_width//2, tSlider[1] - textOffset)
        bottomTextPos = (self.screen_width//2, bSlider[1] + bSlider[3] + textOffset)

        self.drawText("Record Time", topTextPos, 60, (255,255,255))
        self.drawText("Section Per Second", bottomTextPos, 60, (255,255,255))
        self.drawText("Go!", cButton, 60, (255,255,255))
        self.drawText(str(self.timeSlider), Rect(tSlider).center, 40, (255,255,255))
        self.drawText(str(self.sectionSlider), Rect(bSlider).center, 40, (255,255,255))

    def mainState(self):
        self.gui = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        self.cursor = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)

        self.exitButton()
        self.settingsButton()
        self.drawCursor()

        self.startRecording()
        if self.startCD == True:
            self.countdown()
            self.drawText(self.cdCount, (self.screen_width//2, self.screen_height//2), 300, (255,255,255))

        if self.startRec == False:
            infoTextPos = (self.screen_width//2, self.screen_height//4)
            self.drawText("Keep your hands together to start recording!", infoTextPos, 40, (255,255,255))
            
        if self.cdFinished == True and self.isRecording == False:
            self.isRecording = True
            self.startCD = False
                
        if self.isRecording == True:
            self.cdFinished = False
            self.startRec = False
            self.recTimeStart = time.time()

            self.curState = self.states[3]

    def recordingState(self):
        self.gui = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        self.cursor = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)

        if self.isRecording == True:
            self.record(self.timeSlider, self.sectionSlider)
            self.drawSection()
            self.drawRecordFrame()
        else:
            if self.runOpenGL:
                self.curState = self.states[5]
            else:
                self.tipIndex = random.randint(0,len(self.tipText)-1)
                self.curState = self.states[4]
            

    def invalidState(self):
        self.gui = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        self.cursor = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        self.exitButton()
        self.drawCursor()

        cButton = (self.screen_width//2, self.screen_height//2)
        rButton = 100


        if self.circleHover(cButton, rButton, self.lHandPos) or\
           self.circleHover(cButton, rButton, self.rHandPos):
            color = self.buttonColorHover
        else:
            color = self.buttonColor
        
        pygame.draw.circle(self.gui, color, cButton, rButton)

        self.drawText("Back", cButton, 60, (255,255,255))

        infoTextPos = (self.screen_width//2, self.screen_height//4)
        infoText = "Unfortunately your recording was invalid"
        self.drawText(infoText, infoTextPos, 40, self.frameColorBlink)

        if self.circleSelect(cButton, rButton, "button1"):
                self.curState = self.states[2]

        tipTextPos = (self.screen_width//2, 3*(self.screen_height//4))

        self.drawText("Tip " + str(self.tipIndex) + ":" + self.tipText[self.tipIndex], tipTextPos, 40, (0,0,0))


    def previewState(self):
        self.gui = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        self.cursor = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        self.exitButton()
        self.rotateGL()
        self.drawCursor()

        cButton1 = ((self.screen_width*3)//4, self.screen_height//2)
        rButton1 = 100
        

        if self.circleHover(cButton1, rButton1, self.lHandPos) or\
            self.circleHover(cButton1, rButton1, self.rHandPos) or\
            self.saved == True:
            color = self.buttonColorHover
        else:
            color = self.buttonColor
        
        pygame.draw.circle(self.gui, color, cButton1, rButton1)

        if self.saved == False:
            if self.circleSelect(cButton1, rButton1, "button1"):
                self.writeCSV()
        

        self.drawText("Save", cButton1, 60, (255,255,255))

        cButton2 = ((self.screen_width)//4, self.screen_height//2)
        rButton2 = 100

        if self.circleHover(cButton2, rButton2, self.lHandPos) or\
           self.circleHover(cButton2, rButton2, self.rHandPos):
            color = self.buttonColorHover
        else:
            color = self.buttonColor
        
        pygame.draw.circle(self.gui, color, cButton2, rButton2)

        if self.circleSelect(cButton2, rButton2, "button2"):
            self.runOpenGL = False
            self.curState = self.states[2]
            self.saved = False

        self.drawText("Back", cButton2, 60, (255,255,255))


    def draw_color_frame(self, frame, target_surface):
        target_surface.lock()
        address = self._kinect.surface_as_array(target_surface.get_buffer())
        ctypes.memmove(address, frame.ctypes.data, frame.size)
        del address
        target_surface.unlock()
        
    def blitFrame(self, frame, targetH):
            surface_to_draw = pygame.transform.scale(frame, (self._screen.get_width(), targetH));
            self._screen.blit(surface_to_draw, (0,0))
            surface_to_draw = None

    def run(self):
        # -------- Main Program Loop -----------
        while not self._done:
            self.dt += time.time()-self.gTimer
            self.gTimer = time.time()

            # --- Main event loop ---
            for event in pygame.event.get(): # User did something
                if event.type == pygame.QUIT: # If user clicked close
                    self._done = True # Flag that we are done so we exit this loop
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._done = True


            # We have a color frame. Fill out back buffer surface with frame's data 
            if self._kinect.has_new_color_frame():
                frame = self._kinect.get_last_color_frame()
                self.draw_color_frame(frame, self.colorFrame)
                frame = None

            # We have a body frame, so can get skeletons
            if self._kinect.has_new_body_frame():
                self._bodies = self._kinect.get_last_body_frame()

                if self._bodies is not None: 
                    for i in range(self._kinect.max_body_count):
                        body = self._bodies.bodies[i]
                        if not body.is_tracked: 
                            continue
                        else:
                            self.joints = body.joints
                            self.lHandClosed = (body.hand_left_state == PyKinectRuntime.HandState_Closed)
                            self.rHandClosed = (body.hand_right_state == PyKinectRuntime.HandState_Closed)
                            break
                    if self.joints != None:
                        self.colorJoints = self._kinect.body_joints_to_color_space(self.joints)

                        # continiously check for hand position for gesture tracking.
                        if self.joints[PyKinectV2.JointType_HandRight].TrackingState == PyKinectV2.TrackingState_Tracked:
                            self.rHandPos = (int(self.colorJoints[PyKinectV2.JointType_HandRight].x), int(self.colorJoints[PyKinectV2.JointType_HandRight].y))
                        if self.joints[PyKinectV2.JointType_HandLeft].TrackingState == PyKinectV2.TrackingState_Tracked:
                                self.lHandPos = (int(self.colorJoints[PyKinectV2.JointType_HandLeft].x), int(self.colorJoints[PyKinectV2.JointType_HandLeft].y))
                        

            if self.curState == "welcome":
                self.welcomeState()
            elif self.curState == "settings":
                self.settingsState()
            elif self.curState == "main":
                self.mainState()
            elif self.curState == "record":
                self.recordingState()
            elif self.curState == "invalid":
                self.invalidState()
            elif self.curState == "preview":
                self.previewState()
            
            
            # --- copy back buffer surface pixels to the screen, resize it if needed and keep aspect ratio
            # --- (screen size may be different from Kinect's color frame size) 
            hToW = float(self.colorFrame.get_height()) / self.colorFrame.get_width()
            targetH = int(hToW * self._screen.get_width())
            self.blitFrame(self.colorFrame, targetH)
            if self.curState in set(["welcome", "settings", "invalid"]):
                self.blitFrame(self.alphaSrf, targetH)
            self.blitFrame(self.gui, targetH)
            self.blitFrame(self.cursor, targetH)
            pygame.display.update()

            
            # --- Limit to 60 frames per second
            self._clock.tick(60)
            
            self.toMain.put((self._done, self.runOpenGL, self.verts))
            self.toGL.put([self.rotation])
        
        # Close our Kinect sensor, close the window and quit.
        self._kinect.close()
        pygame.quit()

