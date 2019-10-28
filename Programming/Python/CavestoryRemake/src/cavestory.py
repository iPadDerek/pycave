import sys
import os
import math
import sdl2
import sdl2.sdlimage
import sdl2.ext
import untangle
import traceback
#import pytinyxml2
from enum import Enum
from ctypes import byref, POINTER, c_int
from types import SimpleNamespace
from sdl2 import *

FPS = 50
MAX_FRAME_TIME = 5 * 1000 / FPS

GLOBAL = SimpleNamespace(SCREEN_WIDTH = 640, SCREEN_HEIGHT = 480, SPRITE_SCALE = 2) #640, 480
PLAYER_CONSTANTS = SimpleNamespace(WALK_SPEED = 0.2, JUMP_SPEED = 0.7, GRAVITY = 0.002, GRAVITY_CAP = 0.8) #.2, .7, .002, .8

PATHNAME = os.path.abspath(os.path.dirname(sys.argv[0]))

class Side(Enum):
    TOP = 0
    BOTTOM = 1
    LEFT = 2
    RIGHT = 3
    NONE = 4


def getOppositeSide(side):
    if side == Side.TOP:
        return Side.BOTTOM
    elif side == Side.BOTTOM:
        return Side.TOP
    elif side == Side.RIGHT:
        return Side.LEFT
    elif side == Side.LEFT:
        return Side.RIGHT
    else:
        return Side.NONE

class Direction(Enum):
    LEFT = 0
    RIGHT = 1
    UP = 2
    DOWN = 3

class Vector2(object):
    def __init__(self, x = 0, y = 0):
        self.x = x
        self.y = y

    def zero(self):
        return Vector2(0, 0)

class Tileset(object):
    def __init__(self, texture = None, firstGid = -1):
        self.FirstGid = firstGid
        self.Texture = texture

        
class Sprite(object):
    def __init__(self, graphics, filePath, sourceX, sourceY, width, height, posX, posY):
        self._x = posX
        self._y = posY
        self._sourceRect = SDL_Rect()
        self._spriteSheet = POINTER(SDL_Texture)()
        self._sourceRect.x = sourceX
        self._sourceRect.y = sourceY
        self._sourceRect.w = width
        self._sourceRect.h = height
        self._boundingBox = Rectangle(self._x, self._y, width * GLOBAL.SPRITE_SCALE, height * GLOBAL.SPRITE_SCALE)

        self._spriteSheet = SDL_CreateTextureFromSurface(graphics._renderer, graphics.loadImage(filePath))
        if (self._spriteSheet == None):
            print("\nError: Unable to load image\n")
        

    #def __del__(self):


    def update(self):
        self._boundingBox = Rectangle(self._x, self._y, self._sourceRect.w * GLOBAL.SPRITE_SCALE, self._sourceRect.h * GLOBAL.SPRITE_SCALE)

    def draw(self, graphics, x, y):
        destinationRectangle = SDL_Rect(x, y, self._sourceRect.w * GLOBAL.SPRITE_SCALE, self._sourceRect.h * GLOBAL.SPRITE_SCALE)
        graphics.blitSurface(self._spriteSheet, byref(self._sourceRect), byref(destinationRectangle))

    def getCollisionSide(self, other):
        amtRight = self._boundingBox.getRight() - other.getLeft()
        amtLeft = other.getRight() - self._boundingBox.getLeft()
        amtTop = other.getBottom() - self._boundingBox.getTop()
        amtBottom = self._boundingBox.getBottom() - other.getTop()

        lowest = min(abs(amtRight), abs(amtLeft), abs(amtTop), abs(amtBottom))

        if lowest == abs(amtRight):
            return Side.RIGHT
        elif lowest == abs(amtLeft):
            return Side.LEFT
        elif lowest == abs(amtTop):
            return Side.TOP
        elif lowest == abs(amtBottom):
            return Side.BOTTOM
        else:
            return Side.NONE


