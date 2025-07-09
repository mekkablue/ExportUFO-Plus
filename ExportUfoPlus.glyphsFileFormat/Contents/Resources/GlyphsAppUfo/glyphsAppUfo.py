
from GlyphsApp import Glyphs, GSInstance
import re
import os
import tempfile
import shutil
# from fontParts.world import OpenFont as OpenUfo
from Foundation import NSClassFromString, NSURL
from fontTools.designspaceLib import (
	DesignSpaceDocument, AxisDescriptor, SourceDescriptor, InstanceDescriptor, RuleDescriptor)

from contextlib import contextmanager
from collections import OrderedDict
import plistlib


DEBUG = False
DEBUG_NO = 0
if DEBUG:
	from random import randint
	DEBUG_NO = randint(0, 100)
	print(f">> GlyphsAppUfo – DEBUG mode enabled {DEBUG_NO}")


def _print(txt, verbose):
	if verbose:
		print(txt)


def hardcodedFixes_deleteLater(ufoPath):
	# fix for >>>wrong data types in exported UFO/fontinfo.plist for openTypeOS2CodePageRanges key #1375<<< issue
	fontInfoPath = os.path.join(ufoPath, "fontinfo.plist")

	fontInfo = {}
	with open(fontInfoPath, 'rb') as fontInfoFile:
		fontInfo = plistlib.load(fontInfoFile)
		if 'openTypeOS2CodePageRanges' not in fontInfo.keys():
			fontInfo['openTypeOS2CodePageRanges'] = []
		fontInfo['openTypeOS2CodePageRanges'] = [
			int(string) for string in fontInfo['openTypeOS2CodePageRanges']]

	with open(fontInfoPath, 'wb') as fontInfoFileWrite:
		plistlib.dump(fontInfo, fontInfoFileWrite)


#def getRidOfKernInFEA(RFont):
#	feaText = RFont.features.text
#	allowLineInFeaText = True
#	feaWithoutKerning = []
#
#	for index, feaLine in enumerate(feaText.split("\n")):
#		_feaLine = feaLine.strip()
#		_feaLine = re.sub("\s\s+", " ", _feaLine)
#		_feaLine = _feaLine.replace(" ;", ";")
#
#		if _feaLine.startswith("@MMK_L_"):
#			continue
#		if _feaLine.startswith("@MMK_R_"):
#			continue
#
#		if "feature kern {" == _feaLine:
#			allowLineInFeaText = False
#
#		if allowLineInFeaText:
#			feaWithoutKerning.append(feaLine)
#
#		if "} kern;" == _feaLine:
#			allowLineInFeaText = True
#
#	RFont.features.text = "\n".join(feaWithoutKerning)

def getRidOfKernInFEA(dest):
	f = open(dest + "/features.fea")
	#feaText = RFont.features.text
	feaText = f.read()
	f.close()
	allowLineInFeaText = True
	feaWithoutKerning = []

	for index, feaLine in enumerate(feaText.split("\n")):
		_feaLine = feaLine.strip()
		_feaLine = re.sub(r"\s\s+", " ", _feaLine)
		_feaLine = _feaLine.replace(" ;", ";")

		if _feaLine.startswith("@MMK_L_"):
			continue
		if _feaLine.startswith("@MMK_R_"):
			continue

		if "feature kern {" == _feaLine:
			allowLineInFeaText = False

		if allowLineInFeaText:
			feaWithoutKerning.append(feaLine)

		if "} kern;" == _feaLine:
			allowLineInFeaText = True

	#RFont.features.text = "\n".join(feaWithoutKerning)
	f = open(dest + "/features.fea", "w")
	f.write("\n".join(feaWithoutKerning))
	f.close()


#def getRidOfKernAsData(RFont):
#	RFont.kerning.clear()
#	RFont.groups.clear()


def getRidOfKernAsData(dest):
	os.remove(dest + "/kerning.plist")
	os.remove(dest + "/groups.plist")
	#RFont.kerning.clear()
	#RFont.groups.clear()


