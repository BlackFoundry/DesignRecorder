# -*- coding: utf8 -*-

from drawBot import *
from vanilla import *
from mojo.events import addObserver, removeObserver
from mojo.roboFont import OpenWindow
from drawBot.ui.drawView import DrawView
from fontTools.pens.cocoaPen import CocoaPen
from defconAppKit.windows.baseWindow import BaseWindowController
import json
from robofab.pens.digestPen import DigestPointPen
from robofab.pens.adapterPens import PointToSegmentPen
import copy
import os
import time


class MainController(BaseWindowController):
    def __init__(self):
        self.w = FloatingWindow((200, 170), "Design Recorder")
        self.changeObserver = False
        self.font = CurrentFont()
        self.fontFileName = os.path.split(self.font.path)[1]
        self.storedGlyphPaths = {}
        self.observed = []
        self.w.statusTextBox = TextBox((10, 10, -10, 20), u"⚪️", alignment='center')
        self.w.toggle = Button((10, 30, -10, 20), "Record", callback=self.toggleCallBack)
        self.w.fillStroke = RadioGroup((10, 60, -10, 20), ["Fill", "Stroke"], isVertical=False)
        self.w.fillStroke.set(0)
        self.w.formatWidth = EditText((10, 90, 70, 20), '1280')
        self.w.formatx = TextBox((80, 90, 40, 20), u"✖", alignment='center')
        self.w.formatHeight = EditText((120, 90, 70, 20), '720')
        self.w.typeSizeTextBox = TextBox((10, 110, 100, 20), "Type Size:")
        self.w.typeSizeEditText = EditText((120, 110, 70, 20), '650')
        self.w.loadStory = Button((10, 140, -10, 20), "Load Record", callback=self.loadStoryButtonCallback)
        self.w.bind('close', self.closeCallback)
        addObserver(self, "fontBecameCurrent", "fontBecameCurrent")
        addObserver(self, "glyphChanged", "draw")
        for f in AllFonts():
            for g in f:
                self.initialise(g)
        self.w.center()
        self.w.open()
        
    def toggleCallBack(self, sender):
        if not self.changeObserver:
            self.showGetFolder(callback=self.selectOutputFolder)
            self.changeObserver = not self.changeObserver
            self.w.toggle.setTitle('Stop')
            self.w.statusTextBox.set(u'🔴')
        else:
            self.changeObserver = not self.changeObserver
            self.w.toggle.setTitle('Record')
            self.w.statusTextBox.set(u'⚪️')
            self.stopRecording()

    def initialise(self, g):
        font = g.getParent()
        if (os.path.split(font.path)[1], g.name) not in self.observed:
            self.observed.append( (os.path.split(font.path)[1], g.name) )
            path, width = self.makePathAndGetWidth(g)
            if (os.path.split(font.path)[1], g.name) in self.storedGlyphPaths:
                if len( self.storedGlyphPaths[(os.path.split(font.path)[1], g.name)] ) < 1:
                    self.storedGlyphPaths[(os.path.split(font.path)[1], g.name)] = [(path, width)]
            else:
                self.storedGlyphPaths[(os.path.split(font.path)[1], g.name)] = [(path, width)]

    def glyphChanged(self, notification):
        glyph = notification['glyph']
        if (self.fontFileName, glyph.name) in self.storedGlyphPaths:
            path, width = self.makePathAndGetWidth(glyph)
            if (path, width) != ( self.storedGlyphPaths[ (self.fontFileName, glyph.name)][-1][0], self.storedGlyphPaths[ (self.fontFileName, glyph.name)][-1][1] ):
                self.storedGlyphPaths[(self.fontFileName, glyph.name)].append( (path, width) )

    def makePathAndGetWidth(self, glyph):
        g = glyph.copy()
        components = glyph.getComponents()
        if components:
            g.setParent(glyph.getParent())
            g.decompose()
        return self._glypPath(g), g.width
                
    def closeCallback(self, sender):
        self.stopRecording()
        removeObserver(self, "fontBecameCurrent")
        removeObserver(self, "currentGlyphChanged")
        
    def fontBecameCurrent(self, notification):
        self.font = notification['font']
        self.fontFileName = os.path.split(self.font.path)[1]
        for g in self.font:
            self.initialise(g)

    def currentGlyphChanged(self, notification):
        self.initialise(notification['glyph'])

    def selectOutputFolder(self, sender):
        self.folderPath = sender
    
    def saveJsonCallback(self, sender):
        with open(sender, "w") as file: 
            self.jsonFile = sender

    def loadStoryButtonCallback(self, sender):
        self.fill = self.w.fillStroke.get()
        self.filePath = self.showGetFile(['designRecord'], callback=self.loadStoryCallback)

    def loadStoryCallback(self, sender):
        width = int(self.w.formatWidth.get())
        height = int(self.w.formatHeight.get())
        typeSize = int(self.w.typeSizeEditText.get())
        with open(sender[0], "r") as file:
            story = json.load(file)
            self.makeAnim(story, width, height, typeSize)

    def stopRecording(self):
        self.writeStory(self.folderPath)

    def writeStory(self, folderPath):
        print 'writing story...'
        for (fontFileName, glyphname), storedPaths in self.storedGlyphPaths.iteritems():
            if len(storedPaths) > 1:
                name = ''
                for char in glyphname:
                    c = char
                    if char.isupper:
                        c = char + '_'
                    name += c
                jsonFile = os.path.join(folderPath[0], fontFileName.split('.')[0] + '_' + name + '.designRecord')
                with open(jsonFile, "w") as file:        
                    file.write(json.dumps(storedPaths, file, sort_keys=False))
    
    def makeAnim(self, storedGlyphs, width, height, typeSize):
        print 'making animation...'
        dbw = Window((width, height+40))
        dbw.drawBotCanvas = DrawView((0, 0, -0, -40))
        dbw.saveMovieButton = Button((10, -30, -10, 20), 'Save Movie', callback=self.saveMovieButtonCallback)
        dbw.open()

        UPM = self.font.info.unitsPerEm
        desc = self.font.info.descender
        asc = self.font.info.ascender
        xHeight = self.font.info.xHeight
        
        box_Y = asc - desc

        pitch = 1.0*typeSize / height
        yPos = height*.5   - xHeight*.5*pitch
        newDrawing()
        for i, (path, gwidth) in enumerate(storedGlyphs):
            g = RGlyph()
            g.width = gwidth
            segmentPen = g.getPen()
            pen = PointToSegmentPen(segmentPen)
            count = i
            if path == 'idem':
                path = storedGlyphs[i-1]
                storedPath[i] = storedGlyphs[i-1]

            for i, cmd in enumerate(path):
                if cmd == 'beginPath':
                    pen.beginPath()
                elif cmd == 'endPath':
                    pen.endPath()
                else:
                    pen.addPoint(cmd[0], cmd[1], cmd[2], cmd[3])

            xPos = width*.5 - g.width*.5*pitch
            newPage(width, height)
            save()
            translate(xPos, yPos)
            if self.fill == 0:
                fill(0, 0, 0, 1)
                stroke(None)
            elif self.fill == 1:
                fill(None)
                stroke(0, 0, 0, 1)
            scale(pitch)
            self._drawGlyph(g)
            restore()
        pdfData = pdfImage()
        dbw.drawBotCanvas.setPDFDocument(pdfData)
        
    def _drawGlyph(self, glyph):
        pen = CocoaPen(glyph.getParent())
        glyph.draw(pen)
        drawPath(pen.path)
        
    def _glypPath(self, glyph):
        pen = DigestPointPen()
        glyph.drawPoints(pen)
        return pen.getDigest()
    
    def saveMovieButtonCallback(self, sender):
        print 'making movie... (please wait)'
        self.showPutFile(["mov"], callback=self.saveMovieFileCallback)
        
    def saveMovieFileCallback(self, sender):
        start = time.time()
        with open(sender, "w"):
            movieFile = sender
            saveImage([movieFile])
        end = time.time()
        print 'movie made in ' + str(int(end-start)) + ' seconds'

if CurrentFont():
    OpenWindow(MainController)