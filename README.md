# polar-expander-converter
Allow the interpolation of polar file points making a more granular high definition file.
The polar file is expanded to 1 knot intervals and 1 degree wind angles.

**Note**: 
Polar files are sail boat performance polar file and is defined as the target speed for as specific wind and angle 
Target Boat Speed at (TWS/TWA)

**Run time options:**

python polarInterpolation.py -i input file or directory -o output file 

optional params: [-c converts polar to Expedition polar format]

optional params: [-r will expand to row level csv with columns TWA, TWS, BSP useful for SQL join and data analysis]

