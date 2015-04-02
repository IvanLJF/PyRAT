from __future__ import print_function
import pyrat
import numpy as np
import logging
from PyQt4 import QtGui, QtCore
# from pyrat.filter.tools import rebin
from .Dialogs import ViewerTree
from pyrat.viewer.tools import sarscale
from .StatusBar import *
from . import egg

try:
    from pyrat.viewer.cytools import parallel_rebin as rebin
    from pyrat.viewer.cytools import parallel_abs as npabs
except ImportError:
    from pyrat.filter.tools import rebin
    from pyrat.viewer.tools import npabs
    print("Multi-threaded viewer components not found. (run build process?)")


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setWindowTitle("PyRAT - Radar Tools")

        self.box = [0, 100, 0, 100]
        self.size = [100, 100]
        self.factor = 1.0
        self.sarscale = 2.5
        self.type = 'A'

        self.block_redraw = False
        self.show_rubberband = False
        self.undolist = []

        self.makeActions()
        self.makeToolbar()
        self.makeStatusBar()
        self.makeMenu()
        self.makeView()
        self.initPlugins()
        self.resize(1000, 800)
        self.central.setSizes([150, 800])
        self.show()
        self.rubberband = QtGui.QRubberBand(QtGui.QRubberBand.Rectangle, self.imageLabel)

        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+T"), self, self.easterEgg)
        # self.setMinimumSize(100+self.width()-self.central.width(), 100+self.height()-self.central.height())
        self.central.setMinimumSize(100, 100)

    # -------------------------------- TOOL BAR
    def makeToolbar(self):
        self.openTB = QtGui.QAction(QtGui.QIcon('icons/document-open.png'), 'Open', self)
        self.closeTB = QtGui.QAction(QtGui.QIcon('icons/document-close.png'), 'Close', self)
        # self.zoominTB = QtGui.QAction(QtGui.QIcon('icons/zoom-in.png'), 'Zoom in', self)
        #self.zoomoutTB = QtGui.QAction(QtGui.QIcon('icons/zoom-out.png'), 'Zoom out', self)
        #self.zoomresetTB = QtGui.QAction(QtGui.QIcon('icons/zoom-fit-best.png'), 'Fit zoom', self)
        self.seperatorTB = QtGui.QAction(self)

        self.toolbar1 = self.addToolBar("File")
        self.toolbar1.addAction(self.openTB)
        self.toolbar1.addAction(self.closeTB)

        self.toolbar2 = self.addToolBar("Display")
        self.toolbar2.addAction(self.zoomOutAct)
        self.viewCombo = QtGui.QComboBox(self)
        self.viewCombo.insertItems(1, ["100%", "Fit to window", "Fit to width", "Fit to height", "100%"])
        self.viewCombo.setEditable(False)
        self.viewCombo.activated.connect(self.comboZoom)
        self.toolbar2.addWidget(self.viewCombo)
        self.toolbar2.addAction(self.zoomInAct)

        #self.toolbar3 = self.addToolBar("Layer")
        #self.toolbar3.addAction(self.zoominTB)
        #self.toolbar3.addAction(self.zoomresetTB)

    # -------------------------------- STATUS BAR
    def makeStatusBar(self):
        self.statusBar = StatusBar(self)
        self.statusBar.setMessage(message='no data loaded')

    #-------------------------------- DEFAULT ACTIONS (only those not implemented trough plugins)
    def makeActions(self):
        self.exitAct = QtGui.QAction('Exit', self, shortcut='Q', triggered=self.close)
        self.zoomInAct = QtGui.QAction(QtGui.QIcon('icons/zoom-in.png'), "Zoom &In (25%)", self, shortcut="up",
                                       triggered=lambda: self.zoom(3.0 / 2.0))
        self.zoomOutAct = QtGui.QAction(QtGui.QIcon('icons/zoom-out.png'), "Zoom &Out (25%)", self, shortcut="down",
                                        triggered=lambda: self.zoom(2.0 / 3.0))
        self.fitToWindowAct = QtGui.QAction(QtGui.QIcon('icons/zoom-fit-best.png'), "Reset view", self, shortcut="f",
                                            triggered=self.resetView)
        self.viewAmpAct = QtGui.QAction("View as amplitude", self, checkable=True, shortcut="1",
                                        triggered=self.viewAsAmplitude)
        self.viewPhaAct = QtGui.QAction("View as phase", self, checkable=True, shortcut="2", triggered=self.viewAsPhase)
        self.viewCohAct = QtGui.QAction("View as coherence", self, checkable=True, shortcut="3",
                                        triggered=self.viewAsCoherence)
        self.viewBrighter = QtGui.QAction("View brighter", self, shortcut="right", triggered=self.brighterView)
        self.viewDarker = QtGui.QAction("View darker", self, shortcut="left", triggered=self.darkerView)
        self.undoAct = QtGui.QAction('Undo', self, shortcut='Ctrl+z', triggered=self.undo)

    def easterEgg(self):
        tetris = egg.Tetris(self)
        tetris.show()

    #---------------------------------- PLUGINS
    def initPlugins(self):
        from inspect import getmembers, isclass
        modules = [pyrat.filter, pyrat.load, pyrat.save, pyrat.transform, pyrat.polar, pyrat.plugins, pyrat.viewer]
        logging.debug("Scanning for GUI elements:")
        for current_module in modules:
            modules = getmembers(current_module, isclass)
            for mod in modules:
                if issubclass(mod[1], pyrat.Worker):
                    # plugin = mod[1]()
                    plugin = mod[1]
                    if hasattr(plugin, 'gui'):
                        logging.debug(" Attaching GUI element : "+mod[0])
                        plugin.registerGUI(self)


    def makeMenu(self):
        self.menubar = self.menuBar()
        self.menue = {
            "File": self.menubar.addMenu('File'),
            "General": self.menubar.addMenu('General'),
            "Tools": self.menubar.addMenu('Tools'),
            "SAR": self.menubar.addMenu('SAR'),
            "PolSAR": self.menubar.addMenu('PolSAR'),
            "Help": self.menubar.addMenu('Help')}

        self.menue.update({"File|Open external": self.menue["File"].addMenu('Open external')})
        # self.menue.update({"File|Open pixmap": self.menue["File"].addMenu('Open pixmap')})
        foo = self.menue["File"].addSeparator()
        foo.setWhatsThis("File|line1")


        # self.menue.update({"File|Save external": self.menue["File"].addMenu('Save external')})
        # self.menue.update({"File|Save pixmap": self.menue["File"].addMenu('Save pixmap')})
        self.menue["File"].addSeparator()
        self.menue["File"].addAction(self.exitAct)

        self.menue["General"].addAction(self.undoAct)
        self.menue["General"].addSeparator()
        self.menue["General"].addAction(self.fitToWindowAct)
        self.menue["General"].addAction(self.zoomInAct)
        self.menue["General"].addAction(self.zoomOutAct)
        self.menue["General"].addSeparator()
        self.menue["General"].addAction(self.viewBrighter)
        self.menue["General"].addAction(self.viewDarker)
        self.menue["General"].addSeparator()
        self.viewSel = QtGui.QActionGroup(self.menue["General"], exclusive=True)
        foo = self.viewSel.addAction(self.viewAmpAct)
        self.menue["General"].addAction(foo)
        foo = self.viewSel.addAction(self.viewPhaAct)
        self.menue["General"].addAction(foo)
        foo = self.viewSel.addAction(self.viewCohAct)
        self.menue["General"].addAction(foo)

        self.menue.update({"SAR|Speckle filter": self.menue["SAR"].addMenu('Speckle filter')})
        self.menue.update({"SAR|Edge detection": self.menue["SAR"].addMenu('Edge detection')})
        self.menue.update({"SAR|Texture": self.menue["SAR"].addMenu('Texture')})
        self.menue.update({"SAR|line1": self.menue["SAR"].addSeparator()})
        self.menue.update({"SAR|Sidelobe control": self.menue["SAR"].addMenu('Sidelobe control')})
        self.menue.update({"SAR|Spectral tools": self.menue["SAR"].addMenu('Spectral tools')})
        self.menue.update({"SAR|line2": self.menue["SAR"].addSeparator()})
        self.menue.update({"SAR|Transform": self.menue["SAR"].addMenu('Transform')})
        self.menue.update({"PolSAR|Calibration": self.menue["PolSAR"].addMenu('Calibration')})
        self.menue.update({"PolSAR|Speckle filter": self.menue["PolSAR"].addMenu('Speckle filter')})
        self.menue.update({"PolSAR|Change detection": self.menue["PolSAR"].addMenu('Change detection')})
        self.menue.update({"PolSAR|Decompositions": self.menue["PolSAR"].addMenu('Decompositions')})
        self.menue.update({"PolSAR|Parameters": self.menue["PolSAR"].addMenu('Parameters')})
        self.menue.update({"PolSAR|Transform": self.menue["PolSAR"].addMenu('Transform')})
        self.menue.update({"Tools|Geometry": self.menue["Tools"].addMenu('Geometry')})

        #self.menue["View"].addAction(self.viewAmpAct)
        #self.menue["View"].addAction(self.viewPhaAct)
        #self.menue["View"].addAction(self.viewCohAct)

    #---------------------------------- VIEW AREA
    def makeView(self):
        from pyrat.viewer.Widgets import DelayedUpdater

        # self.central = QtGui.QWidget()
        # self.HLayout = QtGui.QHBoxLayout(self.central)
        self.central = QtGui.QSplitter(self)
        self.central.setOpaqueResize(False)
        self.central.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)

        self.tree = ViewerTree()
        # self.tree.setFixedWidth(200)
        # self.tree.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Expanding)
        self.central.addWidget(self.tree)

        # self.HLayout.addItem(self.spacer)

        self.frame = QtGui.QWidget()
        # self.frame = DelayedUpdater()

        self.frame.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.imageLabel = QtGui.QLabel(self.frame)
        self.imageLabel.setBackgroundRole(QtGui.QPalette.Base)
        self.imageLabel.setStyleSheet("QLabel { background-color: #333 }")
        self.imageLabel.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.imageLabel.setScaledContents(False)
        self.imageLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.imageLabel.resize(self.frame.width(), self.frame.height())
        self.central.addWidget(self.frame)

        self.setCentralWidget(self.central)

        self.resizeframeevent = self.frame.resizeEvent
        self.frame.resizeEvent = self.resizeFrameEvent   # a bit dirtyt to overload like this...

        # self.central.move.connect(lambda: self.splitterMoved())

        # self.frame = QtGui.QWidget()
        # self.imageLabel = QtGui.QLabel(self.frame)
        # self.imageLabel.setBackgroundRole(QtGui.QPalette.Base)
        # self.imageLabel.setStyleSheet("QLabel { background-color: #333 }")
        # self.imageLabel.setSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Ignored)
        # self.imageLabel.setScaledContents(False)
        # self.imageLabel.resize(self.frame.width(), self.frame.height())
        # self.setCentralWidget(self.frame)

    # def split(self, event):
    #     # QtGui.QWidget.resizeEvent(self.frame, event)
    #     # self.central.update()
    #     self.resizeEvent(event)
    #     # self.central.update()
    #     print("Event", self.frame.width(), self.frame.height())

    def updateViewer(self):

        self.updateTree()
        if len(pyrat.data.active) > 0:
            self.statusBar.setMessage(message=' Updating view ', colour='R')
            self.statusBar.progressbar.setValue(50)
            self.genPyramid(pyrat.data.getData(layer=pyrat.data.active))
            self.processPicture(fitwin=1)
            self.statusBar.setMessage(message=' Ready ', colour='G')
            self.statusBar.progressbar.setValue(0)

            self.undolist.append((list(pyrat.data.getLayerNames()), pyrat.data.active))
        else:
            if hasattr(self, "data"):
                del self.data
            self.imageLabel.setPixmap(QtGui.QPixmap())


    def updateTree(self):
        self.tree.delTree()

        layers = pyrat.data.getLayerNames()
        if isinstance(layers, str):
            layers = [layers]
        channels = {}
        for layer in layers:
             channels.update({layer: pyrat.data.getDataLayerNames(layer=layer)})
        self.tree.addLayers(channels)

        if len(pyrat.data.active) > 0:
            self.tree.activateRow(pyrat.data.active)


    def delLayer(self, layer):
        pyrat.data.delLayer(layer)
        self.updateViewer()

    def activateLayer(self, layer):
        pyrat.data.activateLayer(layer)
        self.updateViewer()

