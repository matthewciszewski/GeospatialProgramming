# GeospatialProgramming
The Locations of Interest Tool Converts IP locations into Spatial features' '\n' 
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
        'This tool works best in single project zone
