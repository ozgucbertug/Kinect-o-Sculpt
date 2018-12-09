import GhPython
import rhinoscriptsyntax as rs

dataRead = []
verts = []
mesh = []
points = []
line = []
surface = []
with open(path) as data:
    content = data.read()
    content = content.splitlines()
    for i in range(len(content)):
        content[i] = content[i].split(',')
        temp = []
        for pos in content[i]:
            temp.append(float(pos)*10)
        dataRead.append(tuple(temp))

for section in dataRead:
    temp = []
    for j in range(0,len(section),3):
        point = (section[j], section[j+2], section[j+1])
        temp.append(point)
    verts.append(temp)

for i in range(len(verts)-1):
    for j in range(len(verts[0])):
        quadList = (verts[i][j-1], verts[i][j], verts[i+1][j], verts[i+1][j-1])
        surface.append(rs.AddSrfPt((quadList[0],quadList[1],quadList[2])))
        surface.append(rs.AddSrfPt((quadList[0],quadList[2],quadList[3])))
        faceList = [(0,1,2,2), (0,2,3,3)]
        mesh.append(rs.AddMesh(quadList, faceList))