class AnimatedSprite(Sprite):
    def __init__(self, graphics, filePath, sourceX, sourceY, width, height, posX, posY, timeToUpdate):
        super().__init__(graphics, filePath, sourceX, sourceY, width, height, posX, posY)
        self._frameIndex = 0
        self._timeToUpdate = timeToUpdate
        self._timeElapsed = 0
        self._visible = True
        self._currentAnimationOnce = False
        self._currentAnimation = ""
        self._animations = {}
        self._offsets = {}



    def playAnimation(self, animation, once = False):
        self._currentAnimationOnce = once
        if (self._currentAnimation != animation):
            self._currentAnimation = animation
            self._frameIndex = 0

    def update(self, elapsedTime):
        super().update()

        self._timeElapsed += elapsedTime
        if (self._timeElapsed > self._timeToUpdate):
            self._timeElapsed -= self._timeToUpdate
            if (self._frameIndex < len(self._animations[self._currentAnimation]) - 1):
                self._frameIndex += 1
            else:
                if (self._currentAnimationOnce == True):
                    self.setVisible(False)
                self._frameIndex = 0
                self.animationDone(self._currentAnimation)

    def draw(self, graphics, x, y):
        if (self._visible):
            destinationRectangle = SDL_Rect()
            destinationRectangle.x = int(x) + self._offsets[self._currentAnimation].x
            destinationRectangle.y = int(y) + self._offsets[self._currentAnimation].y
            destinationRectangle.w = self._sourceRect.w * GLOBAL.SPRITE_SCALE
            destinationRectangle.h = self._sourceRect.h * GLOBAL.SPRITE_SCALE

            sourceRect = self._animations[self._currentAnimation][self._frameIndex]
            graphics.blitSurface(self._spriteSheet, sourceRect, destinationRectangle)


    def addAnimations(self, frames, x, y, name, width, height, offset):
        rectangles = []
        for i in range(0, frames):
            newRect = SDL_Rect((i + x) * width, y, width, height)
            rectangles.append(newRect)

        self._animations[name] = rectangles
        self._offsets[name] = offset

    def resetAnimations(self):
        self._animations.clear()
        self._offsets.clear()

    def stopAnimation(self):
        self._frameIndex = 0
        self.animationDone(self._currentAnimation)

    def setVisible(self, visible):
        self._visible = visible

    def animationDone(self, currentAnimation):
        pass


class Player(AnimatedSprite):
    def __init__(self, graphics, spawnPoint):
        cPath = PATHNAME + "/../Resources/sprites/MyChar.png"
        super().__init__(graphics, cPath, 0, 0, 16, 16, spawnPoint.x, spawnPoint.y, 100)
        graphics.loadImage(cPath)
        
        self.setupAnimations()
        self.playAnimation("RunRight")
        self._dx = 0
        self._dy = 0
        self._facing = Direction.RIGHT
        self._grounded = False

    def draw(self, graphics):
        super().draw(graphics, self._x, self._y)


    def update(self, elapsedTime):
        if self._dy <= PLAYER_CONSTANTS.GRAVITY_CAP:
            self._dy += PLAYER_CONSTANTS.GRAVITY * elapsedTime
        self._x += self._dx * elapsedTime
        self._y += self._dy * elapsedTime
        super().update(elapsedTime)


    def animationDone(self, currentAnimation):
        pass


    def setupAnimations(self):
        self.addAnimations(1, 0, 0, "IdleLeft", 16, 16, Vector2(0, 0))
        self.addAnimations(1, 0, 16, "IdleRight", 16, 16, Vector2(0, 0))
        self.addAnimations(3, 0, 0, "RunLeft", 16, 16, Vector2(0, 0))
        self.addAnimations(3, 0, 16, "RunRight", 16, 16, Vector2(0, 0))

    def moveLeft(self):
        self._dx = -PLAYER_CONSTANTS.WALK_SPEED
        self.playAnimation("RunLeft")
        self._facing = Direction.LEFT

    def moveRight(self):
        self._dx = PLAYER_CONSTANTS.WALK_SPEED
        self.playAnimation("RunRight")
        self._facing = Direction.RIGHT

    def stopMoving(self):
        self._dx = 0
        self.playAnimation("IdleRight" if self._facing == Direction.RIGHT else "IdleLeft")

    def jump(self):
        if self._grounded:
            self._dy = 0
            self._dy -= PLAYER_CONSTANTS.JUMP_SPEED
            self._grounded = False

    def handleTileCollisions(self, others):
        for i in range(0, len(others)):
            collisionSide = Sprite.getCollisionSide(self, others[i])
            if collisionSide != Side.NONE:
                if collisionSide == Side.TOP:
                    self._y = others[i].getBottom() + 1
                    self._dy = 0

                elif collisionSide == Side.BOTTOM:
                    self._y = others[i].getTop() - self._boundingBox._height - 1
                    self._dy = 0
                    self._grounded = True

                elif collisionSide == Side.LEFT:
                    self._x = others[i].getRight() + 1

                elif collisionSide == Side.RIGHT:
                    self._x = others[i].getLeft() - self._boundingBox._width - 1

    def handleSlopeCollisions(self, others):
        for i in range(0, len(others)):
            b = (others[i]._p1.y - (others[i]._slope * float(abs(others[i]._p1.x))))
            centerX = self._boundingBox.getCenterX()
            newY = (others[i]._slope * centerX) + b - 8

            if self._grounded:
                self._y = newY - self._boundingBox._height
                self._grounded = True

