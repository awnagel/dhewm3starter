#
# +---------------------------------------------------------+
# | Copyright (c) 2002 Anthony D'Agostino					|
# | http://www.redrival.com/scorpius						|
# | scorpius@netzero.com									|
# | April 21, 2002											|
# | Read and write LightWave Object File Format (*.lwo)		|
# +---------------------------------------------------------+

# ***** BEGIN GPL LICENSE BLOCK *****
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place - Suite 330, Boston, MA	 02111-1307, USA.
#
# ***** END GPL LICENCE BLOCK *****


"""\
This script exports self.meshes to LightWave file format.

LightWave is a full-featured commercial modeling and rendering
application. The lwo file format is composed of 'chunks,' is well
defined, and easy to read and write. It is similar in structure to the
trueSpace cob format.

Usage:<br>
	Select self.meshes to be exported and run this script from "File->Export" menu.

Supported:<br>
	UV Coordinates, Meshes, Materials, Material Indices, Specular
Highlights, and Vertex Colors. For added functionality, each object is
placed on its own layer. Someone added the CLIP chunk and imagename support.

Missing:<br>
	Not too much, I hope! :).

Known issues:<br>
	Empty objects crash has been fixed.

Notes:<br>
	For compatibility reasons, it also reads lwo files in the old LW
v5.5 format.
"""


bl_info = {
	"name": "Export LightWave(.lwo)",
	"author": "Anthony D'Agostino (Scorpius) and Gert De Roost",
	"version": (2, 3, 2),
	"blender": (2, 69, 0),
	"location": "File > Export",
	"description": "Lightwave .lwo export",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"category": "Import-Export"}


import bpy, bmesh
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, FloatProperty, EnumProperty
from bpy.app.handlers import persistent
import os, math, functools
try: import struct
except: struct = None
try: import io
except: io = None
try: import operator
except: operator = None




bpy.types.Material.vcmenu = EnumProperty(
			items = [("<none>", "<none>", "<none>")],
			name = "Vertex Color Map",
			description = "LWO export: vertex color map for this material",
			default = "<none>")
			


class idTechVertexColors(bpy.types.Panel):
	bl_label = "LwoExport Vertex Color Map"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "material"

	@classmethod
	def poll(self, context):
		return context.active_object.active_material!=None

	def draw(self, context):
		layout = self.layout
		layout.prop(context.active_object.active_material, 'vcmenu')


class MessageOperator(bpy.types.Operator):
	bl_idname = "lwoexport.message"
	bl_label = "Saved"

	def invoke(self, context, event):
	
		wm = context.window_manager
		return wm.invoke_popup(self, width=500, height=20)

	def draw(self, context):

		layout = self.layout
		row = layout.row()
		row.label(text = '', icon = "ERROR")
		row.label("Error | This exporter requires a full python installation")


