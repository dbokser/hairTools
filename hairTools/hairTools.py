"""
------------------------------------------
hairTools.py
Author: David Bokser
email: me@davidbokser.com

Website : http://www.davidbokser.com
------------------------------------------

Helps create multi-level hair curves along a poly mesh, with tools
for styling and trimming.

Usage:
import hairTools.hairTools as hairTools
hairTools.hairballUI()

COPYRIGHT DAVID BOKSER 2010-2013.
================================================================
"""

_version = '1.5'

import maya.cmds as mc
import maya.mel as mel
import copy
import random

def hairballUI():
	window = mc.window( title="Hairball v%s" % _version, iconName='hairball', widthHeight=(200, 55) )

	mc.scrollLayout( 'scrollLayout' )
	mc.columnLayout( adjustableColumn=True )
	mc.button(label='Reload', command='''
import maya.cmds as mc
import hairTools.hairTools as hairTools
mc.deleteUI( "%s", window=True)
hairTools.hairballUI()
''' % window)
	mc.frameLayout( label='Grow', labelAlign='center', borderStyle='etchedIn' )
	mc.columnLayout( adjustableColumn=True )	
	densityField = mc.floatSliderGrp( label='Density', cw3=[80, 80, 120], field=True, value = .4, fs=.01, minValue=.01, maxValue=1.0, fmx=200.0 )
	layerField = mc.intSliderGrp( label='Layers', cw3=[80, 80, 120], field=True, value = 5, minValue=1, maxValue=15, fmx=200 )
	twistField = mc.floatSliderGrp( label='Twist', cw3=[80, 80, 120], field=True, value = 0, fs=.01, minValue=-1.0, maxValue=1.0, fmx=5.0, fmn=-5.0 )
	mc.button( label='Cough it up!', command='''
import maya.cmds as mc
import hairTools.hairTools as hairTools
hairTools.makeHair(mc.ls(sl=True, fl=True), mc.floatSliderGrp("%s", q=True, value=True), mc.intSliderGrp("%s", q=True, v=True), mc.floatSliderGrp("%s", q=True, value=True))
''' % (densityField, layerField, twistField))
	mc.setParent( '..' )
	mc.setParent( '..' )
	
	mc.frameLayout( label='Groom', labelAlign='center', borderStyle='etchedIn' )
	mc.columnLayout( adjustableColumn = True)
	rand1Field = mc.floatSliderGrp( label='Start', cw3=[80, 80, 120], field=True, value = .1, fs=.1, minValue=0, maxValue=5.0, fmx=200.0 )
	rand2Field = mc.floatSliderGrp( label='Middle', cw3=[80, 80, 120], field=True, value = .4, fs=.1, minValue=0, maxValue=5.0, fmx=200.0 )
	rand3Field = mc.floatSliderGrp( label='End', cw3=[80, 80, 120], field=True, value = .6, fs=.1, minValue=0, maxValue=5.0, fmx=200.0 )
	mc.button( label='Muss it up.', command='''
import maya.cmds as mc
import hairTools.hairTools as hairTools
hairTools.randomizeHair(mc.ls(sl=True, fl=True), [mc.floatSliderGrp("%s", q=True, value=True), mc.floatSliderGrp("%s", q=True, v=True), mc.floatSliderGrp("%s", q=True, v=True)])
	''' % (rand1Field, rand2Field, rand3Field))
	mc.setParent( '..' )
	mc.setParent( '..' )
	
	mc.frameLayout( label='Trim', labelAlign='center', borderStyle='etchedIn' )
	mc.columnLayout( adjustableColumn = True)
	minTrimField = mc.floatSliderGrp( label='Min Length', cw3=[80, 80, 120], field=True, value = .3, fs=.1, minValue=0.1, maxValue=1.0 )
	percentTrimField = mc.floatSliderGrp( label='Percent to trim', cw3=[80, 80, 120], field=True, value = .5, fs=.1, minValue=0.1, maxValue=1.0 )
	mc.button( label='A little off the top.', command='''
import maya.cmds as mc
import hairTools.hairTools as hairTools
hairTools.trimHair(mc.ls(sl=True), mc.floatSliderGrp("%s", q=True, value=True), mc.floatSliderGrp("%s", q=True, value=True))
	''' % (minTrimField, percentTrimField))
	mc.setParent( '..' )
	mc.setParent( '..' )
	
	mc.showWindow( window )

	mc.window(window, e=True, w=310, h=400)

