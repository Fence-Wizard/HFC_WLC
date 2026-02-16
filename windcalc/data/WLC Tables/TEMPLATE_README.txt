CSV Spacing Table Format
========================

Place CSV files named by wind speed (e.g., 105mph.csv, 110mph.csv, etc.)
in this directory.

Expected CSV format:
--------------------
Row 1: Header row with height columns.
         Col A = "Group"
         Col B = "Post Label"
         Remaining cols = heights in feet (e.g., 4, 6, 8, 10, 12)

Rows 2+: One row per post size.
         Col A = PostGroup key (e.g., "IC_PIPE")
         Col B = table_label matching POST_TYPES (e.g., '2 3/8"')
         Remaining cols = max spacing (ft) for that height.
         Use "-" or empty for "not applicable."

Example (105mph.csv):
---------------------
Group,Post Label,4,6,8,10,12
IC_PIPE,1 7/8",10.0,8.0,6.5,-,-
IC_PIPE,2 3/8",12.0,10.0,8.0,6.0,-
IC_PIPE,2 7/8",14.0,12.0,10.0,8.0,6.0
IC_PIPE,3 1/2",-,14.0,12.0,10.0,8.0
IC_PIPE,4",-,-,14.0,12.0,10.0
IC_PIPE,6 5/8",-,-,-,14.0,12.0
IC_PIPE,8 5/8",-,-,-,-,14.0

When tables are present, the engine will prefer table values over
the Cf1/Cf2-based calculation for spacing limits.
