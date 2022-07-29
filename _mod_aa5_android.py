#Noesis Python model import+export test module, imports/exports some data from/to a made-up format
from asyncore import read
from email import header
from mimetypes import init
from struct import unpack
from inc_noesis import *
import array
import noesis

#rapi methods should only be used during handler callbacks
import rapi

#registerNoesisTypes is called by Noesis to allow the script to register formats.
#Do not implement this function in script files unless you want them to be dedicated format modules!
def registerNoesisTypes():
   handle = noesis.register("Phoenix Wright Ace Attorney: Dual Destinies Android", ".mod")
   noesis.setHandlerTypeCheck(handle, noepyCheckType)
   noesis.setHandlerLoadModel(handle, noepyLoadModel) #see also noepyLoadModelRPG
   noesis.setHandlerWriteModel(handle, noepyWriteModel)
       #noesis.setHandlerWriteAnim(handle, noepyWriteAnim)
   noesis.logPopup()
       #print("The log can be useful for catching debug prints from preview loads.\nBut don't leave it on when you release your script, or it will probably annoy people.")
   return 1

MOD_HEADER = "MOD"
MOD_VERSION = 7
MOD_HEADER_INT = 0x444F4D
MOD_VERTEX_UNKNOWN_VALUE = 0x7F494949
MOD_BONE_GROUP_SIZE = 32
MATERIAL_NAME_TOTAL_SIZE = 128

#check if it's this type based on the data
def noepyCheckType(data):
   bs = NoeBitStream(data)
   if len(data) < 16:
      return 0
   if bs.readBytes(4).decode("ASCII").rstrip("\0") != MOD_HEADER:
      return 0
   return 1       

#load the model
def noepyLoadModel(data, mdlList):
   ctx = rapi.rpgCreateContext()
   bs = NoeBitStream(data)
   mod = ModModelV7(bs) 
   DoModBinds(mod)
   mdl = rapi.rpgConstructModel()
   LoadMaterial(mdl)
   mdl.setBones(mod.noeBones)
   mdlList.append(mdl)
   rapi.rpgClearBufferBinds()
   return 1

def LoadMaterial(mdl):
 mrlData = rapi.loadPairedFileOptional("material file", ".mrl")

 if(mrlData is not None):
    mrlBs = NoeBitStream(mrlData)
    mrl = MRL(mrlBs)
    texList = []
    mdl.setModelMaterials(NoeModelMaterials(texList, mrl.materials))


#write it
def noepyWriteModel(mdl, bs):
    modData = rapi.loadPairedFileOptional("mod file", ".mod")
        
    if(modData is not None):
      modBs = NoeBitStream(modData)
      mod = ModModelV7(modBs)
      WriteModel(mdl, bs, mod)

    return 1
      

   

def WriteModel(mdl,bs,mod):

    #print("bones:")
    #print(mdl.bones)
    
    WriteAllMod(bs,mod);
        
    vertexFormat0xA8FAB00E = []
    
    countMeshes = 0
    meshesDl = mdl.meshes
    meshesMdl = sorted(mdl.meshes, key=lambda x: x.name)
    for mesh in meshesMdl:
        #print("meshes postions:")
        #print(len(mesh.positions))
        #print("normals:")
        #print(len(mesh.normals))
        #print("weights:")
        #print(len(mesh.weights))
        #print("uvs:")
        #print(len(mesh.uvs))
        print("mesh name:")
        print(mesh.name)
        print(mesh.name[-1])
        mod.meshes[countMeshes].minVerticesIndex = len(vertexFormat0xA8FAB00E)
        
        index = 0
        for pos in mesh.positions:
            vertexFormat0xA8FAB00E.append(ModVertexFormat0xA8FAB00E(pos, mesh.normals[index],mesh.weights[index],mesh.uvs[index], int(mesh.name[-1])))
            index+=1
        
        mod.meshes[countMeshes].maxVerticesIndex = len(vertexFormat0xA8FAB00E) - 1
        mod.meshes[countMeshes].vertexCount = len(mesh.positions)
        mod.meshes[countMeshes].VertexBufferIndex = mod.meshes[countMeshes].minVerticesIndex
        
        countMeshes += 1
       
    vertexBuffPos = bs.getOffset()
    
    for vertex in vertexFormat0xA8FAB00E:
          vertex.WriteFormat0xA8FAB00E(bs)
   
    
    
    
    vertexIndicesPos = bs.getOffset()
    bufferSize = vertexIndicesPos - vertexBuffPos
    stripFacesCount = 0;
    noStripFacesCount = 0;
    indexBase = 0
    countMeshes = 0
    faces = []
    for mesh in meshesMdl:
         mod.meshes[countMeshes].faceIndiciesIndex = len(faces)
         ind = rapi.createTriStrip(mesh.indices)
         stripFacesCount += len(ind)
         noStripFacesCount += len(mesh.indices)
         
         for i in ind:
             faces.append(i + mod.meshes[countMeshes].minVerticesIndex)
             bs.writeUShort(i + mod.meshes[countMeshes].minVerticesIndex)       
         
         indexBase = mod.meshes[countMeshes].minVerticesIndex
         mod.meshes[countMeshes].faceIndiciesCount = len(ind)
         countMeshes += 1
         
        
    mod.header.vertexBufferOffset = vertexBuffPos
    mod.header.facesIndiciesOffset = vertexIndicesPos
    mod.header.vertexCount = len(vertexFormat0xA8FAB00E)
    mod.header.vertexBufferSize = bufferSize
    mod.header.faceCount = stripFacesCount
    mod.header.trianguleCount = int(noStripFacesCount / 3)
    
    bs.seek(0)
    WriteAllMod(bs, mod) 

    return 1


