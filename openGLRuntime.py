# Pygame/PyopenGL example by Bastiaan Zapf, Apr 2009

from OpenGL.GL import *
from OpenGL.GLU import *
import statistics
import random
from math import *

import pygame

from vectors import Point, Vector
import sys
import time
import os
import ctypes

class OpenGLRuntime(object):
    def __init__(self, fromK, verts):
        pygame.init() 

        user32 = ctypes.windll.user32        
        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)
        self.scaleFactor = 3
        self.window_width = self.screen_width//self.scaleFactor
        self.window_height = self.screen_height//self.scaleFactor
        self.windowOffset = 100
        self.verts = verts
        self.sortedVerts = []
        self.GLindex = 1
        self.GlListCount = 10
        self.GLLists = None
        self.GLGeos = [None] * self.GlListCount
        self.done = False
        self.dt = 0
        self.timer = time.time()
        self.centroid = [0,0,0]
        self.geoComputed = False
        self.rotation = (0,0)

        self.fromK = fromK

        pos = str(self.screen_width//2 - self.window_width//2) + "," + str(self.screen_height - self.window_height - self.windowOffset)
        os.environ['SDL_VIDEO_WINDOW_POS'] = pos
        pygame.display.set_mode((self.screen_width//3,self.screen_height//3), pygame.OPENGL|pygame.DOUBLEBUF|pygame.NOFRAME)
        

    def createAndCompileShader(self, type,source):
        shader=glCreateShader(type)
        glShaderSource(shader,source)
        glCompileShader(shader)

        # get "compile status" - glCompileShader will not fail with 
        # an exception in case of syntax errors

        result=glGetShaderiv(shader,GL_COMPILE_STATUS)

        if (result!=1): # shader didn't compile
            raise Exception("Couldn't compile shader\nShader compilation Log:\n"+glGetShaderInfoLog(shader))
        return shader

    def getFaceNormal(self, face):
        points = []
        for v in face:
            points.append(Point(v[0], v[1], v[2]))
        vecA = Vector.from_points(points[0],points[1])
        vecB = Vector.from_points(points[0],points[2])
        vecResult = Vector.cross(vecA,vecB)
        return vecResult

    def getVolumeCen(self):
        xVals = [100,0]
        yVals = [100,0]
        zVals = [100,0]

        for section in self.verts:
            for vert in section:
                if vert[0] < xVals[0]:
                    xVals[0] = vert[0]
                if vert[0] > xVals[1]:
                    xVals[1] = vert[0]
                if vert[1] < yVals[0]:
                    yVals[0] = vert[1]
                if vert[1] > yVals[1]:
                    yVals[1] = vert[1]
                if vert[2] < zVals[0]:
                    zVals[0] = vert[2]
                if vert[2] > zVals[1]:
                    zVals[1] = vert[2]
                
        return (statistics.mean(xVals), statistics.mean(yVals), statistics.mean(zVals))

    def geo(self):

        if len(self.sortedVerts) == 0 or self.geoComputed == False:
            for i in range(len(self.verts)-1):
                temp = []
                for j in range(len(self.verts[0])):
                    face1 = [self.verts[i][j-1], self.verts[i][j], self.verts[i+1][j]]
                    face2 = [self.verts[i][j-1], self.verts[i+1][j], self.verts[i+1][j-1]]
                    vec1 = self.getFaceNormal(face1)
                    vec2 = self.getFaceNormal(face2)
                    temp.append([vec1]+face1)
                    temp.append([vec2]+face2)
                self.sortedVerts.extend(temp)
        
            glColor3f(1,1,1)
            
            glNewList(1, GL_COMPILE)

            glBegin(GL_TRIANGLES)
            for face in self.sortedVerts:
                glColor3fv((.7,.7,.7))
                glNormal3f(face[0].x, face[0].y, face[0].z)
                glVertex3f(face[1][0], face[1][1], face[1][2])
                glVertex3f(face[2][0], face[2][1], face[2][2])
                glVertex3f(face[3][0], face[3][1], face[3][2])
            glEnd()
            glEndList()

        self.centroid = self.getVolumeCen()
        self.geoComputed = True

    def initOpenGL(self):
    # build shader program
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_DEPTH_TEST)
        glShadeModel(GL_SMOOTH)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 4)
        glEnable(GL_NORMALIZE);

        glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glEnable(GL_COLOR_MATERIAL)

        glClearColor(0, 0, 0, 0)
        glClearStencil(0)
        glClearDepth(1.0)
        glDepthFunc(GL_LEQUAL)

        vertex_shader= self.createAndCompileShader(GL_VERTEX_SHADER,"""
        varying vec3 v;
        varying vec3 N;

        void main(void)
        {

           v = gl_ModelViewMatrix * gl_Vertex;
           N = gl_NormalMatrix * gl_Normal;

           gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;

        }
        """)

        fragment_shader= self.createAndCompileShader(GL_FRAGMENT_SHADER,"""
        varying vec3 N;
        varying vec3 v;

        void main(void)
        {
           vec3 L = gl_LightSource[0].position.xyz-v;

           // "Lambert's law"? (see notes)
           // Rather: faces will appear dimmer when struck in an acute angle
           // distance attenuation

           float Idiff = max(dot(normalize(L),N),0.0)*pow(length(L),-2.0); 

           gl_FragColor = vec4(.7,.7,.7,1.0)+ // white
                          vec4(1.0,1.0,1.0,1.0)*Idiff; // diffuse reflection
        }
        """)

        program=glCreateProgram()
        glAttachShader(program,vertex_shader)
        glAttachShader(program,fragment_shader)
        glLinkProgram(program)

        glUseProgram(program)   

        self.done = False

    def initLights(self):
        lightKa = (.2, .2, .2, 1.0)
        lightKd = (.7, .7, .7, 1.0)
        lightKs = (1, 1, 1, 1)
        glLightfv(GL_LIGHT0, GL_AMBIENT, lightKa);
        glLightfv(GL_LIGHT0, GL_DIFFUSE, lightKd);
        glLightfv(GL_LIGHT0, GL_SPECULAR, lightKs);

     
        lightPos = (0, 0, 20, 1); 
        glLightfv(GL_LIGHT0, GL_POSITION, lightPos);

        glEnable(GL_LIGHT0); 

    def run(self):
        self.initOpenGL()
        self.initLights()
        self.GLGeos = glGenLists(1)
        self.geo()
        
        while not self.done:
            for event in pygame.event.get(): # User did something
                if event.type == pygame.QUIT: # If user clicked close
                    self._done = True
            
            queueFromK = self.fromK.get()
            self.rotation = queueFromK[0]

            self.dt += time.time()-self.timer
            self.timer = time.time()

            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(50,1,0.01,1000)
            glClearColor(0.0, 0.0, 0.0, 1.0)
            glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)

            if len(self.verts) != 0:

                gluLookAt(sin(self.dt/10+self.rotation[0]/100)*4+self.centroid[0],0,cos(self.dt/10+self.rotation[0]/100)*4+self.centroid[2],self.centroid[0],self.centroid[1],self.centroid[2],0,1,0)
                  
                glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)

                glMatrixMode(GL_MODELVIEW)
                glLoadIdentity()

                # calculate light source position

                ld=[100,100,100]

                # pass data to fragment shader

                light_ambient = [ 1, 1, 1, 1.0 ]
                light_diffuse = [ 1, 1, 1, 1 ]
                light_specular = [ 1.0, 1.0, 1.0, 1.0 ]
                light_position = [ 0, 0, 2.0, 0.0 ]

                glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient);
                glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse);
                glLightfv(GL_LIGHT0, GL_SPECULAR, light_specular);
                glLightfv(GL_LIGHT0, GL_POSITION, light_position);



                glCallList(1)
            

            pygame.display.flip()