def makeHair(firstLoop, density, layers, twist=0.0):
	firstLoop = mc.ls(mc.polyListComponentConversion(firstLoop, fe=True, fv=True, tv=True), fl=True)
	
	# DO A LITTLE ERROR CHECKING TO SEE IF WE GOT WHAT WE NEED
	neighbor = getNeighboringEdgeloops(firstLoop)
	if len(neighbor) != len(firstLoop):
		mel.eval('warning "Selected edgeloop is not a border loop. Please select a border loop and try again."')
		return None
	
	# CREATE THE HULL CURVES
	if twist < 0:
		numIntermediates = round((twist*-1)/.1)-1
	else:
		numIntermediates = round(twist/.1)-1
	if numIntermediates < 0:
		numIntermediates = 0
	hullCurves = makeHullCurves(firstLoop, numIntermediates)
	
	twist /= numIntermediates + 1.0
	
	objName = firstLoop[0].split('.')[0]
	
	# CREATE ALL THE HAIR CURVES
	allHairCurves = []
	for i in range(layers):
		for curve in hullCurves:
			s = (i+1)/(layers*1.0)
			mc.setAttr(curve+'.scale', s, s, s, type='double3')
		allHairCurves += makeHairCurves(hullCurves, density, twist)
	
	# DO SOME SPRING CLEANING
	mc.delete(hullCurves)
	for i in range(len(allHairCurves)):
		curveNum = str(i+1)
		allHairCurves[i] = mc.rename(allHairCurves[i], '%s_%sCRV' % (objName, curveNum))
	
	if len(allHairCurves) > 0:
		hairGrp = mc.rename(mc.group(allHairCurves), objName + '_hairCurves')
	else:
		mel.eval('warning "No hair curves made. Perhaps Density value is too high."')
	
def makeHullCurves(firstLoop, numIntermediates=0):
	verts = mc.ls(mc.polyListComponentConversion(firstLoop, fe=True, fv=True, tv=True), fl=True)
		
	edgeVerts = orderEdgeloopVerts(verts)
	firstVert = edgeVerts[0]
	dirVert = edgeVerts[1]
	
	obj = verts[0].split('.')[0]
	numObjVerts = mc.polyEvaluate(obj, vertex=True)
	
	numEdges = numObjVerts / len(edgeVerts)
	
	if numObjVerts%len(edgeVerts) != 0:
		mel.eval('warning("Number of verts in edge loops must be the same throughout mesh.")')
		return False
	
	usedVerts = []
	edgeCurves = []
	edgeLoops = []
	usedVertOrder = []
	for i in range(numEdges):
		# MAKE CURVES
		currentEdge = makeCurveFromVerts(edgeVerts)[0]
		if i != 0 and numIntermediates != 0:
			edgeCurves += makeIntermediateCurves(edgeCurves[-1], currentEdge, numIntermediates)
		edgeCurves.append(currentEdge)
		
		# KEEP TRACK OF USED VERTS
		for vert in edgeVerts:
			if vert not in usedVerts:
				usedVerts.append(vert)
		usedVertOrder.append(copy.copy(usedVerts))
		
		# GET NEXT LOOP
		edgeLoops.append(edgeVerts)
		neighbors = mc.ls(getNeighboringEdgeloops(edgeVerts), fl=True)
		edgeVerts = []
		for vert in neighbors:
			if vert not in usedVerts:
				edgeVerts.append(vert)
		if len(edgeVerts):
			firstVert = findCorrespondingVertInLoop(firstVert, edgeVerts)
			dirVert = findCorrespondingVertInLoop(dirVert, edgeVerts)
			edgeVerts = orderEdgeloopVerts(edgeVerts, start=firstVert, direction=dirVert)
		
	return edgeCurves

def makeIntermediateCurves(curve1, curve2, numIntermediates=1, close=True):
	cShape1 = mc.listRelatives(curve1, shapes=True)[0]
	cShape2 = mc.listRelatives(curve2, shapes=True)[0]
	
	numCV1 = mc.getAttr(cShape1+'.spans') + mc.getAttr(cShape1+'.degree')
	numCV2 = mc.getAttr(cShape2+'.spans') + mc.getAttr(cShape2+'.degree')
	
	if numCV1 != numCV2:
		mel.eval('warning "Number of CVs between curves are not equal. Can\'t create intermediate curves"')
		return []
	
	step = 1.0/(numIntermediates+1)
	allCurves = []
	for p in range(1, numIntermediates+1):
		points = []
		for i in range(mc.getAttr(cShape1+'.spans')):
			p1 = mc.pointPosition('%s.cv[%i]' % (curve1,i))
			p2 = mc.pointPosition('%s.cv[%i]' % (curve2,i))
			v = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
			p3 = (p1[0]+(v[0]*step*p), p1[1]+(v[1]*step*p), p1[2]+(v[2]*step*p))
			points.append(p3)
		allCurves += makeCurveFromPoints(points, close)
		allCurves[-1] = mc.rename(allCurves[-1], 'intCurve1')
	return allCurves
		
