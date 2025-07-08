# MenuTitle:Ufo Export UI_test
# -*- coding: utf-8 -*-

from importlib import reload
import vanilla as vl
from GlyphsAppUfo import glyphsAppUfo
from GlyphsApp import Glyphs, Message, GetFolder
import sys
import os
import subprocess
pardir = os.path.abspath(os.path.join(__file__, os.pardir))
pardir = os.path.abspath(os.path.join(pardir, os.pardir))
libdir = pardir
sys.path += [libdir]
glyphsAppUfo = reload(glyphsAppUfo)
_DEBUG_ = False
_version_ = "0.0.0.1"
if _DEBUG_:
	import random
	print("ufoGlyphsOutput lib")
	print(_version_)
	__random_int__ = random.randint(0, 100)
	print("random int for attempt", __random_int__)


class UfoMasterExporterView(vl.Group):
	selectionTitle = "Select masters to export as UFO:"
	infoText = "Writes all selected masters as separate .ufo files.\nAll files at the chosen location will be overwritten"
	kerningDataOptions = [
		"... and export kerning as a part of UFO data",
		"export kerning as a part of feature text"
	]

	def __init__(self, posSize, plugin, ufoFactory):
		self.ufoFactory = ufoFactory
		self.font = None
		self.plugin = plugin

		super(UfoMasterExporterView, self).__init__(posSize)
		x, y, p = (10, 10, 10)
		btnH, txtH = (22, 17)
		self.txt01 = vl.TextBox((p * 2, y, -p * 2, txtH), self.selectionTitle)
		y += txtH + p * 2
		endOfList = -(btnH + p) * 4 - txtH * 3
		self.exportUfoList = vl.List((p * 2, y, -p * 2, endOfList), [], selectionCallback=self.selectionCallback)
		y = endOfList + p
		self.use_production_names = vl.CheckBox(
			(p * 2, y, -p * 2, btnH), "Convert glyph names to production names", callback=self.SavePreferences)
		y += btnH + p
		self.decompose_smart_stuff = vl.CheckBox(
			(p * 2, y, -p * 2, btnH), "Decompose smart stuff ...", callback=self.SavePreferences)
		y += btnH  #+ p
		self.kerningDataTypeRadio = vl.RadioGroup(
			(p * 3, y, -p * 2, btnH * 2), self.kerningDataOptions, callback=self.SavePreferences)
		self.kerningDataTypeRadio.set(0)
		y += 2 * btnH + p
		self.txt02 = vl.TextBox((p * 2, y, -p * 2, -p), self.infoText)

		if not self.LoadPreferences():
			print("Note: 'UfoGlyphsOutput.UfoMasterExporterView' could not load preferences. Will resort to defaults")

	def SavePreferences(self, sender):
		# update radio buttons as this is the callback for Decompose Smart Stuff:
		self.kerningDataTypeRadio.enable(self.decompose_smart_stuff.get())
		#if self.decompose_smart_stuff.get():
		#	self.kerningDataTypeRadio.enable(True)
		#	# this option would be better but there is an update glitch
		#	#self.kerningDataTypeRadio.enableRadioButton(0, True)
		#else:
		#	self.kerningDataTypeRadio.enable(False)
		#	# this option would be better but there is an update glitch
		#	#self.kerningDataTypeRadio.enableRadioButton(0, False)
		try:
			Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.use_production_names"] = self.use_production_names.get()
			Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.decompose_smart_stuff"] = self.decompose_smart_stuff.get()
			Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.kerningDataTypeRadio"] = self.kerningDataTypeRadio.get()
		except:
			return False

		return True

	def LoadPreferences(self):
		try:
			Glyphs.registerDefault("com.rafalbuchner.UfoGlyphsOutput.use_production_names", 0)
			Glyphs.registerDefault("com.rafalbuchner.UfoGlyphsOutput.decompose_smart_stuff", 0)
			Glyphs.registerDefault("com.rafalbuchner.UfoGlyphsOutput.kerningDataTypeRadio", 0)
			self.use_production_names.set(Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.use_production_names"])
			self.decompose_smart_stuff.set(Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.decompose_smart_stuff"])
			self.kerningDataTypeRadio.set(Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.kerningDataTypeRadio"])
			self.kerningDataTypeRadio.enable(self.decompose_smart_stuff.get())
		except:
			return False

		return True

	def setFont(self, font):
		if _DEBUG_:
			print(f"> DEBUG: {self.__class__} setting font /{self.font}/")
		self.font = font
		if font is None:
			return
		self.exportUfoList.set([m.name for m in self.font.masters])
		# requires callback
		#self.exportUfoList.setSelection([1])
		self.ufoFactory.setFont(self.font)

	def selectionCallback(self, sender):
		self.plugin.selectedMasterIndexes = sender.getSelection()

	def updateSettings(self):
		if _DEBUG_:
			print(f"> DEBUG: {self.__class__} updateSettings")
		decompose_smart_stuff = True if self.decompose_smart_stuff.get() == 1 else False
		self.plugin.decompose_smart_stuff = decompose_smart_stuff
		use_production_names = True if self.use_production_names.get() == 1 else False
		self.plugin.use_production_names = use_production_names
		###print("self.exportUfoList in update", self.exportUfoList)
		### not to be done on export (new instance!) but on selection change
		###self.plugin.selectedMasterIndexes = self.exportUfoList.getSelection()

		kerningAsFeatureText = True if self.kerningDataOptions[self.kerningDataTypeRadio.get(
		)] == "export kerning as a part of feature text" else False
		self.plugin.kerningAsFeatureText = kerningAsFeatureText

	def getMasters(self):
		if _DEBUG_:
			print(f"> DEBUG: {self.__class__} getting masters")

		return [self.font.masters[index] for index in self.masterList.getSelection()]

	def export(self):
		if _DEBUG_:
			print(f"> DEBUG: {self.__class__} export font <{self.font}>")

		if not self.SavePreferences(None):
			print("Note: 'UfoGlyphsOutput.UfoMasterExporterView' could not write preferences.")

		#self.exportUfoList.enable(False)
		#self.exportUfoList.enable(True)

		if len(self.plugin.masterIndexes) == 0:
			Message("No masters selected.", "Error")
			return (False, None)
		else:
			self.updateSettings()
			#dest = vl.dialogs.getFolder()[0]
			dest = GetFolder()
			for masterIndex in self.plugin.masterIndexes:
				self.ufoFactory.exportSingleUFObyMasterIndex(
					masterIndex=masterIndex,
					dest=dest,
					kerningAsFeatureText=self.plugin.kerningAsFeatureText,
					use_production_names=self.plugin.use_production_names,
					decompose_smart_stuff=self.plugin.decompose_smart_stuff,
					add_mastername_as_stylename=True,
					is_vf=False,
					verbose=True
				)
			subprocess.Popen(["open", dest])
			return (True, None)


class UfoDesignspaceExporterView(vl.Group):
	options = [
		"designspace file only",
		"designspace package\n(together with all masters as UFO files)",
	]
	selectionTitle = "Select designspace export method:"
	infoText = "Writes all selected masters as separate .ufo files.\nAll files at the chosen location will be overwritten"
	kerningDataOptions = ["... and export kerning as a part of UFO data",
						  "export kerning as a part of feature text"]

	def __init__(self, posSize, plugin, ufoFactory):
		self.ufoFactory = ufoFactory
		self.font = None
		self.plugin = plugin

		super(UfoDesignspaceExporterView, self).__init__(posSize)
		x, y, p = (10, 10, 10)
		btnH, txtH = (22, 17)
		self.txt01 = vl.TextBox((p * 2, y, -p * 2, txtH), self.selectionTitle)
		y += txtH + p
		self.radioGroup = vl.RadioGroup(
			(p * 2, y, -p * 2, btnH * 3),
			self.options,
			callback=self.radioGroupCallback
		)
		y += btnH * 3+p * 2

		# in tooltip list all the functionalities
		self.is_vf = vl.CheckBox(
			(p * 2, y, -p * 2, btnH),
			"Prepare designspace file for variable font.", callback=self.SavePreferences
		)
		toolTipMessage = """Prepares file and variable style naming for variable fonts inside the designspace file.
Data for the preparation is being taken from the variable font settings in the "Exports" panel.
"""
		self.is_vf._nsObject.setToolTip_(toolTipMessage)
		y += btnH + p

		self.mute_not_exporting_glyphs = vl.CheckBox(
			(p * 2, y, -p * 2, btnH), "mute non-exporting glyphs in designspace file", callback=self.SavePreferences)
		toolTipMessage = """Sets glyphs with the "export" option disabled to muted inside the designspace file."""
		self.mute_not_exporting_glyphs._nsObject.setToolTip_(toolTipMessage)
		y += btnH + p
		# https://glyphsapp.com/learn/additional-masters-for-individual-glyphs-the-brace-trick
		self.delete_unnecessary_glyphs_in_special_masters = vl.CheckBox(
			(p * 2, y, -p * 2, 2 * btnH), "Delete unnecessary glyphs in special intermediate masters\n(created due to brace layers).", callback=self.SavePreferences)
		toolTipMessage = """Deletes all glyphs from the UFO master that are not affected by brace layers in the font.
UFO masters are allowed to have differing numbers of glyphs, giving more control over the interpolation.
"""
		self.delete_unnecessary_glyphs_in_special_masters._nsObject.setToolTip_(
			toolTipMessage
		)
		y += 2 * btnH + p

		self.line = vl.HorizontalLine((p * 2, y, -p * 2, 2))
		y += 2 + p
		endOfList = -(btnH + p) * 4 - txtH * 3
		y = endOfList + p
		self.use_production_names = vl.CheckBox(
			(p * 2, y, -p * 2, btnH), "Convert Glyph Names to Production Names", callback=self.SavePreferences)
		y += btnH + p
		self.decompose_smart_stuff = vl.CheckBox(
			(p * 2, y, -p * 2, btnH), "Decompose Smart Stuff ...", callback=self.SavePreferences)
		y += btnH  #+ p
		self.kerningDataTypeRadio = vl.RadioGroup(
			(p * 3, y, -p * 2, btnH * 2), self.kerningDataOptions, callback=self.SavePreferences)
		self.kerningDataTypeRadio.set(0)
		y += 2 * btnH + p
		self.txt02 = vl.TextBox((p * 2, y, -p * 2, -p), self.infoText)

		if not self.LoadPreferences():
			print("Note: 'UfoGlyphsOutput.UfoMasterExporterView' could not load preferences. Will resort to defaults")

	def updateControls(self):
		#self.kerningDataTypeRadio.enable(self.decompose_smart_stuff.get())
		if self.options[self.radioGroup.get()] == "designspace file only":
			self.delete_unnecessary_glyphs_in_special_masters.enable(False)
			self.use_production_names.enable(False)
			self.decompose_smart_stuff.enable(False)
			self.kerningDataTypeRadio.enable(False)

		if self.options[self.radioGroup.get()] == "designspace package\n(together with all masters as UFO files)":
			self.delete_unnecessary_glyphs_in_special_masters.enable(True)
			self.use_production_names.enable(True)
			self.decompose_smart_stuff.enable(True)
			self.kerningDataTypeRadio.enable(self.decompose_smart_stuff.get())

	def SavePreferences(self, sender):
		self.updateControls()
		#self.kerningDataTypeRadio.enable(self.decompose_smart_stuff.get())
		try:
			Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.UfoDesignspaceExporterView.radioGroup"] = self.radioGroup.get()
			Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.UfoDesignspaceExporterView.is_vf"] = self.is_vf.get()
			Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.UfoDesignspaceExporterView.mute_not_exporting_glyphs"] = self.mute_not_exporting_glyphs.get()
			Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.UfoDesignspaceExporterView.delete_unnecessary_glyphs_in_special_masters"] = self.delete_unnecessary_glyphs_in_special_masters.get()
			#
			Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.use_production_names"] = self.use_production_names.get()
			Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.decompose_smart_stuff"] = self.decompose_smart_stuff.get()
			Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.kerningDataTypeRadio"] = self.kerningDataTypeRadio.get()
		except:
			return False

		return True

	def LoadPreferences(self):
		try:
			Glyphs.registerDefault("com.rafalbuchner.UfoGlyphsOutput.UfoDesignspaceExporterView.radioGroup", 0)
			Glyphs.registerDefault("com.rafalbuchner.UfoGlyphsOutput.UfoDesignspaceExporterView.is_vf", 0)
			Glyphs.registerDefault("com.rafalbuchner.UfoGlyphsOutput.UfoDesignspaceExporterView.mute_not_exporting_glyphs", 0)
			Glyphs.registerDefault("com.rafalbuchner.UfoGlyphsOutput.UfoDesignspaceExporterView.delete_unnecessary_glyphs_in_special_masters", 0)
			self.radioGroup.set(Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.UfoDesignspaceExporterView.radioGroup"])
			self.is_vf.set(Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.UfoDesignspaceExporterView.is_vf"])
			self.mute_not_exporting_glyphs.set(Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.UfoDesignspaceExporterView.mute_not_exporting_glyphs"])
			self.delete_unnecessary_glyphs_in_special_masters.set(Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.UfoDesignspaceExporterView.delete_unnecessary_glyphs_in_special_masters"])
			#
			Glyphs.registerDefault("com.rafalbuchner.UfoGlyphsOutput.use_production_names", 0)
			Glyphs.registerDefault("com.rafalbuchner.UfoGlyphsOutput.decompose_smart_stuff", 0)
			Glyphs.registerDefault("com.rafalbuchner.UfoGlyphsOutput.kerningDataTypeRadio", 0)
			self.use_production_names.set(Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.use_production_names"])
			self.decompose_smart_stuff.set(Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.decompose_smart_stuff"])
			self.kerningDataTypeRadio.set(Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.kerningDataTypeRadio"])
			self.kerningDataTypeRadio.enable(self.decompose_smart_stuff.get())
		except:
			return False

		return True

	def radioGroupCallback(self, sender):
		self.SavePreferences(sender)
		self.updateControls()
		#if self.options[sender.get()] == "designspace file only":
		#	self.delete_unnecessary_glyphs_in_special_masters.enable(False)
		#	self.use_production_names.enable(False)
		#	self.decompose_smart_stuff.enable(False)
		#	self.kerningDataTypeRadio.enable(False)
        #
		#if self.options[sender.get()] == "designspace package\n(together with all masters as ufo files)":
		#	self.delete_unnecessary_glyphs_in_special_masters.enable(True)
		#	self.use_production_names.enable(True)
		#	self.decompose_smart_stuff.enable(True)
		#	self.kerningDataTypeRadio.enable(True)

	def setFont(self, font):
		if _DEBUG_:
			print(f"> DEBUG: {self.__class__} setting font /{self.font}/")
		self.font = font
		self.ufoFactory.setFont(self.font)

	def updateSettings(self):
		if _DEBUG_:
			print(f"> DEBUG: {self.__class__} updateSettings")
		decompose_smart_stuff = True if self.decompose_smart_stuff.get() == 1 else False
		self.plugin.decompose_smart_stuff = decompose_smart_stuff
		use_production_names = True if self.use_production_names.get() == 1 else False
		self.plugin.use_production_names = use_production_names
		kerningAsFeatureText = True if self.kerningDataOptions[self.kerningDataTypeRadio.get(
		)] == "export kerning as a part of feature text" else False
		self.plugin.kerningAsFeatureText = kerningAsFeatureText

	def getMasters(self):
		if _DEBUG_:
			print("> DEBUG: getting masters")
		if not self.font:
			return []
		return [self.font.masters[index] for index in self.masterList.getSelection()]

	def export(self):
		if _DEBUG_:
			print(f"> DEBUG: {self.__class__} export font {self.font}")
		self.updateSettings()
		is_vf = True if self.is_vf.get() == 1 else False
		mute_not_exporting_glyphs = True if self.mute_not_exporting_glyphs.get() == 1 else False
		delete_unnecessary_glyphs_in_special_masters = True if self.delete_unnecessary_glyphs_in_special_masters.get() == 1 else False
		#dest = vl.dialogs.getFolder()[0]
		dest = GetFolder()

		if self.options[self.radioGroup.get()] == "designspace file only":
			font_name = self.ufoFactory._getFamilyName(is_vf)
			useUSClassForMapping = True  # make UI for this
			designspace_doc = self.ufoFactory.getDesignSpaceDocument(
				useUSClassForMapping, mute_not_exporting_glyphs, is_vf)
			# export designspace, UFOs for masters, and UFOs for brace layers
			designspace_path = "%s/%s.designspace" % (dest, font_name)
			designspace_doc.write(designspace_path)

		if self.options[self.radioGroup.get()] == "designspace package\n(together with all masters as UFO files)":
			self.ufoFactory.createUfoAndDesignspacePackage(
				dest=dest,
				kerningAsFeatureText=self.plugin.kerningAsFeatureText,
				mute_not_exporting_glyphs=mute_not_exporting_glyphs,
				use_production_names=self.plugin.use_production_names,
				decompose_smart_stuff=self.plugin.decompose_smart_stuff,
				add_mastername_as_stylename=is_vf,
				delete_unnecessary_glyphs_in_special_masters=delete_unnecessary_glyphs_in_special_masters,
				is_vf=is_vf,
				verbose=False)

		subprocess.Popen(["open", dest])
		return (True, None)


class UfoInstanceExporterView(UfoMasterExporterView):
	selectionTitle = "Select instances to export as UFO:"
	infoText = "Writes all selected instances as separate .ufo files.\nAll files at the chosen location will be overwritten"

	def setFont(self, font):
		if _DEBUG_:
			print(f"> DEBUG: {self.__class__} setting font /{self.font}/")
		self.font = font
		if font is None:
			return
		exportList = []
		for i in self.font.instances:
			exportList += [i.fullName]
		self.exportUfoList.set(exportList)

	def export(self):
		if _DEBUG_:
			print(f"> DEBUG: {self.__class__} export font {self.font}")

		if not self.SavePreferences(None):
			print("Note: 'UfoGlyphsOutput.UfoInstanceExporterView' could not write preferences.")

		if len(self.plugin.masterIndexes) == 0:
			Message("No instances selected.", "Error")
			return (False, None)
		else:
			self.updateSettings()
			#dest = vl.dialogs.getFolder()[0]
			dest = GetFolder()

			instances = [
				self.font.instances[index]
				for index in self.plugin.masterIndexes
			]
			for instance in instances:
				master = instance.interpolatedFont.masters[0]
				instance_dest = os.path.join(dest, instance.fullName + ".ufo")

				self.ufoFactory.exportSingleUFObyMaster(
					master,
					instance_dest,
					kerningAsFeatureText=self.plugin.kerningAsFeatureText,
					use_production_names=self.plugin.use_production_names,
					decompose_smart_stuff=self.plugin.decompose_smart_stuff,
					add_mastername_as_stylename=False,
					verbose=True
				)

			subprocess.Popen(["open", dest])
			return (True, None)


class UfoExporterTabs(object):

	def __init__(self, posSize, plugin):
		if _DEBUG_:
			print("ufoGlyphsOutput lib")
			print(_version_)
			print("random int for attempt", __random_int__)

		self.plugin = plugin
		self.superView = getattr(self.plugin, "w", None)
		if self.superView is None:
			self.superView = self.plugin
		self.superView.mainGroup = vl.Group(posSize)
		tabsPossize = (10, 10, -10, -10)
		if _DEBUG_:
			tabsPossize = (10, 40, -10, -10)
			self.superView.mainGroup.debugBtn = vl.Button(
				(10, 10, 80, 20), "DEBUG", callback=self.debugCallback)

		self.superView.mainGroup.tabs = vl.Tabs(
			(10, 10, -10, -10), ["Designspace Export", "Master Export", "Instance Export"], callback=self.tabSwitchCallback)
		self.ufoFactory = glyphsAppUfo.UfoFactory()

		self.designspaceExportTab = self.superView.mainGroup.tabs[0]
		self.designspaceExportGroup = UfoDesignspaceExporterView(
			(0, 0, -0, -0), self.plugin, self.ufoFactory)
		self.designspaceExportTab.view = self.designspaceExportGroup

		self.masterExportTab = self.superView.mainGroup.tabs[1]
		self.masterExportGroup = UfoMasterExporterView(
			(0, 0, -0, -0), self.plugin, self.ufoFactory)
		self.masterExportTab.view = self.masterExportGroup

		self.instanceExportTab = self.superView.mainGroup.tabs[2]
		self.instanceExportGroup = UfoInstanceExporterView(
			(0, 0, -0, -0), self.plugin, self.ufoFactory)
		self.instanceExportTab.view = self.instanceExportGroup


		if not self.LoadPreferences():
			print("Note: 'UfoGlyphsOutput' could not load preferences. Will resort to defaults")

		# set initial values
		#view = self.superView.mainGroup.tabs[sender.get()].view
		#if hasattr(view, "exportUfoList"):
		#	self.plugin.selectedMasterIndexes = view.exportUfoList.getSelection()
		#else:
		#	view.updateControls() # designspace view has extra controls in place of list

	def getNSView(self):
		return self.superView.mainGroup.getNSView()

	def setFont(self, font):
		if _DEBUG_:
			print(f"> DEBUG: {self.__class__} setting font /{font}/")
		self.font = font
		self.masterExportTab.view.setFont(font)
		self.instanceExportTab.view.setFont(font)
		self.designspaceExportTab.view.setFont(font)

	def export(self):
		if not self.SavePreferences(None):
			print("Note: 'UfoGlyphsOutput' could not write preferences.")
		self.superView.mainGroup.tabs[self.superView.mainGroup.tabs.get(
		)].view.export()

	def debugCallback(self, sender):
		print(f"> DEBUG BUTTON: {self.__class__} /{self.font}/")

	#def updateControls(self):
	#	view = self.superView.mainGroup.tabs[self.superView.mainGroup.tabs.get()]
	#	if hasattr(view, "exportUfoList"):
	#		self.plugin.selectedMasterIndexes = view.exportUfoList.getSelection()
	#	else:
	#		view.updateControls() # designspace view has extra controls in place of list

	def tabSwitchCallback(self, sender):
		for exportGroup in self.masterExportGroup ,self.instanceExportGroup , self.designspaceExportGroup:
			exportGroup.LoadPreferences()

		view = self.superView.mainGroup.tabs[sender.get()].view
		if hasattr(view, "exportUfoList"):
			self.plugin.selectedMasterIndexes = view.exportUfoList.getSelection()
		else:
			view.updateControls()  # designspace view has extra controls in place of list
		#self.updateControls()
		self.SavePreferences(sender)


	def SavePreferences(self, sender):
		try:
			Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.UfoExporterTabs.tabs"] = self.superView.mainGroup.tabs.get()
		except:
			return False

		return True

	def LoadPreferences(self):
		try:
			Glyphs.registerDefault("com.rafalbuchner.UfoGlyphsOutput.UfoExporterTabs.tabs", 0)
			#self.superView.mainGroup.tabs.set(Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.UfoExporterTabs.tabs"])

			tabIndex = Glyphs.defaults["com.rafalbuchner.UfoGlyphsOutput.UfoExporterTabs.tabs"]
			self.superView.mainGroup.tabs.set(tabIndex)

			if (tabIndex == 0):
				self.superView.mainGroup.tabs[tabIndex].view.updateControls()

			#self.updateControls()
			#print("tabs is now1", self.superView.mainGroup.tabs.getNSTabView())
			#print("tabs is now2", self.superView.mainGroup.tabs[self.superView.mainGroup.tabs.get()])

		except:
			return False

		return True


def main():
	class ExporterUITest:
		def __init__(self):
			self.selectedMasterIndexes = []
			self.use_production_names = False
			self.decompose_smart_stuff = False
			self.kerningAsFeatureText = False
			self.w = vl.FloatingWindow((500, 500))
			self.w.exporterView = UfoExporterTabs((10, 10, -10, -40), self)
			self.w.exportBtn = vl.Button(
				(-110, -30, 100, 20), "Export", callback=self.exportCallback)
			self.w.open()

			self.setFont_(Glyphs.font)

		def setFont_(self, GSFontObj):
			self.w.exporterView.setFont(GSFontObj)

		def exportCallback(self, sender):
			try:
				self.w.exporterView.export()
				self.w.close()

			except:
				import traceback
				print(traceback.format_exc())
				# return (False, NSError)

	ExporterUITest()


if __name__ == '__main__':
	main()
