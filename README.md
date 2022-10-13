# GeospatialProgramming
The Locations of Interest Tool Converts IP locations into Spatial features 
The input is a raw data in spreadsheet format, as formatted by the supplying financial institute
and the output is a shapefile and two .xlsx reports.
The output shapefile contains LOI field with indexed scores, and closest police station.
One .xlxs report conatins LOI with associcated addresses, if available, in the area.
The second .xlxs report contains LOI with associated account numbers and names.

Locations are buffered to account for IP address collection inaccuracies. Overlapping features are removed
based on Latitude and Longitude to represent individual locations of activity. Each location is then provided
an indexed score based on the count of activities recorded in that location and the number of accounts associated with that location.

The higher the index score the more likelihood suspicious activity has occurred at the location.
This tool works best in single projection zone and use the data provided as the required templated data.