class Rectangle(object):
    def __init__(self, x, y, width, height):
        self._x = x
        self._y = y
        self._width = width
        self._height = height

    def getCenterX(self):
        return self._x + self._width // 2
    
    def getCenterY(self):
        return self._y + self._height // 2
    
    def getLeft(self):
        return self._x
    
    def getRight(self):
        return self._x + self._width

    def getTop(self):
        return self._y

    def getBottom(self):
        return self._y + self._height

    def getSide(self, side):
        if side == Side.LEFT:
            return self.getLeft()
        elif side == Side.RIGHT:
            return self.getRight()
        elif side == Side.TOP:
            return self.getTop()
        elif side == Side.BOTTOM:
            return self.getBottom()
        else:
            return Side.NONE

    def collidesWith(self, other):
        return self.getRight() >= other.getLeft() and self.getLeft() <= other.getRight() and self.getTop() <= other.getBottom() and self.getBottom() >= other.getTop()
        
    def isValidRectangle(self):
        return self._x >= 0 and self._y >= 0 and self._width >= 0 and self._height >= 0

class Slope(object):
    def __init__(self, p1, p2):
        self._p1 = p1
        self._p2 = p2
        if(self._p2.x - self._p1.x != 0):
            self._slope = (abs(self._p2.y) - abs(self._p1.y)) / (abs(self._p2.x) - abs(self._p1.x))

    def collidesWith(self, other):
        return ((other.getRight() >= self._p2.x and other.getLeft() <= self._p1.x and other.getTop() <= self._p2.y and other.getBottom() >= self._p1.y) or (other.getRight() >= self._p1.x and other.getLeft() <= self._p2.x and other.getTop() <= self._p1.y and other.getBottom() >= self._p2.y) or \
            (other.getLeft() <= self._p1.x and other.getRight() >= self._p2.x and other.getTop() <= self._p1.y and other.getBottom() >= self._p2.y) or (other.getLeft() <= self._p2.x and other.getRight() >= self._p1.x and other.getTop() <= self._p2.y and other.getBottom() >= self._p1.y))

class Graphics(object):
    def __init__(self):
        self._window = POINTER(SDL_Window)()
        self._renderer = POINTER(SDL_Renderer)()
        self._spriteSheets = {}
        SDL_CreateWindowAndRenderer(GLOBAL.SCREEN_WIDTH, GLOBAL.SCREEN_HEIGHT, 0, byref(self._window), byref(self._renderer))
        SDL_SetWindowTitle(self._window, b"Cavestory")
        
    
    def __del__(self):
        SDL_DestroyWindow(self._window)
        SDL_DestroyRenderer(self._renderer)

    def loadImage(self, filePath):
        if filePath not in self._spriteSheets:
                self._spriteSheets[filePath] = sdl2.ext.load_image(filePath)

        return self._spriteSheets[filePath]

    def blitSurface(self, texture, sourceRectangle, destinationRectangle):
        SDL_RenderCopy(self._renderer, texture, sourceRectangle, destinationRectangle)

    def flip(self):
        SDL_RenderPresent(self._renderer)

    def clear(self):
        SDL_RenderClear(self._renderer)