def WriteAllMod(bs, mod):
    mod.header.writeHeader(bs)
    for bone in mod.bones:
        bone.writeBones(bs)
    
    for bone in mod.bones:
        bs.writeBytes(bone.localT)
    
    for bone in mod.bones:
        bs.writeBytes(bone.worldT)
        
    bs.writeBytes(mod.Bone256List)
     
    for bonemap in mod.boneMaps:
        size = len(bonemap)
        remaining = MOD_BONE_GROUP_SIZE - size
        bs.writeInt(size)
        vcount = 0
        for b in bonemap:
            bs.writeByte(b)
        writePadding(bs, remaining)
       
    for meshGroup in mod.meshGroups:
        meshGroup.writeMeshGroups(bs)
           
    for materialName in mod.materialNames:
        materialNameSize = len(materialName)
        remaining = MATERIAL_NAME_TOTAL_SIZE - materialNameSize
        bs.writeString(materialName,0)
        writePadding(bs, remaining)
        
    for mesh in mod.meshes:
        mesh.writeMesh(bs)
        
    afterMeshCount = len(mod.AfterMeshes)
    bs.writeInt(afterMeshCount)
    
    for afterMesh in mod.AfterMeshes:
        afterMesh.writeAfterMesh(bs)

def rev_slice(mylist):
    a = mylist[::-1]
    return a

def writePadding(bs, size):
    for i in range(size):
           bs.writeByte(0)
       

def noepyWriteBone(bs, bone):
    bs.writeInt(bone.index)
    bs.writeInt(bone.parentIndex)
    for mat in bone.getMatrix().toMat44():
        #print(str(mat.toBytes()))
        bs.writeBytes(mat.toBytes())
       #bs.writeBytes(mat)
    #print(str(bone.index))

def DoModBinds(mod):

   counter = 0
   for mesh in mod.meshes:
       rapi.rpgSetMaterial(hex(mod.GetMeshMaterialNameHash(mesh)))
       rapi.rpgSetBoneMap(mod.boneMaps[mesh.BoneGroupIndex])
       rapi.rpgSetName("mesh" + str(mesh.meshIndex) + "_" + str(mesh.boneIndices[0]))
       rapi.rpgBindPositionBufferOfs(mesh.vertices, noesis.RPGEODATA_SHORT, 6,0)
       rapi.rpgBindNormalBuffer(mesh.normals, noesis.RPGEODATA_FLOAT, 16,0)
       rapi.rpgBindUV1Buffer(mesh.uvs, noesis.RPGEODATA_FLOAT, 8,0)
       rapi.rpgBindBoneIndexBuffer(mesh.boneIndices, noesis.RPGEODATA_INT, 4, 1)
       rapi.rpgBindBoneWeightBufferOfs(mesh.boneWeights, noesis.RPGEODATA_INT, 4, 0, 1)
       #rapi.rpgCommitTriangles(mesh.faces, noesis.RPGEODATA_SHORT, (mesh.faceIndiciesCount - 1) * 3, noesis.RPGEO_TRIANGLE, 0)
       rapi.rpgCommitTriangles(mesh.faces, noesis.RPGEODATA_SHORT, mesh.faceIndiciesCount, noesis.RPGEO_TRIANGLE_STRIP, 0)
       counter += 1
       if(counter > 100):
           break
       
           
