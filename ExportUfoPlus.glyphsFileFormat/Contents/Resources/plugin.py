# encoding: utf-8

from __future__ import division, print_function, unicode_literals
import objc
from collections import OrderedDict
from GlyphsApp import *
from GlyphsApp.plugins import *
import vanilla as vl
import GlyphsAppUfo.glyphsAppUfo as glyphsAppUfo
from GlyphsAppUfo.UI import UfoExporterTabs
from AppKit import NSPoint, NSSize
_DEBUG_ = False


class ExportUfoPlus(FileFormatPlugin):
	@objc.python_method
	def settings(self):
		self.tabIndex = 0
		self.selectedMasterIndexes = []
		self.masterIndexes = []
		self.use_production_names = False
		self.decompose_smart_stuff = False
		self.kerningAsFeatureText = False
		self.exporterView = UfoExporterTabs((0, 10, 0, 0), self)
		self.dialog = self.exporterView.getNSView()
		mask = 0
		self.dialog.setAutoresizingMask_(mask)
		self.dialog.setFrame_(NSRect(NSPoint(0, 0), NSSize(490, 520)))
		self.name = Glyphs.localize({'en': u'UFO+'})
		self.icon = 'UFOTemplate'
		self.toolbarPosition = 100

	def exportOptions(self):
		return {"selectedMasterIndexes": self.selectedMasterIndexes}
	
	def setExportOptions_(self, exportOptions):
		# master indices of previous object
		self.masterIndexes = exportOptions["selectedMasterIndexes"]

	@objc.python_method
	def export(self, font):
		try:
			self.exporterView.setFont(Glyphs.font)
			self.exporterView.export()
			return (True, 'The export was successful.')

		except Exception as error:
			import traceback
			traceback.print_tb(error)
			return (False, 'No file chosen')

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__

	def setFont_(self, GSFontObj):
		super(ExportUfoPlus, self).setFont_(GSFontObj)
		self.exporterView.setFont(GSFontObj)