#-----------------------------------------------------------
#-----------------------------------------------------------
#-----------------------------------------------------------
#-----------------------------------------------------------
    def genPyramid(self, data, **kargs):
        if isinstance(data, list):
            data = data[0]
        # data[~np.isfinite(data)] = 0.0
        if data.ndim == 3:
            self.colour = True
            dshape = data.shape
            dmin = dshape.index(min(dshape))
            if dmin == 0:
                data = np.rollaxis(np.rollaxis(data, 2), 2)
            elif dmin == 1:
                data = np.rollaxis(data, 2, 1)
            else:
                pass
            dshape = data.shape
            if dshape[2] < 3:
                data = np.append(data, data[..., 0:1], axis=2)
            if dshape[2] > 3:
                data = data[..., 0:3]
        elif data.ndim == 4:
            self.colour = True
            dshape = data.shape
            dmin = dshape.index(min(dshape))
            if dmin == 0:
                data = np.rollaxis(np.rollaxis(data, 3), 3)
            else:
                pass
            data = np.diagonal(data,axis1=2,axis2=3)
            dshape = data.shape
            if dshape[2] < 3:
                data = np.append(data, data[..., 0:1], axis=2)
            if dshape[2] > 3:
                data = data[..., 0:3]
        else:
            self.colour = False

        if self.type == 'P' and np.iscomplexobj(data):
            data = [np.angle(data)]
        elif np.iscomplexobj(data):
            data = [npabs(data, threads=pyrat.pool._processes)]
        else:
            data = [data]
        # data[0][np.isnan(data[0])] = 0.0
        scale = 0
        lange = min(data[scale].shape)

        while lange > 1:
            cut = np.array(data[scale].shape[0:2]) // 2 * 2
            newdim = np.array(data[scale].shape[0:2]) // 2
            if self.colour is True:
                newdim = np.append(newdim, 3)
            if self.type == 'P':
                data.append(rebin(data[scale][:cut[0], :cut[1], ...], newdim, phase=True, threads=pyrat.pool._processes))
            else:
                data.append(rebin(data[scale][:cut[0], :cut[1], ...], newdim, threads=pyrat.pool._processes))
            scale += 1
            lange = min(data[scale].shape)
        self.data = data
        self.size = data[0].shape[0:2][::-1]  # [xmin,xmax,ymin,ymax]

    def data2img(self, cut_box, scale=0):
        if self.data[scale].dtype == 'uint8':
            img = self.data[scale][cut_box[2]:cut_box[3], cut_box[0]:cut_box[1], ...]
        elif self.type == 'P':
            img = np.uint8(
                np.clip(self.data[scale][cut_box[2]:cut_box[3], cut_box[0]:cut_box[1], ...] / np.pi * 128 + 127, 0.0, 255.0))
            self.viewPhaAct.setChecked(True)
        elif self.type == 'C':
            img = np.uint8(np.clip(self.data[scale][cut_box[2]:cut_box[3], cut_box[0]:cut_box[1], ...] * 255.0, 0.0, 255.0))
            self.viewCohAct.setChecked(True)
        elif self.type == 'A':
            img = self.data[scale][cut_box[2]:cut_box[3], cut_box[0]:cut_box[1], ...].copy()
            if self.colour is True:
                for k in range(img.shape[2]): img[..., k] /= np.mean(img[..., k])
            img = sarscale(img, factor=self.sarscale)
            self.viewAmpAct.setChecked(True)
        else:
            img = np.uint8(self.data[scale][cut_box[2]:cut_box[3], cut_box[0]:cut_box[1], ...])

        img = img[0:img.shape[0] // 4 * 4, 0:img.shape[1] // 4 * 4, ...]  # QT Limitation,

        if self.colour is True:
            return QtGui.QImage(img.tostring(), img.shape[1], img.shape[0],
                                QtGui.QImage.Format_RGB888)  # convert to Qimage
        else:
            return QtGui.QImage(img.tostring(), img.shape[1], img.shape[0],
                                QtGui.QImage.Format_Indexed8)  # convert to Qimage

    def processPicture(self, **kwargs):
        if "fitwin" in kwargs.keys():
            self.scale = len(self.data) - 1
            while self.scale >= 0:
                if self.data[self.scale].shape[1] > self.imageLabel.width() or self.data[self.scale].shape[
                    0] > self.imageLabel.height(): break
                self.scale -= 1
            self.box = [0, self.size[0], 0, self.size[1]]
            cut_box = [foo // 2 ** self.scale for foo in self.box]
        else:
            self.scale = len(self.data) - 1
            while self.scale >= 0:
                cut_box = [foo // 2 ** self.scale for foo in self.box]
                #print cut_box
                if cut_box[1] - cut_box[0] > self.imageLabel.width() or cut_box[3] - cut_box[
                    2] > self.imageLabel.height(): break
                self.scale -= 1
        self.scale = np.clip(self.scale, 0, len(self.data) - 1)

        img = self.data2img(cut_box, scale=self.scale)

        xWin = self.imageLabel.width()
        yWin = self.imageLabel.height()
        winRatio = 1.0 * xWin / yWin

        self.width = img.width()
        self.height = img.height()

        imgRatio = 1.0 * self.width / self.height

        if imgRatio >= winRatio:  #match widths
            self.width = xWin
            self.height = xWin / imgRatio
        else:  #match heights
            self.height = yWin
            self.width = yWin * imgRatio

        self.factor = int(100.0 * self.width / (self.box[1] - self.box[0]))
        if self.factor <= 100:
            img = img.scaled(int(self.width), int(self.height))  # Bilinear?
        else:
            img = img.scaled(int(self.width), int(self.height))  # Nearest Neighbour

        self.statusBar.setMessage(size=1, zoom=1, level=1, scale=1)
        self.viewCombo.setItemText(0, str(int(self.factor)) + '%')

        colortable = [QtGui.qRgb(i, i, i) for i in range(256)]
        img.setColorTable(colortable)
        self.imageLabel.setPixmap(QtGui.QPixmap.fromImage(img))

    def zoom(self, factor, mx=0, my=0):
        px = self.box[0] + int(
            (1.0 * self.box[1] - self.box[0]) / self.imageLabel.width() * (mx + self.imageLabel.width() // 2))
        py = self.box[2] + int(
            (1.0 * self.box[3] - self.box[2]) / self.imageLabel.height() * (my + self.imageLabel.height() // 2))

        midx = self.box[0] + (self.box[1] - self.box[0]) // 2
        midy = self.box[2] + (self.box[3] - self.box[2]) // 2
        sizx = self.box[1] - self.box[0]
        sizy = self.box[3] - self.box[2]
        newx = np.clip(int(sizx / factor), 0, self.size[0])
        newy = np.clip(int(sizy / factor), 0, self.size[1])
        imgRatio = 1.0 * newx / newy
        xWin = self.imageLabel.width()
        yWin = self.imageLabel.height()
        winRatio = 1.0 * xWin / yWin
        if imgRatio >= winRatio:  #match widths:
            newy = np.clip(int(newx / winRatio), 0, self.size[1])
        else:
            newx = np.clip(int(newy * winRatio), 0, self.size[0])
        newx = np.clip(newx, 4, self.size[0])
        newy = np.clip(newy, 4, self.size[1])
        if midx - newx // 2 < 0:            midx = newx // 2
        if midx + newx // 2 > self.size[0]: midx = self.size[0] - newx // 2
        if midy - newy // 2 < 0:            midy = newy // 2
        if midy + newy // 2 > self.size[1]: midy = self.size[1] - newy // 2
        self.box = [midx - newx // 2, midx + newx // 2, midy - newy // 2, midy + newy // 2]

        if mx != 0 and my != 0:
            midx = px - int((1.0 * self.box[1] - self.box[0]) / self.imageLabel.width() * mx)
            midy = py - int((1.0 * self.box[3] - self.box[2]) / self.imageLabel.height() * my)
            sizx = self.box[1] - self.box[0]
            sizy = self.box[3] - self.box[2]
            if midx - sizx // 2 < 0:            midx = sizx // 2
            if midx + sizx // 2 > self.size[0]: midx = self.size[0] - sizx // 2
            if midy - sizy // 2 < 0:            midy = sizy // 2
            if midy + sizy // 2 > self.size[1]: midy = self.size[1] - sizy // 2
            self.box = [midx - sizx // 2, midx + sizx // 2, midy - sizy // 2, midy + sizy // 2]
        if hasattr(self, 'data'):
            self.processPicture()

    def undo(self):
        if len(self.undolist) >= 2:
            actual = set(self.undolist[-1][0])
            before = set(self.undolist[-2][0])
            diff = actual.difference(before)
            pyrat.data.activateLayer(self.undolist[-2][1])
            pyrat.data.delLayer(list(diff))
            self.undolist.pop()
            self.undolist.pop()
            self.updateViewer()

    def viewAsAmplitude(self):
        self.type = 'A'
        if hasattr(self, 'data'):
            self.processPicture()

    def viewAsCoherence(self):
        self.type = 'C'
        if hasattr(self, 'data'):
            self.processPicture()

    def viewAsPhase(self):
        self.type = 'P'
        if hasattr(self, 'data'):
            self.processPicture()

    def darkerView(self):
        self.sarscale += 0.5
        if hasattr(self, 'data'):
            self.processPicture()

    def brighterView(self):
        self.sarscale -= 0.5
        if self.sarscale < 0.5:
            self.sarscale = 0.5
        if hasattr(self, 'data'):
            self.processPicture()

    def resetView(self):
        self.sarscale = 2.5
        if hasattr(self, 'data'):
            self.processPicture(fitwin=1)

    def comboZoom(self, index):
        if index == 1:
            if hasattr(self, 'data'): self.processPicture(fitwin=1)
            self.viewCombo.setCurrentIndex(0)
        elif index == 2:
            print("Not implemented")
            self.viewCombo.setCurrentIndex(0)
        elif index == 3:
            print("Not implemented")
            self.viewCombo.setCurrentIndex(0)
        elif index == 4:
            print("Not implemented")
            self.viewCombo.setCurrentIndex(0)

    def resizeFrameEvent(self, event):
        if self.block_redraw is False:         # needed to avoid concurrent redraws -> segfault
            self.block_redraw = True
            self.imageLabel.setGeometry(0, 0, self.frame.width(), self.frame.height())
            midx = self.box[0] + (self.box[1] - self.box[0]) // 2
            midy = self.box[2] + (self.box[3] - self.box[2]) // 2
            sizx = self.box[1] - self.box[0]
            sizy = self.box[3] - self.box[2]
            newx = np.clip(int(sizx), 0, self.size[0])
            newy = np.clip(int(sizy), 0, self.size[1])
            imgRatio = 1.0 * newx / newy
            xWin = self.imageLabel.width()
            yWin = self.imageLabel.height()

            winRatio = 1.0 * xWin / yWin
            if imgRatio >= winRatio:  #match widths:
                newy = np.clip(int(newx / winRatio), 0, self.size[1])
            else:
                newx = np.clip(int(newy * winRatio), 0, self.size[0])
            midx -= (midx-newx // 2) * ((midx-newx // 2)<0)
            midy -= (midy-newy // 2) * ((midy-newy // 2)<0)

            self.box = [midx - newx // 2, midx + newx // 2, midy - newy // 2, midy + newy // 2]

            if hasattr(self, 'data'):
                self.processPicture()
            self.resizeframeevent(event)
            self.block_redraw = False

    def wheelEvent(self, event):
        if event.delta() < 0:
            self.zoom(2.0/3.0, mx=event.x()-self.imageLabel.width()//2, my=event.y()-self.imageLabel.height()//2)
        if event.delta() > 0:
            self.zoom(3.0/2.0, mx=event.x()-self.imageLabel.width()//2, my=event.y()-self.imageLabel.height()//2)
        if hasattr(self, 'data'):
            self.processPicture()

    def mousePressEvent(self, event):
        if self.show_rubberband is True:
            # self.origin = event.pos()
            self.origin = self.frame.mapFrom(self, event.pos())
            self.rubberband.setGeometry(QtCore.QRect(self.origin, QtCore.QSize()))
            self.rubberband.show()
        else:
            self.dragX = event.x()
            self.dragY = event.y()
        QtGui.QWidget.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self.show_rubberband is True:
            if self.rubberband.isVisible():
                self.rubberband.hide()
                self.show_rubberband = False
        else:
            if event.button() == 1:
                dx = int((1.0 * self.box[1] - self.box[0]) / self.imageLabel.width() * (self.dragX - event.x()))
                dy = int((1.0 * self.box[3] - self.box[2]) / self.imageLabel.height() * (self.dragY - event.y()))
                midx = self.box[0] + (self.box[1] - self.box[0]) // 2 + dx
                midy = self.box[2] + (self.box[3] - self.box[2]) // 2 + dy
                sizx = self.box[1] - self.box[0]
                sizy = self.box[3] - self.box[2]
                if midx - sizx // 2 < 0:            midx = sizx // 2
                if midx + sizx // 2 > self.size[0]: midx = self.size[0] - sizx // 2
                if midy - sizy // 2 < 0:            midy = sizy // 2
                if midy + sizy // 2 > self.size[1]: midy = self.size[1] - sizy // 2
                self.box = [midx - sizx // 2, midx + sizx // 2, midy - sizy // 2, midy + sizy // 2]
                if hasattr(self, 'data'):
                    self.processPicture()
                self.imageLabel.setGeometry(0, 0, self.frame.width(), self.frame.height())
        QtGui.QWidget.mouseReleaseEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.show_rubberband is True:
            if self.rubberband.isVisible():
                pos = self.frame.mapFrom(self, event.pos())
                # todo: limit size
                self.rubberband.setGeometry(QtCore.QRect(self.origin, pos).normalized())
        else:
            self.imageLabel.move(event.x()-self.dragX, event.y()-self.dragY)
        QtGui.QWidget.mouseMoveEvent(self, event)