class ModModelV7:
    def __init__(self,bs):
        self.Load(bs)
        
        
    def Load(self,bs):
        self.calculator = JamCrcCalculator()
        self.header = ModHeaderV7(bs)
        self.ReadBones(self.header.bonesOffset, self.header.boneCount, bs)
        self.ReadMaterialNames(self.header.materialNamesOffset, self.header.materialCount,bs)
        self.ReadMesheGroups(self.header.meshGroupsOffset, self.header.meshGroupCount, bs)
        self.ReadMeshes(self.header.meshesOffset, self.header.meshCount, bs)
        self.ReadMeshesVertex(self.header.vertexBufferOffset, bs)
        self.ReadMeshesFaces(self.header.facesIndiciesOffset, bs)
        
       
        
    def ReadMaterialNames(self, materialNamesOffset, materialCount , bs):
        self.materialNames = []
        for i in range(materialCount):
            bs.seek(materialNamesOffset, NOESEEK_ABS)
            materialName = bs.readString()
            self.materialNames.append(materialName)
            materialNamesOffset += 0x80
            
    def ReadMesheGroups(self,offset, mesheGroupCount, bs):
        bs.seek(offset, NOESEEK_ABS)
        self.meshGroups = []
        for i in range(mesheGroupCount):
            meshGroup = MeshGroup(bs)
            self.meshGroups.append(meshGroup)
        
    def ReadMeshes(self,offset, mesheCount, bs):
        #print(offset)
        bs.seek(offset, NOESEEK_ABS)
        self.meshes = []
        for i in range(mesheCount):
            #rapi.rpgSetName(str(i))
            mesh = MeshV7(bs)
            self.meshes.append(mesh)
        
        self.ReadAfterMeshes(bs)
    
    def ReadAfterMeshes(self, bs):
        self.AfterMeshes = []
        afterMeshesCount = bs.readInt()
        for i in range(afterMeshesCount):
            afterMesh = AfterMesh(bs)
            self.AfterMeshes.append(afterMesh)

    def GetMeshMaterialName(self, mesh):       
        return self.materialNames[mesh.materialIndex]

    def GetMeshMaterialNameHash(self, mesh):       
        return self.calculator.Caculate(self.materialNames[mesh.materialIndex])
    
    def ReadMeshesVertex(self, vertexBufferOffset, bs):
        for mesh in self.meshes:
            bs.seek(vertexBufferOffset, NOESEEK_ABS)
            self.ReadVertexFormat0xA8FAB00E(mesh, mesh.vertexCount, bs)
            vertexBufferOffset += mesh.vertexCount * mesh.vertexStride
        
    def ReadMeshesFaces(self, facesIndiciesOffset, bs):
        
        for mesh in self.meshes:
            offset = facesIndiciesOffset + mesh.faceIndiciesIndex * 2
            bs.seek(offset, NOESEEK_ABS)
            facestmp = []
            facess = []
            
            for i in range(mesh.faceIndiciesCount):
                face = bs.readUShort() - mesh.VertexBufferIndex
                facess.append(face)
                facestmp.extend(face.to_bytes(2, byteorder='little'))
               
            
           

            
            #index = 0
            #total = ((mesh.faceIndiciesCount - 1) * 3)
            #Indices = [0]*total
            #print("pauuuuuuuuuuu")
            #print(len(Indices))
            #while index < total:
               #if(index > 2):
                 #Indices[index] = Indices[index - 2]
                # Indices[index + 1] = Indices[index - 1]
               #  index+=2
               
              # Indices[index] =  bs.readShort() - mesh.VertexBufferIndex
              # print("pau")
             #  print(index)
             #  index += 1

            
           
            #for i in Indices:
              # facestmp.extend(i.to_bytes(2, byteorder='little'))

                
            mesh.faces = bytearray(facestmp)

    def ReadBones(self, bonesOffset, boneCount, bs):
        bs.seek(bonesOffset, NOESEEK_ABS)
        bones = []
        noebones = []
        localTs = []
        worldTs = []
        for i in range(boneCount):
            bone = Bone(bs)
            bones.append(bone)
        
        for bone in bones:
            localTBytes = bs.readBytes(0x40)
            localT = NoeMat44.fromBytes(localTBytes).toMat43()
            #localT[3] = bone.position
            bone.localT = localTBytes
            #noebones.append(NoeBone(bone.index, "bone_" + str(bone.index), localT, None, bone.parentIndex))
           
        for bone in bones:
            worldTBytes = bs.readBytes(0x40)
            worldT = NoeMat44.fromBytes(worldTBytes).toMat43().inverse()
            bone.worldT = worldTBytes
            #worldT[3] = bone.position
            noebones.append(NoeBone(bone.index,"bone_" + str(bone.index), worldT, None, bone.parentIndex))

        self.bones = bones 
        self.noeBones = noebones
        self.Bone256List = bs.readBytes(0x100)
        position = bs.getOffset()
        bonemaps = []
        for i in range(self.header.boneMapCount):
            bs.seek(position, NOESEEK_ABS)
            elementCount = bs.readInt()
            bonemap = [] 
            #bonemap = [0] #teste começando com 0
            for e in range(elementCount):
                bonemap.append(bs.readByte())
            
            bonemaps.append(bonemap)
            position += 0x24

        self.boneMaps = bonemaps
  
    def ReadVertexFormat0xA8FAB00E(self, mesh, count, bs):
        
        vertexBuffer = []
        normalBuffer = []
        UVBuffer = []
        boneIndexBuffer = []
        boneWeightBuffer = []
        for i in range(count):
            x = bs.readShort() #* 128
            y = bs.readShort() #* 128
            z = bs.readShort() #* 128
            bs.seek(2, NOESEEK_REL)
            nx = bs.readByte() / 64.0
            ny = bs.readByte() / 64.0
            nz = bs.readByte() / 64.0
            nw = bs.readByte() / 64.0
            boneIndex = bs.readInt()
            u = bs.readShort() / 1024.0
            v = bs.readShort() / 1024.0
            vertexBuffer.extend(bytearray(struct.pack("h", x)))
            vertexBuffer.extend(bytearray(struct.pack("h", y)))
            vertexBuffer.extend(bytearray(struct.pack("h", z)))
            normalBuffer.extend(bytearray(struct.pack("f", nx)))
            normalBuffer.extend(bytearray(struct.pack("f", ny)))
            normalBuffer.extend(bytearray(struct.pack("f", nz)))
            normalBuffer.extend(bytearray(struct.pack("f", nw)))
            UVBuffer.extend(bytearray(struct.pack("f", u)))
            UVBuffer.extend(bytearray(struct.pack("f", v)))
            boneIndexBuffer.extend(bytearray(struct.pack("i", boneIndex)))
            boneWeightBuffer.extend(bytearray(struct.pack("f", 1.0)))
            bs.seek(4, NOESEEK_REL)
        
        mesh.vertices = bytearray(vertexBuffer)
        mesh.normals = bytearray(normalBuffer)
        mesh.uvs = bytearray(UVBuffer)
        mesh.boneIndices = bytearray(boneIndexBuffer)
        mesh.boneWeights = bytearray(boneWeightBuffer)
   