def orderEdgeloopVerts(verts, start=None, direction=None):
	'''
	Orders a list of verts in an edge loop.
	Assumes the verts are actually in an edge loop,
	otherwise will freeze Maya, so be WARNED!!
	'''
	allEdgeVerts = copy.copy(verts)
	
	orderedVerts = []
	if not start:
		start = verts.pop(0)
	else:
		if start in verts:
			verts.remove(start)
		else:
			mel.eval('warning("given start vert is not in edge verts, using default")')
			start = verts.pop(0)
	if direction and direction in verts:
		verts.remove(direction)
	else:
		adjacentVerts = mc.ls(mc.polyListComponentConversion(mc.polyListComponentConversion(start, fv=True, te=True), fe=True, tv=True),fl=True)
		for vert in adjacentVerts:
			if vert in verts:
				direction = vert
		verts.remove(direction)
	
	orderedVerts.append(start)
	orderedVerts.append(direction)
	
	while len(verts) > 1:
		adjacentVerts = mc.ls(mc.polyListComponentConversion(mc.polyListComponentConversion(orderedVerts[-1], fv=True, te=True), fe=True, tv=True), fl=True)
		for vert in adjacentVerts:
			if vert in verts:
				orderedVerts.append(vert)
				verts.remove(orderedVerts[-1])
	
	orderedVerts.append(verts[0])
	return orderedVerts

def makeCurveFromVerts(verts, close=True):
	p = []
	for vert in verts:
		p.append(mc.pointPosition(vert))

	return makeCurveFromPoints(p, close)

def makeCurveFromPoints(p, close=True):
	curve = mc.curve(p=p, d=3)
	if close:
		curve = mc.closeCurve(curve, ps=0, rpo=1, bb=0.5, bki=0, p=0.1)
	curve = mc.rebuildCurve(curve, rpo=1, rt=0, end=1, kr=0, kcp=1, kep=1, kt=0, s=4, d=3, tol=0.000129167)
	
	mc.xform(curve, centerPivots=True)
	
	return curve

def getNeighboringEdgeloops(edgeLoop):
	'''
	Get the neighboring edge loop. 
	Takes in and returns verts, not edges
	'''
	expandedVerts = mc.ls(mc.polyListComponentConversion(mc.polyListComponentConversion(edgeLoop, fv=True, te=True), fe=True, tv=True), fl=True)
	expandedEdgeVerts = mc.ls(edgeLoop, fl=True)
	
	for vert in expandedEdgeVerts:
		if vert in expandedVerts:
			expandedVerts.remove(vert)
	
	return mc.ls(expandedVerts, fl=True)
	
def findCorrespondingVertInLoop(vert, edgeLoop):
	'''
	Finds a vert on the edgeLoop whose edge is shared with the given vert
	'''
	nearestVerts = mc.ls(mc.polyListComponentConversion(mc.polyListComponentConversion(vert, fv=True, te=True), fe=True, tv=True), fl=True)
	for vert in nearestVerts:
		if vert in edgeLoop:
			return vert
	
	return None

def makeHairCurves(hullCurves, d, twist = 0.0):
	'''
	Populate a hull with hair curves based on arclen of the biggest curve
	'''
	largestArclen = 0
	for curve in hullCurves:
		arclen = mc.arclen(curve)
		if arclen > largestArclen:
			largestArclen = arclen
	
	numCurves = largestArclen / (d * 1.0)
	
	allCurves = []
	for i in range(int(numCurves)):
		allCurves.append(makeHairCurve(hullCurves, i/numCurves, twist))

	return allCurves

def makeHairCurve(hullCurves, u, twist=0.0):
	'''
	Create a curve through a series of hull curves by u parameter
	'''
	p = []
	i = 0
	for hull in hullCurves:
		p.append(mc.pointPosition('%s.u[%f]' % (hull, (u+(twist*i))%1.0 ) ))
		i+=1
		
	curve = mc.curve(p=p, d=3)
	curve = mc.rebuildCurve(curve, rpo=1, rt=0, end=1, kr=0, kcp=1, kep=1, kt=0, s=4, d=3, tol=0.000129167)

	mc.xform(curve, centerPivots=True)

	return curve