class LwoExport(bpy.types.Operator, ExportHelper):
	bl_idname = "export.lwo"
	bl_label = "LwoExport"
	bl_description = "Export Lightwave .lwo file"
	bl_options = {"REGISTER"}
	filename_ext = ".lwo"
	filter_glob = StringProperty(default = "*.lwo", options = {'HIDDEN'})

	filepath = StringProperty( 
		name = "File Path",
		description = "File path used for exporting the .lwo file",
		maxlen = 1024,
		default = "" )

	option_idtech = BoolProperty( 
			name = "idTech compatible",
			description = "Saves .lwo compatible with idTech engines",
			default = True )

	option_smooth = BoolProperty( 
			name = "Smoothed",
			description = "Save entire mesh as smoothed",
			default = False )

	option_subd = BoolProperty( 
			name = "Export as subpatched",
			description = "Export mesh data as subpatched",
			default = False )

	option_applymod = BoolProperty( 
			name = "Apply modifiers",
			description = "Applies modifiers before exporting",
			default = True )

	option_triangulate = BoolProperty( 
			name = "Triangulate",
			description = "Triangulates all exportable objects",
			default = True )

	option_normals = BoolProperty( 
			name = "Recalculate Normals",
			description = "Recalculate normals before exporting",
			default = False )

	option_remove_doubles = BoolProperty( 
			name = "Remove Doubles",
			description = "Remove any duplicate vertices before exporting",
			default = False )

	option_apply_scale = BoolProperty( 
			name = "Scale",
			description = "Apply scale transformation",
			default = True )

	option_apply_location = BoolProperty( 
			name = "Location",
			description = "Apply location transformation",
			default = True )

	option_apply_rotation = BoolProperty( 
			name = "Rotation",
			description = "Apply rotation transformation",
			default = True )

	option_batch = BoolProperty( 
			name = "Batch Export",
			description = "A separate .lwo file for every selected object",
			default = False )

	option_normaddon = BoolProperty( 
			name = "Use \"Recalc Vert Normals\" addon data",
			description = "Export the vertex normals created with the \"Recalc Vert Normals\" addon",
			default = False )

	option_scale = FloatProperty( 
			name = "Scale",
			description = "Object scaling factor (default: 1.0)",
			min = 0.01,
			max = 1000.0,
			soft_min = 0.01,
			soft_max = 1000.0,
			default = 1.0 )
	
	def draw( self, context ):
		layout = self.layout

		box = layout.box()
		box.label( 'Essentials:' )
		box.prop( self, 'option_idtech' )
		box.prop( self, 'option_applymod' )
		box.prop( self, 'option_subd' )
		box.prop( self, 'option_triangulate' )
		box.prop( self, 'option_normals' )
		box.prop( self, 'option_remove_doubles' )
		box.prop( self, 'option_smooth' )
		box.label( "Transformations:" )
		box.prop( self, 'option_apply_scale' )
		box.prop( self, 'option_apply_rotation' )
		box.prop( self, 'option_apply_location' )
		box.label( "Advanced:" )
		box.prop( self, 'option_scale' )
		box.prop( self, 'option_batch')
		if 'vertex_normal_list' in context.active_object:
			box.prop( self, 'option_normaddon')
		
	@classmethod
	def poll(cls, context):
		obj = context.active_object
		return (obj and obj.type == 'MESH')

	def execute(self, context):
	
		global main
		
		main = self
	
		self.context = context
		self.VCOL_NAME = "Per-Face Vertex Colors"
		self.DEFAULT_NAME = "Blender Default"
		
		if struct and io and operator:
			self.write(self.filepath)
		else:
			bpy.ops.lwoexport.message('INVOKE_DEFAULT')
		

		return {'FINISHED'}

	# ==============================
	# === Write LightWave Format ===
	# ==============================
	def write(self, filename):
		objects = list(self.context.selected_objects)
		actobj = self.context.active_object
		
		try:	objects.sort( key = lambda a: a.name )
		except: objects.sort(lambda a,b: cmp(a.name, b.name))
	
		self.meshes = []
		object_name_lookup_orig = {}
		mesh_object_name_lookup = {} # for name lookups only
		objdups = []
		
		for obj in objects:
			if obj.type != 'MESH':
				continue
				
			bpy.ops.object.select_all(action='DESELECT')
			bpy.context.scene.objects.active = obj
			obj.select = True
			bpy.ops.object.duplicate()
			objdup = bpy.context.active_object
			objdups.append(objdup)
			object_name_lookup_orig[objdup] = obj.name
			
			if self.option_applymod:
				if not(objdup.data.shape_keys):
					while (len(objdup.modifiers)):
						bpy.ops.object.modifier_apply(apply_as='DATA', modifier = objdup.modifiers[0].name)

			# Options
			bpy.ops.object.mode_set( mode = 'EDIT' )
			if self.option_remove_doubles:
				bpy.ops.object.mode_set( mode = 'EDIT' )
				bpy.ops.mesh.select_all( action = 'SELECT' )
				bpy.ops.mesh.remove_doubles()
			if self.option_triangulate:
				bpy.ops.mesh.select_all( action = 'SELECT' )
				bpy.ops.mesh.quads_convert_to_tris()
			if self.option_normals:
				bpy.ops.object.mode_set( mode = 'EDIT' )
				bpy.ops.mesh.select_all( action = 'SELECT' )
				bpy.ops.mesh.normals_make_consistent()

			# Transformations
			bpy.ops.object.mode_set( mode = 'OBJECT' )
			bpy.ops.object.transform_apply( location = self.option_apply_location, rotation = self.option_apply_rotation, scale = self.option_apply_scale )

			mesh = objdup.data
			if mesh:
				mesh_object_name_lookup[mesh] = obj.name
				if not(self.option_batch):
					self.meshes.append(mesh)
					
					
		for obj in objdups:
			if (self.option_batch):
				self.meshes = [obj.data]

			if (self.option_batch):
				filename = os.path.dirname(filename)
				filename += (os.sep + object_name_lookup_orig[obj].replace('.', '_'))
			if not filename.lower().endswith('.lwo'):
				filename += '.lwo'
			file = open(filename, "wb")
		
			matmeshes, material_names = self.get_used_material_names()
			self.clips = []
			self.clippaths = []
			self.currclipid = 1
			tags = self.generate_tags(material_names)
			surfs = []
			chunks = [tags]
		
			meshdata = io.BytesIO()
			
			layer_index = 0
			
			for i, mesh in enumerate(self.meshes):
				if not(self.option_batch):
					mobj = objdups[i]
					
				if mesh.vertex_colors:
					#if meshtools.average_vcols:
					#	vmap_vc = generate_rgba_vc(mesh)  # per vert
					#else:
					if self.option_idtech:
						rgba_vcs = self.generate_rgba_vc(mesh)  # per vert
					else:
						rgb_vcs = self.generate_rgb_vc(mesh)  # per face
				
				for j, m in enumerate(matmeshes):
					if m == mesh:
						surfs.append(self.generate_surface(m, material_names[j]))
				layr = self.generate_layr(mesh_object_name_lookup[mesh], layer_index)
				pnts = self.generate_pnts(mesh)
				bbox = self.generate_bbox(mesh)
				if not(self.option_idtech):
					if not(self.option_normaddon and 'vertex_normal_list' in mobj):
						vnorms = self.generate_vnorms(mesh, None)
					else:
						vnorms = self.generate_vnorms(mesh, mobj.vertex_normal_list)
				pols = self.generate_pols(mesh, self.option_subd)
				if not(self.option_idtech):
					if not(self.option_normaddon and 'vertex_normal_list' in mobj):
						lnorms = self.generate_lnorms(mesh)
				ptag = self.generate_ptag(mesh, material_names)
		
				if mesh.uv_layers:
					vmad_uvs = self.generate_vmad_uv(mesh)  # per face
		
				if not(self.option_idtech):
					creases = False
					for edge in mesh.edges:
						if edge.crease > 0:
							creases = True
							vmad_ew = self.generate_vmad_ew(mesh)
							break
			
					if mesh.shape_keys:
						vmap_morphs = self.generate_vmap_morph(mesh)
			
					if len(mobj.vertex_groups):
						vmap_weights = self.generate_vmap_weight(mobj)
		
				self.write_chunk(meshdata, "LAYR", layr); chunks.append(layr)
				self.write_chunk(meshdata, "PNTS", pnts); chunks.append(pnts)
				self.write_chunk(meshdata, "BBOX", bbox); chunks.append(bbox)
				if not(self.option_idtech):
					self.write_chunk(meshdata, "VMAP", vnorms); chunks.append(vnorms)
				if mesh.vertex_colors:
					if self.option_idtech:
						for vmad in rgba_vcs:
							self.write_chunk(meshdata, "VMAD", vmad)
							chunks.append(vmad)
					else:
						for vmad in rgb_vcs:
							self.write_chunk(meshdata, "VMAD", vmad)
							chunks.append(vmad)
				self.write_chunk(meshdata, "POLS", pols); chunks.append(pols)
				if not(self.option_idtech):
					if not(self.option_normaddon and 'vertex_normal_list' in mobj):
						self.write_chunk(meshdata, "VMAD", lnorms); chunks.append(lnorms)
				self.write_chunk(meshdata, "PTAG", ptag); chunks.append(ptag)
		
				if mesh.uv_layers:
					for vmad in vmad_uvs:
						self.write_chunk(meshdata, "VMAD", vmad)
						chunks.append(vmad)
				
				if not(self.option_idtech):
					if creases:
						self.write_chunk(meshdata, "VMAD", vmad_ew)
						chunks.append(vmad_ew)
		
					if len(mobj.vertex_groups):
						for vmap in vmap_weights:
							self.write_chunk(meshdata, "VMAP", vmap)
							chunks.append(vmap)
			
					if mesh.shape_keys:
						for vmap in vmap_morphs:
							self.write_chunk(meshdata, "VMAP", vmap)
							chunks.append(vmap)
		
				layer_index += 1
				
			surfs = list(surfs)
			for clip in self.clips:
				chunks.append(clip)
			for surf in surfs:
				chunks.append(surf)
		
			self.write_header(file, chunks)
			self.write_chunk(file, "TAGS", tags)
			file.write(meshdata.getvalue()); meshdata.close()
			for clip in self.clips:
				self.write_chunk(file, "CLIP", clip)
			for surf in surfs:
				self.write_chunk(file, "SURF", surf)
		
			file.close()
			
			bpy.ops.object.select_all(action='DESELECT')
			bpy.context.scene.objects.active = obj
			obj.select = True
			bpy.ops.object.delete()
			
			if not(self.option_batch):
				# if not batch exporting, all meshes of objects are already saved
				break
		
		for obj in objects:
			obj.select = True
		bpy.context.scene.objects.active = actobj
		
		
	# =======================================
	# === Generate Null-Terminated String ===
	# =======================================
	def generate_nstring(self, string):
		if len(string)%2 == 0:	# even
			string += "\0\0"
		else:					# odd
			string += "\0"
		return string
	
	# ===============================
	# === Get Used Material Names ===
	# ===============================
	def get_used_material_names(self):
		matnames = []
		matmeshes = []
		for mesh in self.meshes:
			if mesh.materials:
				for material in mesh.materials:
					if material:
						matmeshes.append(mesh)
						matnames.append(material.name)
			elif mesh.vertex_colors:
				matmeshes.append(mesh)
				matnames.append(self.LWO_VCOLOR_MATERIAL)
			else:
				matmeshes.append(mesh)
				matnames.append(self.LWO_DEFAULT_MATERIAL)
		return matmeshes, matnames
	
	# =========================================
	# === Generate Tag Strings (TAGS Chunk) ===
	# =========================================
	def generate_tags(self, material_names):
		data = io.BytesIO()
		if material_names:
			for mat in material_names:
				data.write(bytes(self.generate_nstring(mat), 'UTF-8'))
			return data.getvalue()
		else:
			return self.generate_nstring('')
	
	# ========================
	# === Generate Surface ===
	# ========================
	def generate_surface(self, mesh, name):
		#if name.find("\251 Per-") == 0:
		#	return generate_vcol_surf(mesh)
		if name == self.DEFAULT_NAME:
			return self.generate_default_surf()
		else:
			return self.generate_surf(mesh, name)
	
	# ===================================
	# === Generate Layer (LAYR Chunk) ===
	# ===================================
	def generate_layr(self, name, idx):
		px, py, pz = bpy.data.objects.get(name).location
		data = io.BytesIO()
		data.write(struct.pack(">h", idx))			# layer number
		data.write(struct.pack(">h", 0))			# flags
		data.write(struct.pack(">fff", px, pz, py))	# pivot
		data.write(bytes(self.generate_nstring(name.replace(" ","_").replace(".", "_")), 'UTF-8'))
		return data.getvalue()
	
	# ===================================
	# === Generate Verts (PNTS Chunk) ===
	# ===================================
	def generate_pnts(self, mesh):
		data = io.BytesIO()
		for i, v in enumerate(mesh.vertices):
			x, y, z = v.co
			x *= self.option_scale
			y *= self.option_scale
			z *= self.option_scale
			data.write(struct.pack(">fff", x, z, y))
		return data.getvalue()
	
	# ============================================
	# === Generate Vertex Normals (VMAP Chunk) ===
	# ============================================
	def generate_vnorms(self, mesh, nolist):
		data = io.BytesIO()
		name = self.generate_nstring("vert_normals")
		data.write(b"NORM")										# type
		data.write(struct.pack(">H", 3))						# dimension
		data.write(bytes(name, 'UTF-8')) 						# name
		for i, v in enumerate(mesh.vertices):
			if nolist:
				x, y, z = nolist[i]['normal']
			else:
				x, y, z = v.normal
			x *= self.option_scale
			y *= self.option_scale
			z *= self.option_scale
			data.write(self.generate_vx(i)) # vertex index
			data.write(struct.pack(">fff", x, z, y))
		return data.getvalue()
	
	# ============================================
	# === Generate Loop Normals (VMAD Chunk) ===
	# ============================================
	def generate_lnorms(self, mesh):
		mesh.calc_normals_split()
		data = io.BytesIO()
		name = self.generate_nstring("vert_normals")
		data.write(b"NORM")										# type
		data.write(struct.pack(">H", 3))						# dimension
		data.write(bytes(name, 'UTF-8')) 						# name
		for i, p in enumerate(mesh.polygons):
			for li in p.loop_indices:
				l = mesh.loops[li]
				x, y, z = l.normal
				x *= self.option_scale
				y *= self.option_scale
				z *= self.option_scale
				data.write(self.generate_vx(l.vertex_index)) # vertex index
				data.write(self.generate_vx(i)) # face index
				data.write(struct.pack(">fff", x, z, y))
		return data.getvalue()
	
	# ==========================================
	# === Generate Bounding Box (BBOX Chunk) ===
	# ==========================================
	def generate_bbox(self, mesh):
		data = io.BytesIO()
		# need to transform verts here
		if mesh.vertices:
			nv = [v.co for v in mesh.vertices]
			xx = [ co[0] * self.option_scale for co in nv ]
			yy = [ co[1] * self.option_scale for co in nv ]
			zz = [ co[2] * self.option_scale for co in nv ]
		else:
			xx = yy = zz = [0.0,]
		
		data.write(struct.pack(">6f", min(xx), min(zz), min(yy), max(xx), max(zz), max(yy)))
		return data.getvalue()
	
	# ========================================
	# === Average All Vertex Colors (Fast) ===
	# ========================================
	'''
	def average_vertexcolors(self, mesh):
		vertexcolors = {}
		vcolor_add = lambda u, v: [u[0]+v[0], u[1]+v[1], u[2]+v[2], u[3]+v[3]]
		vcolor_div = lambda u, s: [u[0]/s, u[1]/s, u[2]/s, u[3]/s]
		for i, f in enumerate(mesh.faces):	# get all vcolors that share this vertex
			if not i%100:
				Blender.Window.DrawProgressBar(float(i)/len(mesh.verts), "Finding Shared VColors")
			col = f.col
			for j in range(len(f)):
				index = f[j].index
				color = col[j]
				r,g,b = color.r, color.g, color.b
				vertexcolors.setdefault(index, []).append([r,g,b,255])
		i = 0
		for index, value in vertexcolors.iteritems():	# average them
			if not i%100:
				Blender.Window.DrawProgressBar(float(i)/len(mesh.verts), "Averaging Vertex Colors")
			vcolor = [0,0,0,0]	# rgba
			for v in value:
				vcolor = vcolor_add(vcolor, v)
			shared = len(value)
			value[:] = vcolor_div(vcolor, shared)
			i+=1
		return vertexcolors
	'''
	
	# ====================================================
	# === Generate RGBA Vertex Colors (VMAD Chunk) ===
	# ====================================================
	def generate_rgba_vc(self, mesh):
		alldata = []
		layers = mesh.vertex_colors
		for l in layers:
			vcname = self.generate_nstring(l.name)
			data = io.BytesIO()
			data.write(b"RGBA")										# type
			data.write(struct.pack(">H", 4))						# dimension
			data.write(bytes(vcname, 'UTF-8')) # name
			
			found = False
			for i, p in enumerate(mesh.polygons):
				p_vi = p.vertices
				for v, loop in zip(p.vertices, p.loop_indices):
					r,g,b = tuple(l.data[loop].color)
					data.write(self.generate_vx(v)) # vertex index
					data.write(self.generate_vx(i)) # face index
					data.write(struct.pack(">ffff", r, g, b, 0.5))
					found = True
			if found:
				alldata.append(data.getvalue())
					
		return alldata
	
	# ====================================================
	# === Generate RGB Vertex Colors (VMAD Chunk) ===
	# ====================================================
	def generate_rgb_vc(self, mesh):
		alldata = []
		layers = mesh.vertex_colors
		for l in layers:
			vcname = self.generate_nstring(l.name)
			data = io.BytesIO()
			data.write(b"RGB ")										# type
			data.write(struct.pack(">H", 3))						# dimension
			data.write(bytes(vcname, 'UTF-8')) # name
			
			found = False
			for i, p in enumerate(mesh.polygons):
				p_vi = p.vertices
				for v, loop in zip(p.vertices, p.loop_indices):
					r,g,b = tuple(l.data[loop].color)
					data.write(self.generate_vx(v)) # vertex index
					data.write(self.generate_vx(i)) # face index
					data.write(struct.pack(">fff", r, g, b))
					found = True
			if found:
				alldata.append(data.getvalue())
					
		return alldata
	
	# ================================================
	# === Generate Per-Face UV Coords (VMAD Chunk) ===
	# ================================================
	def generate_vmad_uv(self, mesh):
		alldata = []
		layers = mesh.uv_layers
		for l in layers:
			uvname = self.generate_nstring(l.name)
			data = io.BytesIO()
			data.write(b"TXUV")										 # type
			data.write(struct.pack(">H", 2))						 # dimension
			data.write(bytes(uvname, 'UTF-8')) # name
			
			found = False
			for i, p in enumerate(mesh.polygons):
				for v, loop in zip(p.vertices, p.loop_indices):
					searchl = list(p.loop_indices)
					searchl.extend(list(p.loop_indices))
					pos = searchl.index(loop)
					prevl = searchl[pos - 1]
					nextl = searchl[pos + 1]
					youv = l.data[loop].uv
					if l.data[prevl].uv == youv == l.data[nextl].uv:
						continue
					data.write(self.generate_vx(v)) # vertex index
					data.write(self.generate_vx(i)) # face index
					data.write(struct.pack(">ff", youv[0], youv[1]))
					found = True
			if found:
				alldata.append(data.getvalue())
				
		return alldata
	
	# ================================================
	# === Generate Edge Weights (VMAD Chunk) ===
	# ================================================
	def generate_vmad_ew(self, mesh):
		data = io.BytesIO()
		data.write(b"WGHT")										 # type
		data.write(struct.pack(">H", 1))						 # dimension
		data.write(bytes(self.generate_nstring("Edge Weight"), 'UTF-8')) # name
		face_edge_map = {ek: mesh.edges[i] for i, ek in enumerate(mesh.edge_keys)}
		for i, p in enumerate(mesh.polygons):
			vs = list(p.vertices)
			for ek in p.edge_keys:
				edge = face_edge_map[ek]
				if edge.crease == 0:
					continue
				v1, v2 = edge.vertices
				if vs[vs.index(v1) - 1] == v2:
					vi = v1
				else:
					vi = v2
				data.write(self.generate_vx(vi)) # vertex index
				data.write(self.generate_vx(i)) # face index
				data.write(struct.pack(">f", edge.crease))
					
		return data.getvalue()
	
	# ================================================
	# === Generate Endomorphs (VMAP Chunk) ===
	# ================================================
	def generate_vmap_morph(self, mesh):
		alldata = []
		keyblocks = mesh.shape_keys.key_blocks
		for kb in keyblocks:
			emname = self.generate_nstring(kb.name)
			data = io.BytesIO()
			data.write(b"MORF")										 # type
			data.write(struct.pack(">H", 3))						 # dimension
			data.write(bytes(emname, 'UTF-8')) # name
			for i, v in enumerate(mesh.vertices):
				x, y, z = kb.data[v.index].co - v.co
				data.write(self.generate_vx(v.index)) # vertex index
				data.write(struct.pack(">fff", x, z, y))
			alldata.append(data.getvalue())
					
		return alldata
	
	# ================================================
	# === Generate Weightmap (VMAP Chunk) ===
	# ================================================
	def generate_vmap_weight(self, obj):
		alldata = []
		vgroups = obj.vertex_groups
		for vg in vgroups:
			vgname = self.generate_nstring(vg.name)
			data = io.BytesIO()
			data.write(b"WGHT")										 # type
			data.write(struct.pack(">H", 1))						 # dimension
			data.write(bytes(vgname, 'UTF-8')) # name
			for i, v in enumerate(obj.data.vertices):
				w = 0.0
				try:
					w = vg.weight(v.index)
				except:
					pass
				data.write(self.generate_vx(v.index)) # vertex index
				data.write(struct.pack(">f", w))
			alldata.append(data.getvalue())
					
		return alldata
	
	# ======================================
	# === Generate Variable-Length Index ===
	# ======================================
	def generate_vx(self, index):
		if index < 0xFF00:
			value = struct.pack(">H", index)				 # 2-byte index
		else:
			value = struct.pack(">L", index | 0xFF000000)	 # 4-byte index
		return value
	
	# ===================================
	# === Generate Faces (POLS Chunk) ===
	# ===================================
	def generate_pols(self, mesh, subd):
		data = io.BytesIO()
		if subd:
			data.write(b"SUBD") # subpatch polygon type
		else:
			data.write(b"FACE") # normal polygon type
		for i,p in enumerate(mesh.polygons):
			data.write(struct.pack(">H", len(p.vertices))) # numfaceverts
			numfaceverts = len(p.vertices)
			p_vi = p.vertices
			for j in range(numfaceverts-1, -1, -1):			# Reverse order
				data.write(self.generate_vx(p_vi[j]))
		bm = bmesh.new()
		bm.from_mesh(mesh)
		for e in bm.edges:
			if len(e.link_faces) == 0:
				data.write(struct.pack(">H", 2))
				data.write(self.generate_vx(e.verts[0].index))
				data.write(self.generate_vx(e.verts[1].index))		
		bm.to_mesh(mesh)
		
		return data.getvalue()
	
	# =================================================
	# === Generate Polygon Tag Mapping (PTAG Chunk) ===
	# =================================================
	def generate_ptag(self, mesh, material_names):
		data = io.BytesIO()
		data.write(b"SURF")
		for poly in mesh.polygons:
			if mesh.materials:
				matindex = poly.material_index
				matname = mesh.materials[matindex].name
				surfindex = material_names.index(matname)
				
				data.write(self.generate_vx(poly.index))
				data.write(struct.pack(">H", surfindex)) 
			else:
				data.write(self.generate_vx(poly.index))
				data.write(struct.pack(">H", 0)) 
		return data.getvalue()
	
	# ===================================================
	# === Generate VC Surface Definition (SURF Chunk) ===
	# ===================================================
	"""
	def generate_vcol_surf(mesh):
		data = io.BytesIO()
		if len(mesh.vertex_colors):
			surface_name = self.generate_nstring(self.VCOL_NAME)
		data.write(surface_name)
		data.write(b"\0\0")
	
		data.write(b"COLR")
		data.write(struct.pack(">H", 14))
		data.write(struct.pack(">fffH", 1, 1, 1, 0))
	
		data.write(b"DIFF")
		data.write(struct.pack(">H", 6))
		data.write(struct.pack(">fH", 0.0, 0))
	
		data.write(b"LUMI")
		data.write(struct.pack(">H", 6))
		data.write(struct.pack(">fH", 1.0, 0))
	
		data.write(b"VCOL")
		data.write(struct.pack(">H", 34))
		data.write(struct.pack(">fH4s", 1.0, 0, "RGB "))  # intensity, envelope, type
		data.write(bytes(map(ord, self.generate_nstring(mesh.vert_colors.active.name)))) # name
	
		data.write(b"CMNT") # material comment
		comment = "Vertex Colors: Exported from Blender\256 2.70"
		comment = self.generate_nstring(comment)
		data.write(struct.pack(">H", len(comment)))
		data.write(bytes(map(ord, comment)))
		return data.getvalue()
	"""
	
	# ================================================
	# === Generate Surface Definition (SURF Chunk) ===
	# ================================================
	def generate_surf(self, mesh, material_name):
		data = io.BytesIO()
		data.write(bytes(self.generate_nstring(material_name), 'UTF-8'))
		
		try:
			material = bpy.data.materials.get(material_name)
			R,G,B = material.diffuse_color[0], material.diffuse_color[1], material.diffuse_color[2]
			diff = material.diffuse_intensity
			lumi = material.emit
			spec = material.specular_intensity
			gloss = math.sqrt((material.specular_hardness - 4) / 400)
			if material.raytrace_mirror.use:
				refl = material.raytrace_mirror.reflect_factor
			else:
				refl = 0.0
			rblr = 1.0 - material.raytrace_mirror.gloss_factor
			rind = material.raytrace_transparency.ior
			tran = 1.0 - material.alpha
			tblr = 1.0 - material.raytrace_transparency.gloss_factor
			trnl = material.translucency
			if mesh.use_auto_smooth:
				sman = mesh.auto_smooth_angle
			else:
				sman = 0.0
			
			
		except:
			material = None
			
			R=G=B = 1.0
			diff = 1.0
			lumi = 0.0
			spec = 0.2
			hard = 0.0
			gloss = 0.0
			refl = 0.0
			rblr = 0.0
			rind = 1.0
			tran = 0.0
			tblr = 0.0
			trnl = 0.0
			sman = 0.0
		
			
		data.write(b"COLR")
		data.write(struct.pack(">H", 0))
		
		data.write(b"COLR")
		data.write(struct.pack(">H", 14))
		data.write(struct.pack(">fffH", R, G, B, 0))
	
		data.write(b"DIFF")
		data.write(struct.pack(">H", 6))
		data.write(struct.pack(">fH", diff, 0))
	
		data.write(b"LUMI")
		data.write(struct.pack(">H", 6))
		data.write(struct.pack(">fH", lumi, 0))
	
		data.write(b"SPEC")
		data.write(struct.pack(">H", 6))
		data.write(struct.pack(">fH", spec, 0))
	
		if not(self.option_idtech):
			data.write(b"REFL")
			data.write(struct.pack(">H", 6))
			data.write(struct.pack(">fH", refl, 0))
		
			data.write(b"RBLR")
			data.write(struct.pack(">H", 6))
			data.write(struct.pack(">fH", rblr, 0))
		
			data.write(b"TRAN")
			data.write(struct.pack(">H", 6))
			data.write(struct.pack(">fH", tran, 0))
		
			data.write(b"RIND")
			data.write(struct.pack(">H", 6))
			data.write(struct.pack(">fH", rind, 0))
			
			data.write(b"TBLR")
			data.write(struct.pack(">H", 6))
			data.write(struct.pack(">fH", tblr, 0))
			
			data.write(b"TRNL")
			data.write(struct.pack(">H", 6))
			data.write(struct.pack(">fH", trnl, 0))
		
		data.write(b"GLOS")
		data.write(struct.pack(">H", 6))
		data.write(struct.pack(">fH", gloss, 0))
	
		if material:
			vcname = material.vcmenu
			if vcname != "<none>":
				data.write(b"VCOL")
				data_tmp = io.BytesIO()
				data_tmp.write(struct.pack(">fH4s", 1.0, 0, b"RGBA"))  # intensity, envelope, type
				data_tmp.write(bytes(self.generate_nstring(vcname), 'UTF-8')) # name
				data.write(struct.pack(">H", len(data_tmp.getvalue())))
				data.write(data_tmp.getvalue())
	
		data.write(b"SMAN")
		data.write(struct.pack(">H", 4))
		if self.option_idtech:
			data.write(struct.pack(">f", sman))
		elif self.option_smooth:
			data.write(struct.pack(">f", sman))
		else:
			data.write(struct.pack(">f", 0))
	