class ModVertexFormat0xA8FAB00E:
    def __init__(self, position, normal, weight, uv, boneIndex):
        self.normal = normal
        self.position = position
        self.weight = weight
        self.uv = uv
        self.boneIndex = boneIndex
        
    def WriteFormat0xA8FAB00E(self, bs):
        for s in self.position:
            bs.writeShort(int(s * 32767.0))
            
        bs.writeByte(int(0))
        bs.writeByte(int(0))
         
        for n in self.normal:
            bs.writeByte(int(n * 64.0))
            
        bs.writeByte(int(0))
            
        #for w in self.weight.indices:
            #bs.writeInt(int(w))
        
        bs.writeInt(self.boneIndex)
            
        bs.writeShort(int(self.uv[0] * 1024.0))
        bs.writeShort(int(self.uv[1] * 1024.0))
        bs.writeInt(0x7F494949)
        #bs.writeBytes(self.uv.toBytes())
            
        
         
            
        
 
class ModHeaderV7:
    def __init__(self,bs):
        self.bs = bs
        self.magic = bs.readBytes(4)
        self.version = bs.readShort()
        self.boneCount = bs.readShort()
        self.meshCount = bs.readShort()
        self.materialCount = bs.readShort()
        self.vertexCount = bs.readInt()
        self.faceCount = bs.readInt()
        self.trianguleCount = bs.readInt()
        self.vertexBufferSize = bs.readInt()
        self.somePadding0 = bs.readInt()
        self.meshGroupCount = bs.readInt()
        self.boneMapCount = bs.readInt()
        self.bonesOffset = bs.readInt()
        self.somePadding1 = bs.readInt()
        self.meshGroupsOffset = bs.readInt()
        self.somePadding2 = bs.readInt()
        self.materialNamesOffset = bs.readInt()
        self.somePadding3 = bs.readInt()
        self.meshesOffset = bs.readInt()
        self.somePadding4 = bs.readInt()
        self.vertexBufferOffset = bs.readInt()
        self.somePadding5 = bs.readInt()
        self.facesIndiciesOffset = bs.readInt()
        self.somePadding6 = bs.readInt()
        self.somePadding7 = bs.readInt()
        self.somePadding8 = bs.readInt()
        self.boundingSphere = Vector4(bs)
        self.boundingSphereMin = Vector4(bs)
        self.boundingSphereMax = Vector4(bs)
        self.osId1 = bs.readInt()
        self.osId2 = bs.readInt()
        self.somePadding9 = bs.readInt()
        self.somePadding10 = bs.readInt()
        
    def writeHeader(self, bs):
        bs.writeBytes(self.magic)
        bs.writeShort(self.version)
        bs.writeShort(self.boneCount)
        bs.writeShort(self.meshCount)
        bs.writeShort(self.materialCount)
        bs.writeInt(self.vertexCount)
        bs.writeInt(self.faceCount)
        bs.writeInt(self.trianguleCount)
        bs.writeInt(self.vertexBufferSize)
        bs.writeInt(self.somePadding0)
        bs.writeInt(self.meshGroupCount)
        bs.writeInt(self.boneMapCount)
        bs.writeInt(self.bonesOffset)
        bs.writeInt(self.somePadding1)
        bs.writeInt(self.meshGroupsOffset)
        bs.writeInt(self.somePadding2)
        bs.writeInt(self.materialNamesOffset)
        bs.writeInt(self.somePadding3)
        bs.writeInt(self.meshesOffset)
        bs.writeInt(self.somePadding4)
        bs.writeInt(self.vertexBufferOffset)
        bs.writeInt(self.somePadding5)
        bs.writeInt(self.facesIndiciesOffset)
        bs.writeInt(self.somePadding6)
        bs.writeInt(self.somePadding7)
        bs.writeInt(self.somePadding8)
        self.boundingSphere.writeVector4(bs)
        self.boundingSphereMin.writeVector4(bs)
        self.boundingSphereMax.writeVector4(bs)
        bs.writeInt(self.osId1)
        bs.writeInt(self.osId2)
        bs.writeInt(self.somePadding9)
        bs.writeInt(self.somePadding10)
        return 1