def randomizeHair(curves, rMult = []):
	'''
	random.randomizes the cvs on a set of selected curves.
	Takes in an array that will be multiplied against the random.random value
	so that the user has more control of random.randomization along the curve.
	'''
	
	# FIND THE MAX NUMBER OF CVS
	longestCVCount = 0
	for curve in curves:
		numCV = mc.getAttr( curve+'.degree' ) + mc.getAttr( curve+'.spans' )
		if numCV > longestCVCount:
			longestCVCount = numCV

	# GET MULT MODIFIER VALUES FOR EACH CV
	numMult = len(rMult)-1
	numCVSplit = longestCVCount / numMult
	cvMult = []
	for i in range(longestCVCount):
		p = i/numCVSplit
		m = (i%numCVSplit)/(numCVSplit*1.0)
		try:
			dif = rMult[p+1] - rMult[p]
		except:
			dif = rMult[p]
		cvMult.append( (m*dif)+rMult[p] )
		
	for curve in curves:
		numCV = mc.getAttr( curve+'.degree' ) + mc.getAttr( curve+'.spans' )
		for i in range(numCV):
			rx = cvMult[i] * (random.random() - .5)
			ry = cvMult[i] * (random.random() - .5)
			rz = cvMult[i] * (random.random() - .5)
			mc.move(rx, ry, rz, '%s.cv[%i]' % (curve, i), r=True)

def trimHair(curves, min, percent):
	'''
	random.randomly trim hair curves for more variation in length
	'''
	percentOfCurves = int(len(curves) * percent)
	for i in range(percentOfCurves):
		activeCurve = curves.pop(int(random.random()*len(curves)))
		r = (random.random() * (1.0 - min)) + min
		mc.delete(mc.detachCurve('%s.u[%f]' % (activeCurve, r), ch=False, cos=True, rpo=True)[0])

def createCenterCurve():
	firstLoop = mc.ls(mc.polyListComponentConversion(fe=True, fv=True, tv=True), fl=True)
	
	# DO A LITTLE ERROR CHECKING TO SEE IF WE GOT WHAT WE NEED
	neighbor = getNeighboringEdgeloops(firstLoop)
	if len(neighbor) != len(firstLoop):
		mel.eval('warning "Selected edgeloop is not a border loop. Please select a border loop and try again."')
		return None
	
	# CREATE THE HULL CURVEs
	hullCurves = makeHullCurves(firstLoop)
	
	objName = firstLoop[0].split('.')[0]
	
	# CREATE ALL THE HAIR CURVES
	for curve in hullCurves:
		s = 0
		mc.setAttr(curve+'.scale', s, s, s, type='double3')
	hairCurve = makeHairCurve(hullCurves, .5)
	
	# DO SOME SPRING CLEANING
	mc.delete(hullCurves)
	hairCurve = mc.rename(hairCurve, '%s_CenterCRV' % objName)
	
	return hairCurve

def trimFromBeginning(inputCurves, shortestLength):
	newCurves = []
	for obj in inputCurves:
		parent = mc.listRelatives(obj, parent=True)
		r = random.random()*(1-shortestLength)
		obj = mc.rebuildCurve(obj,  ch=0, rpo=1, rt=0, end=1, kr=0, kcp=1, kep=1, kt=0, s = 10, d = 3, tol = 0)[0]
		curves = mc.detachCurve( '%s.u[%f]' % (obj, r), ch=0, cos=True, rpo=1 )
		mc.delete(curves[-1])
		mc.rebuildCurve(curves[0], ch=1, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt= 0, s = 0, d = 3, tol = 0)
		curves[0] = mc.rename(curves[0], obj)
		if parent:
			curves[0] = mc.parent(curves[0], parent)[0]
		
		newCurves.append(curves[0])
	
	return newCurves

def snapBaseToScalp(curves, scalp, mult=[.7, .4, .1]):
	import cgm.lib.distance as bbDistanceLib
	
	for obj in curves:
		currentPos = mc.pointPosition(obj+'.cv[0]')
		newPos = bbDistanceLib.returnClosestPointOnMeshInfoFromPos(currentPos, scalp)['position']
		relPos = [newPos[0]-currentPos[0], newPos[1]-currentPos[1], newPos[2]-currentPos[2]]
		mc.move(newPos[0], newPos[1], newPos[2], obj+'.cv[0]', a=True)
		mc.move(relPos[0]*mult[0], relPos[1]*mult[0], relPos[2]*mult[0], obj+'.cv[1]', r=True)
		mc.move(relPos[0]*mult[1], relPos[1]*mult[1], relPos[2]*mult[1], obj+'.cv[2]', r=True)
		mc.move(relPos[0]*mult[2], relPos[1]*mult[2], relPos[2]*mult[2], obj+'.cv[3]', r=True)