class Level(object):
    def __init__(self, mapName, spawnPoint, graphics):
        self._mapName = mapName
        self._spawnPoint = spawnPoint
        self._size = Vector2(0, 0)
        self.loadMap(mapName, graphics)


    def update(self, elapsedTime):
        pass

    def draw(self, graphics):
        for i in range(0, len(self._tileList)):
            self._tileList[i].draw(graphics)

    def checkTileCollisions(self, other):
        others = []
        for i in range(0, len(self._collisionRects)):
            if self._collisionRects[i].collidesWith(other):
                others.append(self._collisionRects[i])
        return others

    def checkSlopeCollisions(self, other):
        others = []
        for i in range(0, len(self._slopes)):
            if self._slopes[i].collidesWith(other):
                others.append(self._slopes[i])
        
        return others

        
    def loadMap(self, mapName, graphics):
        self._tilesets = []
        self._tileList = []
        self._collisionRects = []
        self._slopes = []
        ss = PATHNAME + "/../Resources/maps/" + mapName + ".tmx"
        #ss = "/home/derek/Programming/Python/CavestoryRemake/Resources/maps/" + mapName + ".tmx"
        doc = untangle.parse(ss)

        width, height = 0, 0
        width = int(doc.map["width"])
        height = int(doc.map["height"])
        self._size = Vector2(width, height)

        tileWidth, tileHeight = 0, 0
        tileWidth = int(doc.map["tilewidth"])
        tileHeight = int(doc.map["tileheight"])
        self._tileSize = Vector2(tileWidth, tileHeight)

        try:
            if len(doc.map.tileset) == 0:
                firstgid = 0
                source = doc.map.tileset["source"]
                xmlPath = PATHNAME + "/../Resources/maps/" + source
                xmlss = untangle.parse(xmlPath)
                ss = PATHNAME + "/../Resources/maps/" + xmlss.tileset.image["source"]
                #ss = source
                firstgid = int(doc.map.tileset["firstgid"])
                tex = SDL_CreateTextureFromSurface(graphics._renderer, graphics.loadImage(ss))
                self._tilesets.append(Tileset(tex, firstgid))

            else:
                for i in range(0, len(doc.map.tileset)):
                    firstgid = 0
                    source = doc.map.tileset[i]["source"]
                    xmlPath = PATHNAME + "/../Resources/maps/" + source
                    xmlss = untangle.parse(xmlPath)
                    ss = PATHNAME + "/../Resources/maps/" + xmlss.tileset.image["source"]
                    #ss = source
                    firstgid = int(doc.map.tileset[i]["firstgid"])
                    tex = SDL_CreateTextureFromSurface(graphics._renderer, graphics.loadImage(ss))
                    self._tilesets.append(Tileset(tex, firstgid))

        except AttributeError:
            pass

        #Loading Layers

        try:
            for k in range(0, len(doc.map.layer)): #len(doc.map)
                try:
                    if len(doc.map.layer[k].data) == 1:
                      pass

                    else:   #else multiple tile tags
                        tileCounter = 0
                        for i in range(0, len(doc.map.layer[k].data)):
                            if doc.map.layer[k].data.tile[i]["gid"] == 0:
                                tileCounter += 1
                                if i < (len(doc.map.layer[k].data)):
                                    continue
                                else:
                                    break
                            try:
                                gid = int(doc.map.layer[k].data.tile[i]["gid"])
                            except TypeError:
                                gid = 0
                            
                            if gid == 0:
                                tileCounter += 1
                                if i < (len(doc.map.layer[k].data)):
                                    continue
                                else:
                                    break

                            tls = Tileset()
                            for i in range(0, len(self._tilesets)):
                                if self._tilesets[i].FirstGid <= gid:
                                    tls = self._tilesets[i]
                                    break
                            
                            if tls.FirstGid == -1:
                                tileCounter += 1
                                if i < (len(doc.map.layer[k].data)):
                                    continue
                                else:
                                    break

                            xx = 0
                            yy = 0
                            xx = tileCounter % width
                            xx *= tileWidth
                            yy += tileHeight * (tileCounter // width)#
                            finalTilePosition = Vector2(xx, yy)

                            tilesetWidth, tilesetHeight = 256, 80   #0, 0
                            SDL_QueryTexture(tls.Texture, None, None, byref(c_int(tilesetWidth)), byref(c_int(tilesetHeight)))
                            tsxx = gid % (tilesetWidth // tileWidth) - 1
                            tsxx *= tileWidth
                            tsyy = 0
                            amt = int((gid // (tilesetWidth // tileWidth)))#
                            tsyy = tileHeight * amt
                            finalTilesetPosition = Vector2(tsxx, tsyy)

                            tile = Tile(tls.Texture, Vector2(tileWidth, tileHeight), finalTilesetPosition, finalTilePosition)
                            self._tileList.append(tile)
                            tileCounter += 1

                except (AttributeError, IndexError):
                    traceback.print_exc()
                    #print(e)
                    pass


        except (AttributeError, IndexError):
            traceback.print_exc()
            #print(e)
            pass

        #Load Collisions
        #try:
        for i in range(0, len(doc.map.objectgroup)):
            name = doc.map.objectgroup[i]["name"]
            if name == "collisions":
                for j in range(0, len(doc.map.objectgroup[i])):
                    x, y, width, height = 0, 0, 0, 0
                    x = float(doc.map.objectgroup[i].object[j]["x"])
                    y = float(doc.map.objectgroup[i].object[j]["y"])
                    width = float(doc.map.objectgroup[i].object[j]["width"])
                    height = float(doc.map.objectgroup[i].object[j]["height"])
                    self._collisionRects.append(Rectangle(math.ceil(x) * GLOBAL.SPRITE_SCALE, math.ceil(y) * GLOBAL.SPRITE_SCALE, math.ceil(width) * GLOBAL.SPRITE_SCALE, math.ceil(height) * GLOBAL.SPRITE_SCALE))
            if name == "slopes":
                for j in range(0, len(doc.map.objectgroup[i])):
                    points = []
                    p1 = Vector2(math.ceil(float(doc.map.objectgroup[i].object[j]["x"])), math.ceil(float(doc.map.objectgroup[i].object[j]["y"])))
                    pairs = []
                    pointString = doc.map.objectgroup[i].object[j].polyline["points"]
                    pairs.append(pointString.split(' '))

                    for k in range(0, len(pairs[0])):
                        ps = []
                        ps.append(pairs[0][k].split(","))
                        points.append(Vector2(int(math.ceil(float(ps[0][0]))), int(math.ceil(float(ps[0][1])))))
                    
                    for k in range(0, len(points), 2):
                        if k < 2:
                            self._slopes.append(Slope(Vector2((p1.x + points[k].x) * GLOBAL.SPRITE_SCALE, (p1.y + points[k].y) * GLOBAL.SPRITE_SCALE), Vector2((p1.x + points[k + 1].x) * GLOBAL.SPRITE_SCALE, (p1.y + points[k + 1].y) * GLOBAL.SPRITE_SCALE)))
                        else:
                            self._slopes.append(Slope(Vector2((p1.x + points[k - 1].x) * GLOBAL.SPRITE_SCALE, (p1.y + points[k - 1].y) * GLOBAL.SPRITE_SCALE), Vector2((p1.x + points[k].x) * GLOBAL.SPRITE_SCALE, (p1.y + points[k].y) * GLOBAL.SPRITE_SCALE)))

            if name == "spawn points":
                if len(doc.map.objectgroup[i]) == 1:
                    x = float(doc.map.objectgroup[i].object["x"])
                    y = float(doc.map.objectgroup[i].object["y"])
                    name = doc.map.objectgroup[i].object["name"]
                    if name == "player":
                        self._spawnPoint = Vector2(math.ceil(x) * GLOBAL.SPRITE_SCALE, math.ceil(y) * GLOBAL.SPRITE_SCALE)
                else: 
                    for j in range(0, len(doc.map.objectgroup[i])):
                        x = float(doc.map.objectgroup[i].object[j]["x"])
                        y = float(doc.map.objectgroup[i].object[j]["y"])
                        name = doc.map.objectgroup[i].object[j]["name"]
                        if name == "player":
                            self._spawnPoint = Vector2(math.ceil(x) * GLOBAL.SPRITE_SCALE, math.ceil(y) * GLOBAL.SPRITE_SCALE)


    
class Tile(object):
    def __init__(self, tileset, size, tilesetPosition, position):
        self._tileset = tileset
        self._size = size
        self._tilesetPostion = tilesetPosition
        self._position = Vector2(position.x * GLOBAL.SPRITE_SCALE, position.y * GLOBAL.SPRITE_SCALE)

    def update(self, elapsedTime):
        pass

    def draw(self, graphics):
        destRect = SDL_Rect(int(self._position.x), int(self._position.y), self._size.x * GLOBAL.SPRITE_SCALE, self._size.y * GLOBAL.SPRITE_SCALE)
        sourceRect = SDL_Rect(self._tilesetPostion.x, self._tilesetPostion.y, self._size.x, self._size.y)

        graphics.blitSurface(self._tileset, sourceRect, destRect)


class Game(object):
    def __init__(self):
        SDL_Init(SDL_INIT_EVERYTHING)
        self.gameLoop()

    def gameLoop(self):
        graphics = Graphics()
        input = Input()
        event = SDL_Event()

        self._level = Level("Map 1", Vector2(100, 100), graphics)
        self._player = Player(graphics, self._level._spawnPoint)

        LAST_UPDATE_TIME = SDL_GetTicks()

        while True:
            input.beginNewFrame()

            if (SDL_PollEvent(byref(event))):
                if (event.type == SDL_KEYDOWN):
                    if (event.key.repeat == 0):
                        input.keyDownEvent(event)
                
                elif (event.type == SDL_KEYUP):
                    input.keyUpEvent(event)

                elif (event.type == SDL_QUIT):
                    return

            if (input.wasKeyPressed(SDL_SCANCODE_ESCAPE) == True):
                return

            elif (input.isKeyHeld(SDL_SCANCODE_LEFT) == True):
                self._player.moveLeft()

            elif (input.isKeyHeld(SDL_SCANCODE_RIGHT) == True):
                self._player.moveRight()

            if (input.isKeyHeld(SDL_SCANCODE_Z) == True):
                self._player.jump()

            if (input.isKeyHeld(SDL_SCANCODE_1) == True):
                self._level = Level("Map 1", Vector2(100, 100), graphics)
                self._player = Player(graphics, self._level._spawnPoint)
                LAST_UPDATE_TIME = SDL_GetTicks()
                continue
            
            if (input.isKeyHeld(SDL_SCANCODE_2) == True):
                self._level = Level("Map 2", Vector2(100, 100), graphics)
                self._player = Player(graphics, self._level._spawnPoint)
                LAST_UPDATE_TIME = SDL_GetTicks()
                continue

            if (not input.isKeyHeld(SDL_SCANCODE_LEFT) and not input.isKeyHeld(SDL_SCANCODE_RIGHT)):
                self._player.stopMoving()

            CURRENT_TIME_MS = SDL_GetTicks()
            ELAPSED_TIME_MS = CURRENT_TIME_MS - LAST_UPDATE_TIME
            self.update(min([ELAPSED_TIME_MS, MAX_FRAME_TIME]))
            LAST_UPDATE_TIME = CURRENT_TIME_MS

            self.draw(graphics)

    def draw(self, graphics):
        graphics.clear()

        self._level.draw(graphics)
        self._player.draw(graphics)

        graphics.flip()

    def update(self, elapsedTime):
        self._player.update(elapsedTime)
        self._level.update(elapsedTime)

        others = []
        others = self._level.checkTileCollisions(self._player._boundingBox)
        if (len(others) > 0):
            self._player.handleTileCollisions(others)

        otherSlopes = []
        otherSlopes = self._level.checkSlopeCollisions(self._player._boundingBox)
        if (len(otherSlopes) > 0):
            self._player.handleSlopeCollisions(otherSlopes)

class Input(object):
    def __init__(self):
        self._heldKeys = {}
        self._pressedKeys = {}
        self._releasedKeys = {}

    def beginNewFrame(self):
        self._pressedKeys.clear()
        self._releasedKeys.clear()

    def keyUpEvent(self, event):
        self._releasedKeys[event.key.keysym.scancode] = True
        self._heldKeys[event.key.keysym.scancode] = False

    def keyDownEvent(self, event):
        self._pressedKeys[event.key.keysym.scancode] = True
        self._heldKeys[event.key.keysym.scancode] = True

    def wasKeyPressed(self, key):
        try:
            return self._pressedKeys[key]
        except KeyError:
            return False

    def wasKeyReleased(self, key):
        try:
            return self._releasedKeys[key]
        except KeyError:
            return False

    def isKeyHeld(self, key):
        try:
            return self._heldKeys[key]
        except KeyError:
            return False


game = Game()