class Vector4:
    def __init__(self, bs):
        self.x = bs.readFloat()
        self.y = bs.readFloat()
        self.z = bs.readFloat()
        self.w = bs.readFloat()
    
    def writeVector4(self, bs):
        bs.writeFloat(self.x)
        bs.writeFloat(self.y)
        bs.writeFloat(self.z)
        bs.writeFloat(self.w)
        return 1

class MeshGroup:
    def __init__(self, bs):
        self.groupId = bs.readInt()
        self.unknown0 = bs.readInt()
        self.unknown1 = bs.readInt()
        self.unknown2 = bs.readInt()
        self.unknownBouding = Vector4(bs)
    
    def writeMeshGroups(self, bs):
        bs.writeInt(self.groupId)
        bs.writeInt(self.unknown0)
        bs.writeInt(self.unknown1)
        bs.writeInt(self.unknown2)
        self.unknownBouding.writeVector4(bs)
        
class MeshV7:
    def __init__(self, bs):
        self.meshTypeFlags = bs.readShort()
        self.vertexCount = bs.readShort()
        self.materialIndexAndUnknown0 = bs.readShort()
        self.setMaterialIndex(self.materialIndexAndUnknown0)
        self.unknown1 = bs.readByte()
        self.renderType = bs.readByte()
        self.meshFlags = bs.readByte()
        self.renderPriority = bs.readByte()
        self.vertexStride = bs.readByte()
        self.attributesCount = bs.readByte()
        self.VertexBufferIndex = bs.readInt()
        self.padding0 = bs.readInt()
        self.VertexBufferFormat = bs.readInt()
        self.faceIndiciesIndex = bs.readInt()
        self.faceIndiciesCount = bs.readInt()
        self.padding1 = bs.readInt()
        self.BoneGroupIndex = bs.readByte()
        print("BoneGroupIndex")
        print(self.BoneGroupIndex)
        self.BoneIndiciesIndex = bs.readByte()
        self.meshIndex = bs.readShort()
        self.minVerticesIndex = bs.readShort()
        self.maxVerticesIndex = bs.readShort()
        self.meshUniqueHash = bs.readInt()
        self.padding2 = bs.readInt()
        self.padding3 = bs.readInt()
    
    def setMaterialIndex(self, value):
        self.materialIndex = value >> 0xC
        self.unknown0 = value & 0xFFF
        
    def writeMesh(self, bs):
        bs.writeUShort(self.meshTypeFlags)
        bs.writeUShort(self.vertexCount)
        bs.writeUShort(self.materialIndexAndUnknown0)
        bs.writeByte(self.unknown1)
        bs.writeByte(self.renderType)
        bs.writeByte(self.meshFlags)
        bs.writeByte(self.renderPriority)
        bs.writeByte(self.vertexStride)
        bs.writeByte(self.attributesCount)
        bs.writeInt(self.VertexBufferIndex)
        bs.writeInt(self.padding0)
        bs.writeInt(self.VertexBufferFormat)
        bs.writeInt(self.faceIndiciesIndex)
        bs.writeInt(self.faceIndiciesCount)
        bs.writeInt(self.padding1)
        bs.writeByte(self.BoneGroupIndex)
        bs.writeByte(self.BoneIndiciesIndex)
        bs.writeUShort(self.meshIndex)
        bs.writeUShort(self.minVerticesIndex)
        bs.writeUShort(self.maxVerticesIndex)
        bs.writeInt(self.meshUniqueHash)
        bs.writeInt(self.padding2)
        bs.writeInt(self.padding3)
       
       
