
The code for processing the images of the all sky cameras will be set up

Initially we will try using PyASB https://eprints.ucm.es/id/eprint/24626/ 

A tool to process all sky images to determine cloud cover sky brightness and applies photometric calibration extinction calibration etc.

This module is to be pulled into this directory so that you can use the standard commands I will give
 
running docker-compose up in this directory will start aa docker container in which you will have to install pyasb by running set up with install (and possibly build before that)

After installation the pipeline can be used, the original paper referenced a launcher however I cant find it so executing main from within docker will do the trick

While it is advertised that the module is capable of loading CR2 files this does not appear to be implemented into the code but a seperate manual processing step:

./cr2fits.py <cr2filename> <color-index>

where color index doesnt appear to make a differnce as it will extract all channels regardless


HOW DO WE SET THE CORRECT VALUES IN THE CONFIG FILE - CONTACT AUTHOR


Issues I ran into : 

- Anything reported as an issue with ImageInfo is related to the config file, so if there is a parameter missing just add None in the config as a key value pair

- tkinter - saying no $DISPLAY variable
    - We need to specify the AGG backend which can be manually done by placing 
import matplotlib

matplotlib.use('Agg')  

    before the import statements
    - We can also specify it in the config file, but as we are root user i dont know how that works


Cmd to run from (my) local machine within docker 
python pyasb/__main__.py  -i /home/KID/KID_scripts/trial_processing/6D/IMG_0917-G.fits -om /home/KID/KID_scripts/trial_processing/outputs/ -or /home/KID/KID_scripts/trial_processing/outputs/ -ocm /home/KID/KID_scripts/trial_processing/outputs/ -os /home/KID/KID_scripts/trial_processing/outputs/ -ost /home/KID/KID_scripts/trial_processing/outputs/


## Code issues (Need Fixing):


In astrometry the table gets flipped, and i dont know why
Also its done wrong so the x array gets shifted from 0-len(x) to len(x)/2-3len(x)/2
Replace line ~121 (not sure what it is in source code), content: "X = ImageInfo.resolution[0] - X" with "X=-X" 

Note that the above may also be wrong need to check if cardinal direction in final plot are correct

Rfactor may be computed wrong:
Rfactor[Rfactor>360./np.pi]=360./np.pi
But mine and original implementation work, but why





Calibration Ideas:

Lateral displacement optical axis and sensor center
halfsphere placed above fisheye with horizon and zenith marking (relative to halfsphere base)

TODO: Do we need a correction for non-perfect zenith pointing? shouldnt star alignment do that?

TODO:
ccd_bits = 16
ccd_gain = 0.5
read_noise = 8.7
thermal_noise = 0.02






## Meeting Jaime Zamorano


SQM's and TESS
- SQM Problem - spectral response shorter than TESS, drops at 600nm vs 750nm at TESS. Ie cant find R band with SQM's. Tess overall more sensitive (better for dark dark places)
- For monitoring blue : No recommendation


Cameras:
- Jake bought ACOR or something
- Sony camera - row image - strange - problem with stars - they are a peak and get cut off - may have gotten updated
- Second hand cameras -- much cheaper
- Peleng lens -- cheap fisheye



Vignetting:
- PTGui

Ask Reynier for all sky lens to try out calibration methods

Says no difference in vignetting in color bands - Doubble check 

Send email to Bjorn about optical alignment calibration -- check how focus works -- also vignetting corrction

--- Use dot for calibration, we can show something screenshot it and compare it - hopefully it willbe sufficient for infinite focus check for lens
-- Check if we can rotate lens a little to determine 
    


DOCUMENTATION PLZ
X inversion
Rfactor --- what is theta
Rfactor why replace larger htna 360/2pi with 360/2p
which commit for paper data
