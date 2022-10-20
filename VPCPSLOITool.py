# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

#import tools
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsField,
                       QgsProject,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterCrs,
                       QgsAggregateCalculator,
                       QgsVectorLayer,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterString,
                       QgsVectorDataProvider,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFolderDestination,
                       QgsProcessingParameterFileDestination,
                       QgsCoordinateReferenceSystem,
                       QgsProcessingParameterFeatureSink)
from qgis import processing
from qgis.PyQt.QtCore import QVariant
from qgis.utils import iface
from qgis.core import Qgis
import os
import glob

class VPCPSLOITool(QgsProcessingAlgorithm):
    """
    The Locations of Interest Tool takes a table in spreadsheet format, as
    formatted by the supplying financial institute, and returns indexed scored,
    spatially located features including neares address and police station.
    Locations are buffered to account for IP address collection inaccuracies. 
    Overlapping features are removed based on Latitude and Longitude to
    represent indiviudal locations of activity.
    Each locations is then provided an indexed score based on the count of
    activities recorded in that location and the number of accounts associated 
    with that location.
    This tool works best in single project zones
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    #define variables set raw file path and analysis file path here
    Analysispath = "Select Analysis Directory"
    #set these files as raw data input files
    DataPoints= "Input IP Locations Locations Spreadsheet containing IP LAT and IP LON Fields"
    JurisdictionPGN = "Input Jurisdication Polygon"
    AddressLocs = "Input VicLands Address Data Features"
    VICPolAOR = "Input Victorian Police Area Of Responsibility feature class"
    CoordRefSystem = "Select the correct Project Coordinate System"
    #This is the final output file
    OutputFile = "Output Feature Class will be output one file directory above analysis directory"
    #this is the Distance input for analysis buffers
    Distance = 'Use 50 as default value'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return VPCPSLOITool()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'VPCPS LOI Tool'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('VPCPS LOI Tool')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('VPCPS LOI Tool')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'VPCPS LOI Tool'

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr('The VPCPS LOI Tool Converts IP locations into Spatial features' '\n' 
        'The input is a raw data in spreadsheet format, as formatted by the supplying financial institute,'
        'and the output is a shapefile and two xlsx reports.' '\n'
        'The shapefile contains LOI field with indexed scores, and closest police station.'
        'One xlxs conatins LOI with associcated addresses, if available, in the area and the second xlxs report contains'
        'LOI with associated account numbers and names''\n'
        'Locations are buffered to account for IP address collection inaccuracies. Overlapping features are removed'
        'based on Latitude and Longitude to represent individual locations of activity. Each locations is then provided'
        'an indexed score based on the count of activities recorded in that location'
        'and the number of accounts associated with that location.' '\n'
        'The higher the index score the more likelihood suspicious activity has occurred at the location''\n'
        'This tool works best in single project zone')

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        
        # Add the input spreadsheet features source. It should be in excel format.
        self.addParameter(QgsProcessingParameterFeatureSource(self.DataPoints,self.tr('Select IP Locations spreadsheed file containing ''IP LAT'' and ''IP LON'' fields containint the  required for analysis'),[QgsProcessing.TypeVectorAnyGeometry]))
        # Identify projected coordinate system
        self.addParameter(QgsProcessingParameterCrs(self.CoordRefSystem,self.tr('Select Projected Coordinate System format'),))
        # Add the bounding jurisdiction polygon vector features. It should be polygon geometry.
        self.addParameter(QgsProcessingParameterFeatureSource(self.JurisdictionPGN,self.tr('Select the required bounding jurisdication polygon feature required for analysis'),[QgsProcessing.TypeVector]))
        # Add the police area of responsibility zones polygon vector features. It should be polygon geometry.
        self.addParameter(QgsProcessingParameterFeatureSource(self.VICPolAOR,self.tr('Select the required Victorian Police Area of Responsibility Polygon feature required for analysis'),[QgsProcessing.TypeVector]))
        # Add the VicLands Address Data point vector features. It should be point geometry.
        self.addParameter(QgsProcessingParameterFeatureSource(self.AddressLocs,self.tr('Select the Vic Lands Address Point Data feature required for analysis'),[QgsProcessing.TypeVector]))
        # Add the source of the Distance for location buffer
        self.addParameter(QgsProcessingParameterNumber(self.Distance,self.tr('Input the distance to buffer locations for Analysis default is 50m')))
        # Add the Analysis folder location as Destination for output files
        self.addParameter(QgsProcessingParameterFolderDestination(self.Analysispath,self.tr('Select the Analysis directory for output files and to review each output'),))
        # Add the Output file name as an option as a string
        self.addParameter(QgsProcessingParameterString(self.OutputFile,self.tr('Output filename NO EXTENSION output extension will default to ".shp" format'),))



    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        source = self.parameterAsSource(parameters,self.DataPoints,context)

        # If source was not found, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSourceError method to return a standard
        # helper text for when a source cannot be evaluated
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.DataPoints))

        #define variables set raw file path and analysis file path here
        Analysispath = self.parameterAsString(parameters, self.Analysispath,context)
        PathList = Analysispath.split('\\')
        NewPath = PathList[:-1]
        ShortPath = '\\'.join(NewPath)
        #set these files as raw data input files
        DataPoints= self.parameterAsString(parameters, self.DataPoints,context)
        JurisdictionPGN = self.parameterAsString(parameters, self.JurisdictionPGN,context)
        AddressLocs = self.parameterAsString(parameters, self.AddressLocs,context)
        VICPolAOR = self.parameterAsString(parameters, self.VICPolAOR,context)
        CoordSys = self.parameterAsCrs(parameters, self.CoordRefSystem,context)
        #These are the intermediate analysis output files
        IPLocations = "IPLocations.shp"
        AddressesofInterest ="AddrInterest.shp"
        IPLocsClip = "IPLocsClip.shp"
        IPLocsWGSz55 = "IPLocsWGSz55.shp"
        JurisdictionPGNWGSz55 ="JDictionPGNWGSz55.shp"
        IPLocsBuffer = "IPLocsBuffer.shp"
        IpBuffClean = "IpBuffClean.shp"
        LocIncidents = "LocIncidents.shp"
        LocIdentities = "LocIdentities.shp"
        LOIRating = "LOIRating.shp"
        LOIOrder = "LOIOrder.shp"
        JoinAccts = "JoinAccts.shp"
        #This is the final output file
        LOIAnalysis = self.parameterAsString(parameters, self.OutputFile,context)
        #this is the Distance input for analysis buffers
        Distance = self.parameterAsInt(parameters, self.Distance,context)
        
        # Reproject JurisdictionPGN to WGS84 Zone 55
        JurisdictionPGNProject_params = {
            'INPUT': JurisdictionPGN,
            'OPERATION': '',
            'TARGET_CRS': QgsCoordinateReferenceSystem(CoordSys),
            'OUTPUT': Analysispath+'\\'+JurisdictionPGNWGSz55
            }
        JurisdictionPGN_outputs = processing.run('native:reprojectlayer', JurisdictionPGNProject_params)

        #Identify, name and Load JurisdictionPGN into map
        JurisdictionPGNLayer = iface.addVectorLayer(JurisdictionPGNProject_params['OUTPUT'],JurisdictionPGNWGSz55[:-4], "ogr")

        # Create points layer from table
        ImportPoints_params = {
            'INPUT': DataPoints,
            'MFIELD': '',
            'TARGET_CRS': QgsCoordinateReferenceSystem('EPSG:4326'),
            'XFIELD': 'IP LON',
            'YFIELD': 'IP LAT',
            'ZFIELD': '',
            'OUTPUT': Analysispath+'\\'+IPLocations
            }
        ImportPoints_outputs = processing.run('native:createpointslayerfromtable', ImportPoints_params)

        #Identify, name and Load ImportPoints into map
        ImportPointsLayer = iface.addVectorLayer(ImportPoints_params['OUTPUT'],IPLocations[:-4], "ogr")

        # Reproject IP Locations to WGS84 Zone 55
        IPLocsProject_params = {
            'INPUT': ImportPointsLayer,
            'OPERATION': '',
            'TARGET_CRS': QgsCoordinateReferenceSystem(CoordSys),
            'OUTPUT': Analysispath+'\\'+IPLocsWGSz55
            }
        IPLocsProject_outputs = processing.run('native:reprojectlayer', IPLocsProject_params)
    
        #Identify, name and Load Import Projected Points into map
        IPLocsProjectLayer = iface.addVectorLayer(IPLocsProject_params['OUTPUT'],IPLocsWGSz55[:-4], "ogr")

        # Extract by location
        ipSelection_params = {
            'INPUT': IPLocsProjectLayer,
            'INTERSECT': JurisdictionPGNLayer,
            'PREDICATE': [0],  # intersect
            'OUTPUT': Analysispath+'\\'+IPLocsClip
            }
        ipSelection_Outputs = processing.run('native:extractbylocation', ipSelection_params)

        #Identify, name and Load Extracted Points into map
        ipLocsSelectLayer = iface.addVectorLayer(ipSelection_params['OUTPUT'],IPLocsClip[:-4], "ogr")

        # Buffer the IP Locations 50m(Radius) as IP distance can be accurate to 100m
        ipBuffer_params = {
            'DISSOLVE': True,
            'DISTANCE': Distance,
            'END_CAP_STYLE': 0,  # Round
            'INPUT': ipLocsSelectLayer,
            'JOIN_STYLE': 0,  # Round
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'OUTPUT': Analysispath+'\\'+IPLocsBuffer
            }
        ipBuffer_Outputs = processing.run('native:buffer', ipBuffer_params)

        #Identify, name and Load IP Point buffers into map
        ipBufferLayer = iface.addVectorLayer(ipBuffer_params['OUTPUT'],IPLocsBuffer[:-4], "ogr")

        #Delete unecessary fields from buffers attribute table before splitting features
        ipBufferLayer.dataProvider().deleteAttributes([0])
        ipBufferLayer.dataProvider().deleteAttributes([0])
        ipBufferLayer.dataProvider().deleteAttributes([0])
        ipBufferLayer.dataProvider().deleteAttributes([0])
        ipBufferLayer.dataProvider().deleteAttributes([0])
        ipBufferLayer.dataProvider().deleteAttributes([0])
        ipBufferLayer.dataProvider().deleteAttributes([0])
        ipBufferLayer.dataProvider().deleteAttributes([0])
        ipBufferLayer.dataProvider().deleteAttributes([0])
        ipBufferLayer.dataProvider().deleteAttributes([0])
        #Create new attribute fields and update
        ipBufferLayer.dataProvider().addAttributes([QgsField("LOI",QVariant.Double,"Double",4,2),QgsField("InCd_Indx",QVariant.Double,"Double",4,2),QgsField("Id_Indx",QVariant.Double,"Double",4,2),QgsField("IndexCalc",QVariant.Double,"Double",4,2)])
        ipBufferLayer.updateFields()

        # Multipart to singleparts
        SinglePart_params = {
            'INPUT': ipBufferLayer,
            'OUTPUT': Analysispath+'\\'+IpBuffClean
        }
        ipLocations_outputs = processing.run('native:multiparttosingleparts', SinglePart_params)

        #Identify, name and Load Singular IP Location Polygons into map
        ipLocationsLayer = iface.addVectorLayer(SinglePart_params['OUTPUT'],IpBuffClean[:-4], "ogr")

        # Count points as incidents of application login at individual locations
        LocIncidents_params = {
            'CLASSFIELD': '',
            'FIELD': 'INCIDENTS',
            'POINTS': ipLocsSelectLayer,
            'POLYGONS': ipLocationsLayer,
            'WEIGHT': '',
            'OUTPUT': Analysispath+'\\'+LocIncidents
            }
        LocIncidents_Outputs = processing.run('native:countpointsinpolygon', LocIncidents_params)

        #Identify, name and Load Singular IP Location Polygons into map
        LocIncidentsLayer = iface.addVectorLayer(LocIncidents_params['OUTPUT'],LocIncidents[:-4], "ogr")

        # Count points as identities logging in at  individual locations
        LocIdentities_params = {
            'CLASSFIELD': 'CUSTOMER N',
            'FIELD': 'IDENTITIES',
            'POINTS': ipLocsSelectLayer,
            'POLYGONS': LocIncidentsLayer,
            'WEIGHT': '',
            'OUTPUT': Analysispath+'\\'+LocIdentities
            }
        LocIdentities_Outputs = processing.run('native:countpointsinpolygon', LocIdentities_params)

        #Identify, name and Load Singular IP Location Polygons into map
        LocIdentitiesLayer = iface.addVectorLayer(LocIdentities_params['OUTPUT'],LocIdentities[:-4], "ogr")

        #Identify the minimum and maximum values for the incidents that occur
        IncidentMin = LocIdentitiesLayer.aggregate(QgsAggregateCalculator.Min, 'INCIDENTS')
        IncidentMinNumber = IncidentMin[0]

        IncidentMax = LocIdentitiesLayer.aggregate(QgsAggregateCalculator.Max, 'INCIDENTS')
        IncidentMaxNumber = IncidentMax[0]

        # Calculate index value for incidents that occur at each location
        Incidents =LocIdentitiesLayer.getFeatures()
        for Incident in Incidents:
            id=Incident.id()
            IncidentIndex = ((Incident["INCIDENTS"]-IncidentMinNumber)/(IncidentMaxNumber-IncidentMinNumber))
            attrs={1:IncidentIndex}
            LocIdentitiesLayer.dataProvider().changeAttributeValues({id:attrs})

        #Identify the minimum and maximum values for the incidents that occur
        IdentityMin = LocIdentitiesLayer.aggregate(QgsAggregateCalculator.Min, 'IDENTITIES')
        IdentityMinNumber = IdentityMin[0]

        IdentityMax = LocIdentitiesLayer.aggregate(QgsAggregateCalculator.Max, 'IDENTITIES')
        IdentityMaxNumber = IdentityMax[0]

        # Calculate index value for account names that occur at a given location
        Idents =LocIdentitiesLayer.getFeatures()
        for Ident in Idents:
            id=Ident.id()
            IDIndex = ((Ident["IDENTITIES"]-IdentityMinNumber)/(IdentityMaxNumber-IdentityMinNumber))
            attrs={2:IDIndex}
            LocIdentitiesLayer.dataProvider().changeAttributeValues({id:attrs})
    
        # Calculate combined index value for each location
        Indexes =LocIdentitiesLayer.getFeatures()
        for Index in Indexes:
            id=Index.id()
            LocIndex = (((Index["InCd_Indx"]*.5)+(Index ["Id_Indx"]*0.5))*100)
            attrs={3:LocIndex}
            LocIdentitiesLayer.dataProvider().changeAttributeValues({id:attrs})
        
        # Order the features by Indexes Score
        LOIOrder_params = {
            'ASCENDING': False,
            'EXPRESSION': 'IndexCalc',
            'INPUT': LocIdentitiesLayer,
            'NULLS_FIRST': False,
            'OUTPUT': Analysispath+'\\'+LOIOrder
            }
        LOIOrder_outputs = processing.run('native:orderbyexpression', LOIOrder_params)

        #Identify, name and Load locations ordered by Index score highest to lowest
        LOIOrderLayer = iface.addVectorLayer(LOIOrder_params['OUTPUT'],LOIOrder[:-4], "ogr")

        # Adjust Index score to add 1 to start list at 1
        LOIRating_params = {
            'FIELD_LENGTH': 4,
            'FIELD_NAME': 'LOI',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,  # Integer
            'FORMULA': '@row_number+1',
            'INPUT': LOIOrderLayer,
            'OUTPUT': Analysispath+'\\'+LOIRating
            }
        LOIRating_outputs = processing.run('native:fieldcalculator', LOIRating_params)

        #Identify, name and Load locations with new ordered score column
        LOIRatingLayer = iface.addVectorLayer(LOIRating_params['OUTPUT'],LOIRating[:-4], "ogr")
    
        # Join attributes by location Locations to VicPolStns
        LOIAnalysis_params = {
            'DISCARD_NONMATCHING': False,
            'INPUT': LOIRatingLayer,
            'JOIN': VICPolAOR,
            'JOIN_FIELDS': ['VicPolSTN'],
            'METHOD': 2,  # Take attributes of the feature with largest overlap only (one-to-one)
            'PREDICATE': [0],  # intersects
            'PREFIX': '',
            'OUTPUT': ShortPath+'\\'+LOIAnalysis+".shp"
            }
        LOIAnalysis_params_Outputs = processing.run('native:joinattributesbylocation', LOIAnalysis_params)

        #Identify, name and Load locations with the closest associated VicPol STN
        LOIAnalysisLayer = iface.addVectorLayer(LOIAnalysis_params['OUTPUT'],LOIAnalysis, "ogr")

        # Join attributes by location VicPOL output to Address loocations
        AddressesofInterest_params = {
            'DISCARD_NONMATCHING': False,
            'INPUT': LOIAnalysisLayer,
            'JOIN': AddressLocs,
            'JOIN_FIELDS': ['EZI_ADD'],
            'METHOD': 0,  # Take attributes of the feature with largest overlap only (one-to-many)
            'PREDICATE': [0],  # intersects
            'PREFIX': '',
            'OUTPUT': Analysispath+'\\'+AddressesofInterest
            }
        AddressesofInterest_outputs = processing.run('native:joinattributesbylocation', AddressesofInterest_params)

        #Identify, name and Load locations final output that includes index value, addresses, closest associated VicPol STN and customer details
        AddressesofInterestLayer = iface.addVectorLayer(AddressesofInterest_params['OUTPUT'],AddressesofInterest[:-4], "ogr")

        # Delete Duplicate records on Order Number and Address 
        LOIAddress_params = {
            'FIELDS' : ['LOI','EZI_ADD'],
            'INPUT' : AddressesofInterestLayer,
            'OUTPUT' : ShortPath+'\\'+LOIAnalysis+"_Address.xlsx"
            }
        LOIAddress_outputs = processing.run('native:removeduplicatesbyattribute', LOIAddress_params)

        # Join Address locations with Customer Name and Account Numbers
        JoinAccts_params = {
            'DISCARD_NONMATCHING': False,
            'INPUT': LOIAnalysisLayer,
            'JOIN': ipLocsSelectLayer,
            'JOIN_FIELDS': ['CUSTOMER I', 'CUSTOMER N','IP ADDRESS'],
            'METHOD': 0,  # Create separate feature for each matching feature (one-to-many)
            'PREDICATE': [0],  # intersects
            'PREFIX': '',
            'OUTPUT': Analysispath+'\\'+JoinAccts
            }
        JoinAccts_outputs = processing.run('native:joinattributesbylocation', JoinAccts_params)

        #Identify, name and Load locations final output that includes index value, addresses, closest associated VicPol STN and customer details
        JoinAcctsLayer = iface.addVectorLayer(JoinAccts_params['OUTPUT'],JoinAccts[:-4], "ogr")

        # Delete Duplicate records on Order Number and Customer Details
        LOIAccounts_params = {
            'FIELDS' : ['LOI','CUSTOMER I','CUSTOMER N'],
            'INPUT' : JoinAcctsLayer,
            'OUTPUT' : ShortPath+'\\'+LOIAnalysis+"_Accounts.xlsx"
            }
        LOIAccounts_outputs = processing.run('native:removeduplicatesbyattribute', LOIAccounts_params)
        
        #Identify, name and Load locations with the closest associated VicPol STN
        QgsProject.instance().removeMapLayer(LOIAnalysisLayer.id())
        LOIAnalysisLayer = iface.addVectorLayer(LOIAnalysis_params['OUTPUT'],LOIAnalysis, "ogr")
        
        return {}
    
    def flags(self):
        return QgsProcessingAlgorithm.FlagNoThreading
        