#		data.write(b"SIDE")
#		data.write(struct.pack(">H", 2))
#		data.write(struct.pack(">H", 3))
	
		if not(self.option_idtech):
			# Check if the material contains any image maps
			def make_ord(nbloks, index):
				i = 8
				d = 16
				while i < 128:
					if i >= nbloks:
						break;
					d /= 2
					i *= 2
				ordinal  = int(128 + index * d)
				return ordinal
	
			if material:
				mtextures = list(material.texture_slots)	# Get a list of textures linked to the material
				for mtex in mtextures:
					if mtex:
						tex = mtex.texture
						if (tex.type == 'IMAGE'):	# Check if the texture is of type "IMAGE"
							path = tex.image.filepath
							if path in self.clippaths:
								clipid = self.clippaths.index(path)
							else:
								self.clippaths.append(path)
								clipid = self.currclipid
								self.clips.append(self.generate_clip(path))
								
							def write_tex_blok(data, channel, opac):
								data.write(b"BLOK")		# Surface BLOK header
				
								# IMAP subchunk (image map sub header)
								data_blok = io.BytesIO()
								data_blok.write(b"IMAP")					
								data_tmp = io.BytesIO()
								data_tmp.write(struct.pack(">B", make_ord(len(mtextures), clipid)))  # ordinal string
								data_tmp.write(struct.pack(">B", 0))
								data_tmp.write(b"CHAN")
								data_tmp.write(struct.pack(">H", 4))
								data_tmp.write(bytes(channel, 'UTF-8'))
								opactype = 0
								if mtex.blend_type == 'SUBTRACT':
									opactype = 1
								elif mtex.blend_type == 'DIFFERENCE':
									opactype = 2
								elif mtex.blend_type == 'MULTIPLY':
									opactype = 3
								elif mtex.blend_type == 'DIVIDE':
									opactype = 4
								elif mtex.blend_type == 'ADD':
									opactype = 7
								data_tmp.write(b"OPAC")				  # Hardcoded texture layer opacity
								data_tmp.write(struct.pack(">H", 8))
								data_tmp.write(struct.pack(">H", opactype))
								data_tmp.write(struct.pack(">f", opac))
								data_tmp.write(struct.pack(">H", 0))
								data_tmp.write(b"ENAB")
								data_tmp.write(struct.pack(">HH", 2, 1))  # 1 = texture layer enabled
								nega = mtex.invert
								data_tmp.write(b"NEGA")
								data_tmp.write(struct.pack(">HH", 2, nega))  # Disable negative image (1 = invert RGB values)
								data_tmp.write(b"AXIS")
								data_tmp.write(struct.pack(">HH", 2, 1))
								data_blok.write(struct.pack(">H", len(data_tmp.getvalue())))
								data_blok.write(data_tmp.getvalue())
				
								# IMAG subchunk
								data_blok.write(b"IMAG")
								data_blok.write(struct.pack(">HH", 2, clipid))
								data_blok.write(b"PROJ")
								data_blok.write(struct.pack(">HH", 2, 5)) # UV projection
				
								data_blok.write(b"VMAP")
								uvname = self.generate_nstring(mtex.uv_layer)
								data_blok.write(struct.pack(">H", len(uvname)))
								data_blok.write(bytes(uvname, 'UTF-8'))
			
								data.write(struct.pack(">H", len(data_blok.getvalue())))
								data.write(data_blok.getvalue())
								
								return data
			
							if mtex.use_map_color_diffuse:
								opac = mtex.diffuse_color_factor
								write_tex_blok(data, "COLR", opac)
								
							if mtex.use_map_diffuse:
								opac = mtex.diffuse_factor
								write_tex_blok(data, "DIFF", opac)
								
							if mtex.use_map_emit:
								opac = mtex.emit_factor
								write_tex_blok(data, "LUMI", opac)
								
							if mtex.use_map_specular:
								opac = mtex.specular_factor
								write_tex_blok(data, "SPEC", opac)
								
							if mtex.use_map_hardness:
								opac = mtex.hardness_factor
								write_tex_blok(data, "GLOS", opac)
								
							if mtex.use_map_raymir:
								opac = mtex.raymir_factor
								write_tex_blok(data, "REFL", opac)
								
							if mtex.use_map_alpha:
								opac = mtex.alpha_factor
								write_tex_blok(data, "TRAN", opac)
								
							if mtex.use_map_translucency:
								opac = mtex.translucency_factor
								write_tex_blok(data, "TRNL", opac)
								
	#						if mtex.use_map_normal:
	#							opac = mtex.normal_factor
	#							write_tex_blok(data, "BUMP", opac)
				
		return data.getvalue()
	
	# =============================================
	# === Generate Default Surface (SURF Chunk) ===
	# =============================================
	def generate_default_surf(self):
		data = io.BytesIO()
		material_name = self.DEFAULT_NAME
		data.write(bytes(self.generate_nstring(material_name), 'UTF-8'))
	
		data.write(b"COLR")
		data.write(struct.pack(">H", 14))
		data.write(struct.pack(">fffH", 0.9, 0.9, 0.9, 0))
	
		data.write(b"DIFF")
		data.write(struct.pack(">H", 6))
		data.write(struct.pack(">fH", 0.8, 0))
	
		data.write(b"LUMI")
		data.write(struct.pack(">H", 6))
		data.write(struct.pack(">fH", 0, 0))
	
		data.write(b"SPEC")
		data.write(struct.pack(">H", 6))
		data.write(struct.pack(">fH", 0.4, 0))
	
		data.write(b"GLOS")
		data.write(struct.pack(">H", 6))
		gloss = 50 / (255/2.0)
		gloss = round(gloss, 1)
		data.write(struct.pack(">fH", gloss, 0))
	
		return data.getvalue()
	
	# ==================================================
	# === Generate Thumbnail Icon Image (ICON Chunk) ===
	# ==================================================
	"""
	def generate_icon(self):
		data = io.BytesIO()
		file = open("f:/obj/radiosity/lwo2_icon.tga", "rb") # 60x60 uncompressed TGA
		file.read(18)
		icon_data = file.read(3600) # ?
		file.close()
		data.write(struct.pack(">HH", 0, 60))
		data.write(icon_data)
		#print len(icon_data)
		return data.getvalue()
	"""
	
	# ===============================================
	# === Generate CLIP chunk with STIL subchunks ===
	# ===============================================
	def generate_clip(self, pathname):
		data = io.BytesIO()
		pathname = pathname[0:2] + pathname.replace("\\", "/")[2:]	# Convert to Modo standard path
		imagename = self.generate_nstring(pathname)
		data.write(struct.pack(">L", self.currclipid))						# CLIP sequence/id
		data.write(b"STIL")											# STIL image
		data.write(struct.pack(">H", len(imagename)))				# Size of image name
		data.write(bytes(imagename, 'UTF-8'))
		self.currclipid += 1
		return data.getvalue()
	
	# ===================
	# === Write Chunk ===
	# ===================
	def write_chunk(self, file, name, data):
		file.write(bytes(name, 'UTF-8'))
		file.write(struct.pack(">L", len(data)))
		file.write(data)
	
	# =============================
	# === Write LWO File Header ===
	# =============================
	def write_header(self, file, chunks):
		chunk_sizes = map(len, chunks)
		chunk_sizes = functools.reduce(operator.add, chunk_sizes)
		form_size = chunk_sizes + len(chunks)*8 + len("FORM")
		file.write(b"FORM")
		file.write(struct.pack(">L", form_size))
		file.write(b"LWO2")
	

def menu_func(self, context):
	self.layout.operator(LwoExport.bl_idname, text="Lightwave (.lwo)")

def register():
	bpy.app.handlers.scene_update_post.append(sceneupdate_handler)

	bpy.utils.register_module(__name__)

	bpy.types.INFO_MT_file_export.append(menu_func)

def unregister():
	bpy.app.handlers.scene_update_post.remove(sceneupdate_handler)

	bpy.utils.unregister_module(__name__)

	bpy.types.INFO_MT_file_export.remove(menu_func)

if __name__ == "__main__":
  register()
  
  
  
@persistent
def sceneupdate_handler(dummy):

	ob = bpy.context.active_object
	if ob:
		if ob.type == 'MESH':
			mesh = bpy.context.active_object.data
		
			itemlist = [("<none>", "<none>", "<none>")]
			vcs = mesh.vertex_colors
			for vc in vcs:
				itemlist.append((vc.name, vc.name, "Vertex Color Map"))
			bpy.types.Material.vcmenu = EnumProperty(
					items = itemlist,
					name = "Vertex Color Map",
					description = "LWO export: vertex color map for this material")

	return {'RUNNING_MODAL'}

  