class AfterMesh:
    def __init__(self, bs):
        self.boneId = bs.readInt()
        self.unknown0 = bs.readInt()
        self.unknown1 = bs.readInt()
        self.unknown2 = bs.readInt()
        self.center = Vector4(bs)
        self.minS = Vector4(bs)
        self.maxS = Vector4(bs)
        self.unknown3 = bs.readBytes(0x50)
    
    def writeAfterMesh(self, bs):
        bs.writeInt(self.boneId)
        bs.writeInt(self.unknown0)
        bs.writeInt(self.unknown1)
        bs.writeInt(self.unknown2)
        self.center.writeVector4(bs)
        self.minS.writeVector4(bs)
        self.maxS.writeVector4(bs)
        bs.writeBytes(self.unknown3)
      
      
class Bone:
    def __init__(self, bs):
        self.index = bs.readByte()
        self.parentIndex = bs.readByte()
        self.opositeIndex = bs.readByte()
        self.padding = bs.readByte()
        self.childDistance = bs.readFloat()
        self.boneSize = bs.readFloat()
        self.boneBytes = bs.readBytes(12)
        self.position = NoeVec3.fromBytes(self.boneBytes)
    
    def writeBones(self, bs):
        bs.writeByte(self.index)
        bs.writeByte(self.parentIndex)
        bs.writeByte(self.opositeIndex)
        bs.writeByte(self.padding)
        bs.writeFloat(self.childDistance)
        bs.writeFloat(self.boneSize)
        bs.writeBytes(self.boneBytes)
       
       
        

class MRL:
    def __init__(self, bs):
       self.header = MRLHeader(bs)
       self.ReadTextureData(self.header.textureCount, self.header.textureDataOffset, bs)
       self.ReadMaterialData(self.header.materialCount, self.header.materialDataOffset, bs)

    def ReadTextureData(self, count, textureDataOffset, bs):
        self.textureData = []
        
        for i in range(count):
            bs.seek(textureDataOffset, NOESEEK_ABS)
            texturedata = MRLTextureData(bs)
            self.textureData.append(texturedata)
            
            textureDataOffset += 0x50

    def ReadMaterialData(self, count, materialDataOffset, bs):
        self.materialData = []
        self.materials = []
        for i in range(count):
            bs.seek(materialDataOffset, NOESEEK_ABS)
            materialdata = MRLMaterialData(bs)
            materialdata.texturePath = self.textureData[materialdata.materialDesc.textureId].texturePath
            self.materialData.append(materialdata)
            material = NoeMaterial(hex(materialdata.materialHashName), rapi.getLocalFileName(materialdata.texturePath) + ".png")
            self.materials.append(material)
            materialDataOffset += 0x30
            
   



