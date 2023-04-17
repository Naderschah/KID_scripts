import time
from picamera2 import Picamera2
from specFunctions import readcal, generateGraticule

# Function definitions (most copied) 



cam = PiCamera2()

# Values to be loaded from some kind of config or auto-configured
Gain = 10.0



#settings for peak detect
savpoly = 7 #savgol filter polynomial max val 15
mindist = 50 #minumum distance between peaks max val 100
thresh = 20 #Threshold max val 100

# Final Image size
frameWidth = 800 # TODO: Double check that this only considers width seperation -- should prob be equal to pixel size
frameHeight = 600

#Go grab the computed calibration data
caldata = readcal()
wavelengthData = caldata[0]
calmsg1 = caldata[1]
calmsg2 = caldata[2]
calmsg3 = caldata[3]


### FIXME; CHeck what this is I assume this is plotting related
#generate the craticule data
graticuleData = generateGraticule(wavelengthData)
tens = (graticuleData[0])
fifties = (graticuleData[1])

def save_data(data):
    now = time.strftime("%Y%m%d--%H%M%S")
    f = open("Spectrum-"+now+'.csv','w')
	f.write('Wavelength,Intensity\r\n')
	for x in zip(data[0],data[1]):
		f.write(str(x[0])+','+str(x[1])+'\r\n')
	f.close()

# TODO: Figure out how the author applies the calibration when plotting prob best to work backwards from snapshot
# And we will probably require that the spectrum is parallel to the rows 
frame = cam.capture_array()
# Here the original author does a bunch of cropping we will see later about this
save_data(frame)

cam.start()