def pushCVOutFromScalp(cvs, scalp, pushMult = 1.5):
	import cgm.lib.distance as bbDistanceLib
	sel = mc.ls(sl=True)
	for obj in cvs:
		currentPos = mc.pointPosition(obj)
		newPos = bbDistanceLib.returnClosestPointOnMeshInfoFromPos(currentPos, scalp)['position']
		relPos = [newPos[0]-currentPos[0], newPos[1]-currentPos[1], newPos[2]-currentPos[2]]
		mc.move(relPos[0]*pushMult, relPos[1]*pushMult, relPos[2]*pushMult, obj, r=True)		
	mc.select(sel)
	
def pushCurveOutFromScalp(curves, scalp, pushMult = 1.5):
	import cgm.lib.distance as bbDistanceLib
	sel = mc.ls(sl=True)
	
	for obj in curves:
		for shape in mc.listRelatives(obj,shapes=True,fullPath=True):
			cvList = (mc.ls([shape+'.cv[*]'],flatten=True))
		
		for cv in cvList:
			currentPos = mc.pointPosition(cv)
			newPos = bbDistanceLib.returnClosestPointOnMeshInfoFromPos(currentPos, scalp)['position']
			relPos = [newPos[0]-currentPos[0], newPos[1]-currentPos[1], newPos[2]-currentPos[2]]
			mc.move(relPos[0]*pushMult, relPos[1]*pushMult, relPos[2]*pushMult, cv, r=True)
	
	mc.select(sel)

def averageCV(amount=1.0):
	for cv in mc.ls(sl=True,fl=True):
		num = int(cv.split('.cv[')[-1].split(']')[0])
		baseObj = cv.split('.')[0]
		pos1 = mc.pointPosition('%s.cv[%i]' % (baseObj, num+1))
		pos2 = mc.pointPosition('%s.cv[%i]' % (baseObj, num-1))
		pos3 = mc.pointPosition('%s.cv[%i]' % (baseObj, num))
		average = [(pos1[0]+pos2[0]+pos3[0])/3, (pos1[1]+pos2[1]+pos3[1])/3, (pos1[2]+pos2[2]+pos3[2])/3]
		relAvg = [average[0]-pos3[0], average[1]-pos3[1], average[2]-pos3[2]]
		mc.move(relAvg[0]*amount, relAvg[1]*amount, relAvg[2]*amount, cv, r=True)
		
def createInterpolatedCurve(curve1, curve2, v):
	interpolatedCurve = mc.duplicate(curve1, rr=True, rc=True)[0]

	for shape in mc.listRelatives(curve2,shapes=True,fullPath=True):
		cvList = (mc.ls([shape+'.cv[*]'],flatten=True))
	
	mc.rebuildCurve(interpolatedCurve, ch=0, rpo=1, rt= 0, end = 1, kr = 0, kcp = 0, kep = 1, kt = 0, s = len(cvList)-3, d = 3, tol = 0)
	for i in range(len(cvList)):
		pos1 = mc.pointPosition('%s.cv[%i]' % (interpolatedCurve,i))
		pos2 = mc.pointPosition('%s.cv[%i]' % (curve2,i))
		newPos = ((pos2[0]-pos1[0])*v+pos1[0], (pos2[1]-pos1[1])*v+pos1[1], (pos2[2]-pos1[2])*v+pos1[2])    
		mc.move(newPos[0], newPos[1], newPos[2], '%s.cv[%i]' % (interpolatedCurve,i), a=True)

	return interpolatedCurve

def createRandomInterpolatedCurves(curves, numCurves):
	newCurves = []
	for i in range(numCurves):
		curve1, curve2 = random.sample(curves,2)
		newCurve = createInterpolatedCurve(curve1, curve2, random.uniform(.3, .7))
		newCurves.append(newCurve)

	return newCurves
	
'''
import hairTools.hairTools as hairTools
hairTools.trimFromBeginning(mc.ls(sl=True), .2)
hairTools.createRandomInterpolatedCurves(mc.ls(sl=True), len(mc.ls(sl=True))*3)
hairTools.snapBaseToScalp(mc.ls(sl=True), scalp)
'''