class MRLHeader:
     def __init__(self, bs):
        self.magic = bs.readBytes(4)
        self.version = bs.readInt()
        self.materialCount = bs.readInt()
        self.textureCount = bs.readInt()
        self.formatHash = bs.readInt()
        self.align0 = bs.readInt()
        self.textureDataOffset = bs.readInt()
        self.align1 = bs.readInt()
        self.materialDataOffset = bs.readInt()
        self.align2 = bs.readInt()
        

class MRLTextureData:
    def __init__(self, bs):
        self.fileTypeHash = bs.readInt()
        self.align0 = bs.readInt()
        self.align1 = bs.readInt()
        self.align2 = bs.readInt()
        self.texturePath = bs.readString()         

class MRLMaterialData:
     def __init__(self, bs):
         self.fileTypeHash = bs.readInt()
         self.unknown0 = bs.readInt()
         self.materialHashName = bs.readUInt()
         self.unknown1 = bs.readInt()
         self.unknown2 = bs.readInt()
         self.unknown3 = bs.readInt()
         self.materialExtendAreaSize = bs.readInt()
         self.unknown4 = bs.readInt()
         self.materialDescOffset = bs.readInt()
         self.align0 = bs.readInt()
         self.materialExtendAreaOffset = bs.readInt()
         self.align1 = bs.readInt()
         self.materialDesc = self.ReadMaterialDesc(self.materialDescOffset, bs)

     def ReadMaterialDesc(self, descOffset, bs):
         bs.seek(descOffset, NOESEEK_ABS)
         return MaterialDesc(bs)


class MaterialDesc:
    def __init__(self, bs):
        self.decType = bs.readInt()
        self.unknown0 = bs.readInt()
        self.someOffset = bs.readInt()
        self.padding0 = bs.readInt()
        self.shaderHashName = bs.readInt()
        self.padding1 = bs.readInt()
        self.blockType = bs.readInt() & 0xf
        self.unknown1 = bs.readInt()
        self.textureId = bs.readInt() - 1
        self.padding2 = bs.readInt()