class UfoFactory(object):
	def __init__(self, fontPath=None):
		self.fontPath = fontPath

	@contextmanager
	def openFile(self, fontFile=None):
		# with statement
		try:
			self.read(fontFile)
			yield self
		finally:
			self.close()

	def close(self):
		# when the font's window is invisible, then close font after the operation
		if self.font.parent.windowController() is None:
			self.font.close()

	def read(self, fontPath=None):
		if fontPath is None:
			fontPath = self.fontPath

		self.loadFontFromPath(fontPath)

	def setFont(self, font):
		self.font = font
		self.fontPath = font.filepath if font else ""

	def loadFontFromPath(self, fontPath):
		font = Glyphs.open(fontPath, showInterface=False)
		self.setFont(font)

	def _getMutedGlyphs(self):
		__doc__ = "Returns an array of non-exporting glyphs to be added as muted glyphs in the designspace"
		return [glyph.name for glyph in self.font.glyphs if not glyph.export]

	def _getBoundsByTag(self, tag):
		__doc__ = """Provided an axis tag, returns an array in the form of [minimum, maximum] representing the bounds of an axis.

Example use:
min, max = getBoundsByTag(Glyphs.font,"wght")"""
		min = None
		max = None
		for i, axis in enumerate(self.font.axes):
			if axis.axisTag != tag:
				continue
			for master in self.font.masters:
				coord = master.axes[i]
				if min is None or coord < min:
					min = coord
				if max is None or coord > max:
					max = coord
		return [min, max]

	def _getAxisNameByTag(self, tag):
		__doc__ = """Returns an axis name"""
		for axis in self.font.axes:
			if axis.axisTag == tag:
				return axis.name

	def _getVariableFontFamily(self):
		__doc__ = """Returns the name associated with a Variable Font Setting export"""

		for instance in self.font.instances:
			if instance.type == 1:  # found VariableFontSettings
				return instance.name
		return "VF"

	def _getFamilyName(self, is_vf=False):
		__doc__ = """Provided a font object, returns a font family name"""
		if is_vf:
			family_name = "%s %s" % (
				self.font.familyName, self._getVariableFontFamily())
		else:
			family_name = self.font.familyName
		return family_name

	def _getFamilyNameWithMaster(self, master, is_vf=False):
		__doc__ = """Returns a font family name"""
		master_name = master.name
		if is_vf:
			font_name = "%s %s - %s" % (
				self.font.familyName,
				self._getVariableFontFamily(), master_name
			)
		else:
			font_name = "%s - %s" % (self.font.familyName, master_name)
		return font_name

	def _getStyleNameWithAxis(self, axes):
		__doc__ = """Returns a style name formatted together with axis values. Used to generate inbetween masters"""
		style_name = ""
		for i, axis in enumerate(axes):
			style_name = "%s %s %s" % (
				style_name, self.font.axes[i].name, axis)
		return style_name.strip()

	# change name to _getFamilyNameWithAxes
	def _getNameWithAxis(self, axes, is_vf=False):
		__doc__ = """Provided a dict of axes for a brace layer, returns a font family name"""
		if is_vf:
			font_name = "%s %s -" % (
				self.font.familyName,
				self._getVariableFontFamily()
			)
		else:
			font_name = self.font.familyName
		for i, axis in enumerate(axes):
			font_name = "%s %s %s" % (font_name, self.font.axes[i].name, axis)
		return font_name

	def _alignSpecialLayers(self):
		__doc__ = """Applies the same master ID referencing the variable font origin to all brace layers"""
		master_id = self.getOriginMaster()
		special_layers = self._getSpecialLayers()
		for layer in special_layers:
			layer.associatedMasterId = master_id

	def getSources(self, mute_not_exporting_glyphs, is_vf=False):
		__doc__ = """Creates and returns a list of designspaceLib SourceDescriptors"""
		sources = []
		for i, master in enumerate(self.font.masters):
			s = SourceDescriptor()
			font_name = self._getFamilyNameWithMaster(master, is_vf)
			s.name = master.name
			s.filename = "%s.ufo" % font_name
			s.familyName = self._getFamilyName(is_vf)
			s.styleName = master.name
			locations = dict()
			for x, axis in enumerate(master.axes):
				locations[self.font.axes[x].name] = axis
			s.location = locations
			origin_master_id = self.getOriginMaster()
			if master.id == origin_master_id:
				s.copyLib = True
				s.copyFeatures = True
				s.copyGroups = True
				s.copyInfo = True
			if mute_not_exporting_glyphs:
				s.mutedGlyphNames = self._getMutedGlyphs()
			sources.append(s)
		return sources

	def _getSpecialLayers(self):
		__doc__ = """Returns a list of GSLayers that are brace layers (have intermediate master coordinates)."""

		return [l for g in self.font.glyphs for l in g.layers if l.isSpecialLayer and l.attributes['coordinates']]

	def _getSpecialLayerAxes(self):
		__doc__ = """Returns a list of dicts containing name and coordinate information for each axis"""
		special_layer_axes = []
		layers = self._getSpecialLayers()
		for layer in layers:
			layer_axes = dict()
			for i, coords in enumerate(layer.attributes['coordinates']):
				layer_axes[self.font.axes[i].name] = layer.attributes['coordinates'][coords]
			if layer_axes not in special_layer_axes:
				special_layer_axes.append(layer_axes)
		return special_layer_axes

	def _getNonSpecialGlyphs(self, axes):
		__doc__ = """Provided a a list of axis coordinates, returns all glyphs without those coordinates"""
		glyph_names_to_delete = []
		for glyph in self.font.glyphs:
			delete_glyph = True
			for layer in glyph.layers:
				if layer.isSpecialLayer and layer.attributes['coordinates']:
					coords = list(layer.attributes['coordinates'].values())
					if coords == axes:
						delete_glyph = False
			if delete_glyph:
				if glyph.name not in glyph_names_to_delete:
					glyph_names_to_delete.append(glyph.name)
		return glyph_names_to_delete

	def _getSpecialSources(self):
		__doc__ = """Returns an array of designspaceLib SourceDescriptors """

		sources = []
		special_layer_axes = self._getSpecialLayerAxes()
		for i, special_layer_axis in enumerate(special_layer_axes):
			axes = list(special_layer_axis.values())
			s = SourceDescriptor()
			s.location = special_layer_axis
			font_name = self._getNameWithAxis(axes)
			s.filename = "%s.ufo" % font_name
			s.name = font_name
			sources.append(s)
		return sources

	def addSources(self, doc, sources):  # ? make ds doc attr ?
		__doc__ = """Provided a designspace document and array of source descriptors, adds those sources to the designspace doc."""
		for source in sources:
			doc.addSource(source)

	def getOriginMaster(self):
		__doc__ = """Returns a string of the master ID referencing the master that is set to the variable font origin by custom paramter"""
		master_id = None
		for parameter in self.font.customParameters:
			if parameter.name == "Variable Font Origin":
				master_id = parameter.value
		if master_id is None:
			return self.font.masters[0].id
		return master_id

	def getOriginCoords(self):
		__doc__ = """Provided a font object, returns an array of axis coordinates specified on the variable font origin master."""
		master_id = None
		for parameter in self.font.customParameters:
			if parameter.name == "Variable Font Origin":
				master_id = parameter.value
		if master_id is None:
			master_id = self.font.masters[0].id
		for master in self.font.masters:
			if master.id == master_id:
				return list(master.axes)

	def __getAxisMappingBasedOnUSClasses(self, axisIndex, axis):
		if axis.axisTag.lower() not in ["wght", "wdth"]:
			return
		isWeight = axis.axisTag.lower() == "wght"

		class_axis_map = OrderedDict()
		for instance in self.font.instances:
			usrValue = instance.axes[axisIndex]

			mappedValue = instance.widthClass
			if isWeight:
				mappedValue = instance.weightClass

			class_axis_map[usrValue] = mappedValue
		return class_axis_map

	def _addAxes(self, doc, useUSClassForMapping):
		__doc__ = """Provided a designspace doc, adds axes from the glyphsapp font to the designspace as AxisDescriptors"""

		for i, axis in enumerate(self.font.axes):
			new_axis = AxisDescriptor()
			axis_min, axis_max = self._getBoundsByTag(axis.axisTag)

			# support for "Axis Mappings" custom parameter
			axis_map = None
			if "Axis Mappings" in self.font.customParameters:
				# checking if "Axis Mappings" parameter is activated:
				if self.font.customParameters["Axis Mappings"] is not None:
					if axis.axisTag in self.font.customParameters["Axis Mappings"].keys():
						glyphsAxisMap = self.font.customParameters["Axis Mappings"][axis.axisTag]
						axis_map = {v: k for k, v in glyphsAxisMap.items()}

			# do it as optional!!!!
			if axis_map is None and useUSClassForMapping:  # maybe there is a better name for it?
				axis_map = self.__getAxisMappingBasedOnUSClasses(i, axis)

			if axis_map is not None:
				for k in sorted(axis_map.keys()):
					new_axis.map.append((axis_map[k], k))
				new_axis.maximum = axis_map[axis_max]
				new_axis.minimum = axis_map[axis_min]
				origin_coord = self.getOriginCoords()[i]
				user_origin = axis_map[origin_coord]
			else:
				# if there is no "Axis Mappings" custom parameter defined
				new_axis.maximum = axis_max
				new_axis.minimum = axis_min
				user_origin = self.getOriginCoords()[i]

			new_axis.default = user_origin
			new_axis.name = axis.name
			new_axis.tag = axis.axisTag
			doc.addAxis(new_axis)

	def removeSubsFromOT(self):
		__doc__ = """Removes subsitutions in feature code"""
		feature_index = None
		for i, feature_itr in enumerate(self.font.features):
			for line in feature_itr.code.splitlines():
				if line.startswith("condition "):
					feature_index = i
					break
		if feature_index:
			self.font.features[feature_index].code = re.sub(
				r'#ifdef VARIABLE.*?#endif', '', self.font.features[feature_index].code, flags=re.DOTALL)

	def getConditionsFromOT(self):
		__doc__ = """Returns two arrays: one a list of OT substitution conditions, and one of the glyph replacements to make given those conditions. Each array has the same index.

Example use:
condition_list, replacement_list = getConditionsFromOT(font)
"""
		feature_code = ""
		for feature_itr in self.font.features:
			for line in feature_itr.code.splitlines():
				if line.startswith("condition "):
					feature_code = feature_itr.code
		condition_index = 0
		condition_list = []
		replacement_list = [[]]
		for line in feature_code.splitlines():
			if line.startswith("condition"):
				conditions = []
				conditions_list = line.split(",")
				for condition in conditions_list:
					m = re.findall(r"< (\w{4})", condition)
					tag = m[0]
					axis_name = self._getAxisNameByTag(tag)
					m = re.findall(r"\d+(?:\.|)\d*", condition)
					cond_min = float(m[0])
					if len(m) > 1:
						cond_max = float(m[1])
						range_dict = dict(
							name=axis_name, minimum=cond_min, maximum=cond_max)
					else:
						_, cond_max = self._getBoundsByTag(tag)
						range_dict = dict(
							name=axis_name, minimum=cond_min, maximum=cond_max)
					conditions.append(range_dict)
				condition_list.append(conditions)
				condition_index = condition_index + 1
			elif line.startswith("sub"):
				m = re.findall("sub (.*) by (.*);", line)[0]
				replace = (m[0], m[1])
				try:
					replacement_list[condition_index - 1].append(replace)
				except:
					replacement_list.append(list())
					replacement_list[condition_index - 1].append(replace)
		return [condition_list, replacement_list]

	def applyConditionsToRules(self, doc, condition_list, replacement_list):
		__doc__ = """Provided a designspace document, condition list, and replacement list (as provided by getConditionsFromOT), adds matching designspace RuleDescriptors to the doc"""
		rules = []
		for i, condition in enumerate(condition_list):
			r = RuleDescriptor()
			r.name = "Rule %s" % str(i + 1)
			r.conditionSets.append(condition)
			for sub in replacement_list[i]:
				r.subs.append(sub)
			rules.append(r)
		doc.rules = rules

	def getInstances(self, is_vf=False):
		__doc__ = """Returns a list of designspaceLib InstanceDescriptors"""
		instances_to_return = []
		for instance in self.font.instances:
			if not instance.active:
				continue
			if instance.familyName is not None:  # skip Variable Font Setting, which is an instance
				continue

			ins = InstanceDescriptor()
			postScriptName = instance.fontName
			if instance.isBold:
				style_map_style = "bold"
			elif instance.isItalic:
				style_map_style = "italic"
			else:
				style_map_style = "regular"
			if is_vf:
				family_name = "%s %s" % (
					self.font.familyName, self._getVariableFontFamily())
			else:
				family_name = instance.preferredFamily
			ins.familyName = family_name
			if is_vf:
				style_name = instance.variableStyleName
			else:
				style_name = instance.name
			ins.styleName = style_name
			ins.filename = "%s.ufo" % postScriptName
			ins.postScriptFontName = postScriptName
			ins.styleMapFamilyName = "%s %s" % (
				instance.preferredFamily, instance.name)
			ins.styleMapStyleName = style_map_style
			axis_name = {}
			for i, axis_value in enumerate(instance.axes):
				axis_name[self.font.axes[i].name] = axis_value
			ins.location = axis_name
			instances_to_return.append(ins)
		return instances_to_return

	def addInstances(self, doc, instances):
		__doc__ = """Provided a doc and list of designspace InstanceDescriptors, adds them to the doc"""
		for instance in instances:
			doc.addInstance(instance)

	def updateFeatures(self):
		__doc__ = """Updates its automatically generated OpenType features"""
		for feature in self.font.features:
			if feature.automatic:
				feature.update()

	def getDesignSpaceDocument(self, useUSClassForMapping, mute_not_exporting_glyphs, is_vf):
		__doc__ = """Returns a designspaceLib DesignSpaceDocument populated with data from the provided font object"""
		doc = DesignSpaceDocument()
		self._addAxes(doc, useUSClassForMapping)

		sources = self.getSources(mute_not_exporting_glyphs, is_vf)
		self.addSources(doc, sources)
		special_sources = self._getSpecialSources()
		self.addSources(doc, special_sources)
		instances = self.getInstances(is_vf)
		self.addInstances(doc, instances)
		condition_list, replacement_list = self.getConditionsFromOT()
		self.applyConditionsToRules(doc, condition_list, replacement_list)
		return doc

	def generateMastersAtBraces(self, temp_ufo_folder, kerningAsFeatureText, delete_unnecessary_glyphs_in_special_masters, use_production_names, decompose_smart_stuff, verbose=False):
		__doc__ = """Provided a font object and export destination, exports all brace layers as individual UFO masters"""
		special_layer_axes = self._getSpecialLayerAxes()
		for i, special_layer_axis in enumerate(special_layer_axes):
			axes = list(special_layer_axis.values())
			self.font.instances.append(GSInstance())
			ins = self.font.instances[-1]
			ins.name = self._getNameWithAxis(axes)
			ufo_file_name = "%s.ufo" % ins.name
			style_name = self._getStyleNameWithAxis(axes)
			ins.styleName = style_name
			ins.axes = axes
			brace_font = ins.interpolatedFont
			brace_font.masters[0].name = style_name
			if delete_unnecessary_glyphs_in_special_masters:
				glyph_names_to_delete = self._getNonSpecialGlyphs(axes)

				for glyph in glyph_names_to_delete:
					del brace_font.glyphs[glyph]
				feature_keys = [
					feature.name for feature in brace_font.features]

				for key in feature_keys:
					del brace_font.features[key]
				class_keys = [
					font_class.name for font_class in brace_font.classes]

				for key in class_keys:
					del brace_font.classes[key]

				for glyph in brace_font.glyphs:
					if glyph.rightKerningGroup:
						glyph.rightKerningGroup = None
					if glyph.leftKerningGroup:
						glyph.leftKerningGroup = None
					if glyph.topKerningGroup:
						glyph.topKerningGroup = None
					if glyph.bottomKerningGroup:
						glyph.bottomKerningGroup = None
				brace_font.kerning = {}
				brace_font.kerningRTL = {}
				brace_font.kerningVertical = {}

			ufo_file_path = os.path.join(temp_ufo_folder, ufo_file_name)
			self.exportSingleUFObyMaster(
				brace_font.masters[0], ufo_file_path, kerningAsFeatureText, use_production_names=use_production_names,
				decompose_smart_stuff=decompose_smart_stuff, add_mastername_as_stylename=False, verbose=False
			)

	def _fixStyleName(self, name, path):
		__doc__ = """Provided a master name and its path, swaps the styleName attribute in fontinfo.plist for the master name. This is required by some plugins like ScaleFast."""
		new_path = os.path.join(path, "fontinfo.plist")
		f = open(new_path, 'r', encoding="utf-8")
		file_data = f.read()
		f.close()
		new_data = re.sub(r'(<key>styleName</key>\n*\r*\s+<string>)(.*)?</string>', rf'\1{name}</string>', file_data)
		f = open(new_path, 'w', encoding="utf-8")
		f.write(new_data)
		f.close()

	def _getRidOfKernAsData(self, name, path):
		pass

	def _getRidOfKernInFEA(self, name, path):
		pass

	def exportSingleUFObyMaster(self, master, dest, kerningAsFeatureText, use_production_names, decompose_smart_stuff, add_mastername_as_stylename, verbose=False):
		__doc__ = """Provided a master and destination path, exports a UFO"""

		exporter = NSClassFromString('GlyphsFileFormatUFO').alloc().init()
		exporter.setFontMaster_(master)
		exporter.setConvertNames_(use_production_names)
		exporter.setDecomposeSmartStuff_(decompose_smart_stuff)
		_print("Exporting master: %s - %s" % (master.font.familyName, master.name), verbose)

		exporter.writeUfo_toURL_error_(
			master, NSURL.fileURLWithPath_(dest), None)

		hardcodedFixes_deleteLater(dest)

		if kerningAsFeatureText:
			getRidOfKernAsData(dest)
		if not kerningAsFeatureText:
			getRidOfKernInFEA(dest)

		if add_mastername_as_stylename:
			self._fixStyleName(master.name, dest)

		# old fontparts code
		#ufoFont = OpenUfo(dest, showInterface=False)
		#print("ufoFont", ufoFont)
		#if kerningAsFeatureText:
		#	getRidOfKernAsData(ufoFont)
		#if not kerningAsFeatureText:
		#	getRidOfKernInFEA(ufoFont)
		#
		#ufoFont.save()
		#if add_mastername_as_stylename:
		#	self._fixStyleName(master.name, dest)

	def exportSingleUFObyMasterIndex(self, masterIndex, dest, kerningAsFeatureText, use_production_names, decompose_smart_stuff, add_mastername_as_stylename, is_vf=False, verbose=False):
		__doc__ = """Provided a master list index and destination path, exports a UFO"""

		master = self.font.masters[masterIndex]
		font_name = self._getFamilyNameWithMaster(master, is_vf)
		file_name = "%s.glyphs" % font_name
		ufo_file_name = file_name.replace('.glyphs', '.ufo')
		ufo_file_path = os.path.join(dest, ufo_file_name)
		self.exportSingleUFObyMaster(
			master, ufo_file_path, kerningAsFeatureText,
			use_production_names, decompose_smart_stuff, add_mastername_as_stylename, verbose
		)

	def exportUFOMasters(self, dest, kerningAsFeatureText, use_production_names, decompose_smart_stuff, add_mastername_as_stylename, is_vf=False, verbose=False):
		__doc__ = """Provided a destination, exports a UFO for each master in the UFO, not including special layers (for that use generateMastersAtBraces)"""
		for master in self.font.masters:
			font_name = self._getFamilyNameWithMaster(master, is_vf)
			file_name = "%s.glyphs" % font_name
			ufo_file_name = file_name.replace('.glyphs', '.ufo')
			ufo_file_path = os.path.join(dest, ufo_file_name)
			self.exportSingleUFObyMaster(
				master, ufo_file_path, kerningAsFeatureText,
				use_production_names, decompose_smart_stuff, add_mastername_as_stylename, verbose
			)

	def createUfoAndDesignspacePackage(self, dest, kerningAsFeatureText, mute_not_exporting_glyphs, use_production_names, decompose_smart_stuff, add_mastername_as_stylename, delete_unnecessary_glyphs_in_special_masters, useUSClassForMapping=True, is_vf=False, verbose=False):
		__doc__ = """Provided a font object, and destination directory path creates ufos and designspace file inside the this directory"""

		# use a copy to prevent modifying the open Glyphs file
		font = self.font.copy()
		# put all special layers on the same masterID
		self._alignSpecialLayers()
		# update any automatically generated features that need it
		self.updateFeatures()

		# as a destination path (and empty it first if it exists)
		font_name = self._getFamilyName(is_vf)

		final_file_paths = []

		# when creating files below, export them to tmp_dir before we copy it over.
		# tempfile will automatically delete the temp files we generated
		with tempfile.TemporaryDirectory() as tmp_dir:
			temp_ufo_folder = os.path.join(tmp_dir, "ufo")
			os.mkdir(temp_ufo_folder)
			# generate a designspace file based on metadata in the copy of the open font
			_print("Building designspace from font metadata...", verbose)
			designspace_doc = self.getDesignSpaceDocument(
				useUSClassForMapping, mute_not_exporting_glyphs, is_vf)

			# remove the OpenType substituties as they are now in the designspace as conditionsets
			self.removeSubsFromOT()
			# export designspace, UFOs for masters, and UFOs for brace layers
			designspace_path = "%s/%s.designspace" % (
				temp_ufo_folder, font_name)
			designspace_doc.write(designspace_path)
			_print("Building UFOs for masters...", verbose)
			self.exportUFOMasters(
				dest=temp_ufo_folder,
				kerningAsFeatureText=kerningAsFeatureText,
				use_production_names=use_production_names,
				decompose_smart_stuff=decompose_smart_stuff,
				add_mastername_as_stylename=add_mastername_as_stylename,
				is_vf=is_vf,
				verbose=verbose
			)
			_print("Building UFOs for brace layers if present...", verbose)
			self.generateMastersAtBraces(
				temp_ufo_folder=temp_ufo_folder,
				kerningAsFeatureText=kerningAsFeatureText,
				delete_unnecessary_glyphs_in_special_masters=delete_unnecessary_glyphs_in_special_masters,
				use_production_names=use_production_names,
				decompose_smart_stuff=decompose_smart_stuff,
				verbose=verbose
			)
			# copy from temp dir to the destination. after this, tempfile will automatically delete the temp files
			for file in os.listdir(temp_ufo_folder):
				srcFilePath = os.path.join(temp_ufo_folder, file)
				dstFilePath = os.path.join(dest, file)
				if os.path.exists(dstFilePath):
					if os.path.isdir(dstFilePath):
						shutil.rmtree(dstFilePath)
					else:
						os.remove(dstFilePath)
				if os.path.isdir(srcFilePath):
					shutil.copytree(srcFilePath, dstFilePath)
				else:
					shutil.copy(srcFilePath, dstFilePath)
				final_file_paths.append(dstFilePath)

		# open the output dir
		_print("Done!", verbose)
		return final_file_paths