class JamCrcCalculator:

    def __init__(self):
       self.table  =  [
                        0x00000000,0x77073096,0xEE0E612C,0x990951BA,0x76DC419,0x706AF48F,0xE963A535,0x9E6495A3,
                        0xEDB8832,0x79DCB8A4,0xE0D5E91E,0x97D2D988,0x9B64C2B,0x7EB17CBD,0xE7B82D07,0x90BF1D91,
                        0x1DB71064,0x6AB020F2,0xF3B97148,0x84BE41DE,0x1ADAD47D,0x6DDDE4EB,0xF4D4B551,0x83D385C7,
                        0x136C9856,0x646BA8C0,0xFD62F97A,0x8A65C9EC,0x14015C4F,0x63066CD9,0xFA0F3D63,0x8D080DF5,
                        0x3B6E20C8,0x4C69105E,0xD56041E4,0xA2677172,0x3C03E4D1,0x4B04D447,0xD20D85FD,0xA50AB56B,
                        0x35B5A8FA,0x42B2986C,0xDBBBC9D6,0xACBCF940,0x32D86CE3,0x45DF5C75,0xDCD60DCF,0xABD13D59,
                        0x26D930AC,0x51DE003A,0xC8D75180,0xBFD06116,0x21B4F4B5,0x56B3C423,0xCFBA9599,0xB8BDA50F,
                        0x2802B89E,0x5F058808,0xC60CD9B2,0xB10BE924,0x2F6F7C87,0x58684C11,0xC1611DAB,0xB6662D3D,
                        0x76DC4190,0x1DB7106,0x98D220BC,0xEFD5102A,0x71B18589,0x6B6B51F,0x9FBFE4A5,0xE8B8D433,
                        0x7807C9A2,0xF00F934,0x9609A88E,0xE10E9818,0x7F6A0DBB,0x86D3D2D,0x91646C97,0xE6635C01,
                        0x6B6B51F4,0x1C6C6162,0x856530D8,0xF262004E,0x6C0695ED,0x1B01A57B,0x8208F4C1,0xF50FC457,
                        0x65B0D9C6,0x12B7E950,0x8BBEB8EA,0xFCB9887C,0x62DD1DDF,0x15DA2D49,0x8CD37CF3,0xFBD44C65,
                        0x4DB26158,0x3AB551CE,0xA3BC0074,0xD4BB30E2,0x4ADFA541,0x3DD895D7,0xA4D1C46D,0xD3D6F4FB,
                        0x4369E96A,0x346ED9FC,0xAD678846,0xDA60B8D0,0x44042D73,0x33031DE5,0xAA0A4C5F,0xDD0D7CC9,
                        0x5005713C,0x270241AA,0xBE0B1010,0xC90C2086,0x5768B525,0x206F85B3,0xB966D409,0xCE61E49F,
                        0x5EDEF90E,0x29D9C998,0xB0D09822,0xC7D7A8B4,0x59B33D17,0x2EB40D81,0xB7BD5C3B,0xC0BA6CAD,
                        0xEDB88320,0x9ABFB3B6,0x3B6E20C,0x74B1D29A,0xEAD54739,0x9DD277AF,0x4DB2615,0x73DC1683,
                        0xE3630B12,0x94643B84,0xD6D6A3E,0x7A6A5AA8,0xE40ECF0B,0x9309FF9D,0xA00AE27,0x7D079EB1,
                        0xF00F9344,0x8708A3D2,0x1E01F268,0x6906C2FE,0xF762575D,0x806567CB,0x196C3671,0x6E6B06E7,
                        0xFED41B76,0x89D32BE0,0x10DA7A5A,0x67DD4ACC,0xF9B9DF6F,0x8EBEEFF9,0x17B7BE43,0x60B08ED5,
                        0xD6D6A3E8,0xA1D1937E,0x38D8C2C4,0x4FDFF252,0xD1BB67F1,0xA6BC5767,0x3FB506DD,0x48B2364B,
                        0xD80D2BDA,0xAF0A1B4C,0x36034AF6,0x41047A60,0xDF60EFC3,0xA867DF55,0x316E8EEF,0x4669BE79,
                        0xCB61B38C,0xBC66831A,0x256FD2A0,0x5268E236,0xCC0C7795,0xBB0B4703,0x220216B9,0x5505262F,
                        0xC5BA3BBE,0xB2BD0B28,0x2BB45A92,0x5CB36A04,0xC2D7FFA7,0xB5D0CF31,0x2CD99E8B,0x5BDEAE1D,
                        0x9B64C2B0,0xEC63F226,0x756AA39C,0x26D930A,0x9C0906A9,0xEB0E363F,0x72076785,0x5005713,
                        0x95BF4A82,0xE2B87A14,0x7BB12BAE,0xCB61B38,0x92D28E9B,0xE5D5BE0D,0x7CDCEFB7,0xBDBDF21,
                        0x86D3D2D4,0xF1D4E242,0x68DDB3F8,0x1FDA836E,0x81BE16CD,0xF6B9265B,0x6FB077E1,0x18B74777,
                        0x88085AE6,0xFF0F6A70,0x66063BCA,0x11010B5C,0x8F659EFF,0xF862AE69,0x616BFFD3,0x166CCF45,
                        0xA00AE278,0xD70DD2EE,0x4E048354,0x3903B3C2,0xA7672661,0xD06016F7,0x4969474D,0x3E6E77DB,
                        0xAED16A4A,0xD9D65ADC,0x40DF0B66,0x37D83BF0,0xA9BCAE53,0xDEBB9EC5,0x47B2CF7F,0x30B5FFE9,
                        0xBDBDF21C,0xCABAC28A,0x53B39330,0x24B4A3A6,0xBAD03605,0xCDD70693,0x54DE5729,0x23D967BF,
                        0xB3667A2E,0xC4614AB8,0x5D681B02,0x2A6F2B94,0xB40BBE37,0xC30C8EA1,0x5A05DF1B,0x2D02EF8D]
      

    def Caculate(self, data):
        #print(data)
        dataBytes = bytearray(data, encoding="ASCII")
        crc = 0xffffffff
        
        for b in dataBytes:
            crc = (crc >> 8) ^ self.table[(crc & 0xff) ^ b]

        return crc;  
    