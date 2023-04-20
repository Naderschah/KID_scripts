"""
Uses captured picture/video to calibrate against solar spectrum
"""
import requests
import rawpy
import numpy as np
import scipy
import os
import cv2 as cv
from PIL import Image
import json 
import skimage
# TODO: 
# Find this file and modify
# https://git.linuxtv.org/libcamera.git/tree/src/ipa/raspberrypi/data/imx477.json#n409
# Mentioned in https://github.com/raspberrypi/picamera2/issues/457

class Calibration:
    """Class to house all calibration routines
    --> Mianly because jupyter notbook is gettng cluttered"""
    calib = {}
    def __init__(self, cal_directory) -> None:
        self.master_dir = os.path.join(cal_directory,'computed_cal_files')
        self.cal_dir = cal_directory
        if not os.path.isdir(self.master_dir):
            os.mkdir(self.master_dir)

        return
    
    def run_all_calibration(self,bias_img_dir=None, dark_img_dir=None,lens_img_dir=None,
                            flat_img_dir=None, rot=None ,crop=None,px_to_lambda=None):
        """Runs calibration with files available
        most inputs are directory paths
        rot needs to be the path to some image directory to align
        crop can be anything except None but rot needs to be given for it to be computed
        """
        #Compute master bias and dark
        if bias_img_dir!=None: 
            master_bias(bias_img_dir,self.master_dir)
            self.calib['mbias']= os.path.join(self.master_dir,'master_bias.npy')
        else:
            self.calib['mbias']=None

        if dark_img_dir!=None: 
            master_dark(dark_img_dir,self.master_dir, os.path.join(self.master_dir,'master_bias.npy'))
            self.calib['mdark']= os.path.join(self.master_dir,'master_dark.npy')
        else:
            self.calib['mdark']=None

        print('Compute lens calibration --> Code should be double checked for new calibration data')
        if lens_img_dir != None: 
            self.calib['mtx'],self.calib['dist'] = compute_lens_correction(lens_img_dir,save=False)

        if flat_img_dir != None:
            master_flat(img_dir=flat_img_dir,out_dir=self.master_dir ,mbias=self.calib['mbias'],mdark=self.calib['mdark'])
            self.calib['mflat']=os.path.join(self.master_dir,'master_flat.npy')
        else:
            self.calib['mflat']=None
        if rot != None:
            im_dat = preprocess_images(img_dir=rot)
            # If lens correction data is available apply first then compute rotation
            if 'dat' in self.calib: im_dat = correct_lens(self.calib,im_dat)
            res = find_rotation(im_dat, initial_guess =[0]).x[0]
            self.calib['Rotation'] = res
        
        if crop != None and rot!= None:
            self.calib['Crop_y'] = find_crop(self.calib['Rotation'],im_dat)
        elif rot == None and crop!=None:
            print('Not computing crop since rotation isnt computed')

        if "px_to_lambda" != None: #FIXME:
            self.calib['px_to_lambda'] =px_to_lambda

        # Ndarray cant be saved
        for key in self.calib:
            if type(self.calib[key]) == np.ndarray:
                self.calib[key] = self.calib[key].tolist()
        with open(os.path.join(self.master_dir, 'calibration.json'),'w') as f:
            f.write(json.dumps(self.calib))

        return


    def load_calibration(self, cal_path=None):
        if cal_path == None: cal_path=os.path.join(self.master_dir, 'calibration.json')
        with open(cal_path,'r') as f:
            self.calib = json.loads(f.read())
        return


    def process_image_with_calibration(self,im_path):
        '''
        Image needs to be raw ie dng or preaveraged numpy array (preprocess_image only providing im dir)
        All loaded images are of type uint16 (or rather in the scaling of uint16)
        '''
        if '.dng' in im_path:
            im = spectral_images_to_data(im_path,extra=False)
        elif '.npy' in im_path:
            im = np.load(im_path)
        else:
            raise Exception('Dont know how to load this file --> Implement method')
        if self.calib['mbias']!=None: 
            mbias = np.load(self.calib['mbias'])
            im = im - mbias
            if np.sum(im<0)>0: 
                print('{} values negative after bias for {}'.format(np.sum(im<0),im_path.split('/')[-1]))
                print('{} of which in region of interest {}'.format(np.sum(im[self.calib['Crop_y'][0]:self.calib['Crop_y'][1]]<0),im_path.split('/')[-1]))
        if self.calib['mdark']!=None : 
            mdark = np.load(self.calib['mdark'])
            im = im - mdark
            if np.sum(im<0)>0: 
                print('{} values negative after dark for {}'.format(np.sum(im<0),im_path.split('/')[-1]))
                print('{} of which in region of interest {}'.format(np.sum(im[self.calib['Crop_y'][0]:self.calib['Crop_y'][1]]<0),im_path.split('/')[-1]))
        if self.calib['mflat']!=None: 
            mflat = np.load(self.calib['mflat'])
            im = im/mflat
            if np.sum(im<0)>0: 
                print('{} values negative after flat for {}'.format(np.sum(im<0),im_path.split('/')[-1]))
                print('{} of which in region of interest {}'.format(np.sum(im[self.calib['Crop_y'][0]:self.calib['Crop_y'][1]]<0),im_path.split('/')[-1]))
        if 'dist' in self.calib: 
            lens_dir = {}
            lens_dir['mtx'] = self.calib['mtx']
            lens_dir['dist'] = self.calib['dist']
            im = correct_lens(lens_dir,im)
            if np.sum(im<0)>0: 
                print('{} values negative after lens correction for {}'.format(np.sum(im<0),im_path.split('/')[-1]))
                print('{} of which in region of interest {}'.format(np.sum(im[self.calib['Crop_y'][0]:self.calib['Crop_y'][1]]<0),im_path.split('/')[-1]))
        if 'Rotation' in self.calib: 
            im = scipy.ndimage.rotate(im,self.calib['Rotation'])
            if np.sum(im<0)>0: 
                print('{} values negative after rotation for {}'.format(np.sum(im<0),im_path.split('/')[-1]))
                print('{} of which in region of interest {}'.format(np.sum(im[self.calib['Crop_y'][0]:self.calib['Crop_y'][1]]<0),im_path.split('/')[-1]))
        if 'Crop_y' in self.calib: 
            im = im[self.calib['Crop_y'][0]:self.calib['Crop_y'][1]]
        print('Setting negatives to 0')
        im[im<0] = 0
        print('changing back to uint16')
        print('Px count above 90% exposure is {:.4}'.format(np.sum(im/2**16*100 > 85)/im.size*100))
        return im.astype(np.uint16)


    def process_spectrum(self, img, out=None):
        """Use calibration data to generate spectrum of image
        img :- image path
        """
        img = self.process_image_with_calibration(img)
        # Bin data to effective pixel size
        img = skimage.measure.block_reduce(img, block_size=(2,2,1),func=np.mean,cval=0)
        # Generate px to wavelength array
        px_wavelengths = np.polyval(self.calib['px_to_lambda'],np.linspace(0,img.shape[1]-1,img.shape[1]))
        # Generate mean value for each px for each color
        mean = np.mean(img,axis=0)
        return px_wavelengths,mean




def get_solar_spectrum():
    """If the data is not available search for it here:
    https://lweb.cfa.harvard.edu/atmosphere/ and the original paper:
    https://www.sciencedirect.com/science/article/abs/pii/S0022407310000610

    Column 1. Vacuum wavelength (nm)',
    'Column 2. Photons s-1 cm-2 nm-1',
    'Column 3. Watts m-2 nm-1',
    'Column 4. Watts m-2 cm (i.e., Watts per meter**2 per wavenumber)

    Only select columns one and two where two is multplied by wavelength
    """
    url = 'https://lweb.cfa.harvard.edu/atmosphere/links/sao2010.solref.converted'
    r = requests.get(url)
    cont = r.text
    cont = cont.split('\n')
    dat = np.zeros((len(cont),2),dtype=np.float64)
    counter=0
    rem = []
    # Extract data
    for i in cont:
        if "Column" not in i and len(i)>1:
            x,y,_,_=[j for j in i.split(' ') if len(j)>1]
            dat[counter] = [np.float64(x.strip(" ")),np.float64(y.strip(" "))]
        else: 
            rem.append(counter)
        counter += 1
    # Remove empty rows
    mask=np.ones(dat.shape[0], bool)
    mask[rem]=False
    dat= dat[mask]
    # Change unit from s-1 cm-2 nm-1 to s-1 cm-2 
    dat[::,1] = dat[::,0]*dat[::,1]
    return dat


def bin_spectrum(dat, bins):
    """
    dat -- data to be binned in form [wavelength, y]
    bins -- wavelengths
    """
    # We make the distance between wavebands symmetric
    min,max = np.diff(bins)[0], np.diff(bins)[-1]
    # Find closest to (min and max )+symm in sol data 
    min,max = np.abs(dat[0]-min-bins[0]).argmin(),np.abs(dat[0]-bins[-1]-max).argmin()

    binning = np.digitize(dat[0][min:max:], bins) # s.t.  bins[i-1] <= x < bins[i]

    # Bin the data accordingly
    return np.array([dat[1][min:max:][binning == i].sum() for i in range(0, len(bins))])


def get_baader_response(graph_path='./moon-skyglow-wavelength.csv'):
    """Generated from image using  apps.automeris.io/wpd
    output: nm, percent transmission
    """
    dat = np.loadtxt(graph_path,delimiter=', ',dtype=np.float64)
    y = dat[::,1]/100 
    x = dat[::,0]
    ## Make monotonically increasing
    #y = np.interp(np.linspace(x.min(),x.max(),4*len(dat)),x,y)
    #x = np.linspace(x.min(),x.max()-1,4*len(dat))
    return [x,y]



def spectral_images_to_data(im_path,custom_debayer=False,extra=False):
    """
    im_path : os path like object to the dng file
    custom_debayer : 2x2 sampling so one gets an effective pixel and an image with half dim as uint16
    extra : Return color array, color string and image without debayering as uint16
    """
    # Convert dngs to tiff using ImageMagick mogrify
    im = rawpy.imread(im_path)
    if extra: # This part isnt in use anymore
        color_array = im.raw_colors
        im_data = im.raw_image_visible.copy()
        # The color array includes 0,1,2,3 with 3 colors the color string makes this a bit more obvious
        color_str = "".join([chr(im.color_desc[i]) for i in im.raw_pattern.flatten()])
        # 10 bit image to 16
        im_data = (im_data/(2**10-1)*(2**16-1)).astype(np.uint16)
        return color_array,color_str, im_data
    else: 
        # TODO: Look into demosaic algorithms 
        # 11:DHT best according to https://www.libraw.org/node/2306
        if not custom_debayer:
            return im.postprocess(demosaic_algorithm=rawpy.DemosaicAlgorithm(11),half_size=False, 
                              # 3color no brightness adjustment (default is False -> ie auto brightness)
                              four_color_rgb=False,no_auto_bright=True,
                              # If using dcb demosaicing
                              dcb_iterations=0, dcb_enhance=False, 
                              # Denoising
                              fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode(0),noise_thr=None,
                              # Color
                              median_filter_passes=0,use_camera_wb=False,use_auto_wb=False, user_wb=None,
                              # sRGB output and output bits per sample : 8 is default
                              output_color=rawpy.ColorSpace(1),output_bps=16,
                              # Black levels for the sensor are predefined and cant be modified i think
                              user_flip=None, user_black=None,
                              # Adjust maximum threshholds only applied if value is nonzero default was 0.75
                              # https://www.libraw.org/docs/API-datastruct.html
                              user_sat=None, auto_bright_thr=None, adjust_maximum_thr=0, bright=1.0,
                              # Ignore default is Clip
                              highlight_mode=rawpy.HighlightMode(1), 
                              # Exp shift 1 is do nothing, None should achieve the same but to be sure, preserve 1 is full preservation
                              exp_shift=1, exp_preserve_highlights=1.0,
                              # V_out = gamma[0]*V_in^gamma 
                              gamma=(1,1), chromatic_aberration=(1,1),bad_pixels_path=None
                              )
        else:
            # Resample colors so that each px = 2x2 px
            color_str = "".join([chr(im.color_desc[i]) for i in im.raw_pattern.flatten()])
            # 10 bit image
            im = im.raw_image_visible.copy()
            print(im.max())
            w,h = im.shape
            # Reshape so that color is lowest level
            im=im.reshape(w//2,h//2,4)
            # make array with 3 color channels --> assuming greens are the same
            arr = np.zeros((w//2,h//2,3))
            colors = {'R':0,'G':1,'B':2}
            color_order = [colors[i] for i in color_str]
            for i in color_order:
                if i != 1:
                    arr[::,::,i] = im[::,::,i]
                else:
                    arr[::,::,i] += im[::,::,i]/2
            arr = (arr/(2**10-1)*(2**16-1)).astype(np.uint16)
            return arr
  





def find_rotation(img,initial_guess):
    """
    img --> np array of image
    im_bounds --> [[y_min, y_max][x_min, x_max]]
    size = img.shape[0]
    The im_bounds need to be really tight so that a very central portion of the spectrum is chosen for alignment
    This is since this minimized the std of the vertical average, so that the final std will be the actual error
    in each waveband 
    """
    # Make greyscale 
    img= np.average(img,axis=-1)
    
    return scipy.optimize.minimize(rotate_and_measure, 
                                   x0=initial_guess,args=(img),
                                   method = 'Powell')


def rotate_and_measure(rotation,img):
    """Function to be optimized to find rotation"""
    img = scipy.ndimage.rotate(img,rotation[0])
    # Downsample image
    img=skimage.measure.block_reduce(img, block_size=(2,2),func=np.mean,cval=0)
    # Take row wise difference and remove last 5 rows (spike at last row) 
    img = (img[:-1:]-img[1::])[:-5:]
    # As diffraction is wavelength dependent, and lens correction doesnt correct for this proper
    # We take the minimum (negative) - maximum to get the combinged gradient 
    return np.min(np.mean(img,axis=1)) - np.max(np.mean(img,axis=1))


def find_crop(rotation,img,greyscale=False):
    # Make greyscale
    if not greyscale: img= np.average(img,axis=-1)
    img = scipy.ndimage.rotate(img,rotation)
    # Downsample image
    img=skimage.measure.block_reduce(img, block_size=(2,2),func=np.mean,cval=0)
    # Take row wise difference and remove last 5 rows (spike at last row) 
    img = (img[:-1:]-img[1::])[:-5:]
    # Find mean 
    mean = np.mean(img,axis=1)
    # Find peaks multiply by 2 since we downsampled
    crop_y = (*np.where(mean == np.min(mean)),*np.where(mean == np.max(mean)))
    return [int(i[0]*2) for i in crop_y]



def preprocess_images(img_dir,out_img=None,master_bias=None,master_dark=None,lens_calibration=None,derot=None,crop_y=None):
    """Calibration data should only be given for debugging not for general usage  ---> use class based
    This should only be used to average images
    --------
    img_dir ---> path to image directory to be averaged
    --------
    """
    im = None
    count = 0 
    
    for i in os.listdir(img_dir):
        try:
            if im is None:
                im = spectral_images_to_data(os.path.join(img_dir,i),extra=False).astype(np.float64)
            else:
                im += spectral_images_to_data(os.path.join(img_dir,i),extra=False).astype(np.float64)
            count += 1
        except: pass
    master = im/count
    if master_bias is not None:
        if type(master_bias) != np.ndarray: master_bias = np.load(master_bias)
        master = master - master_bias
    if master_dark is not None:
        if type(master_dark) != np.ndarray: master_dark = np.load(master_dark)
        master = master - master_dark
    if lens_calibration is not None:
        master = correct_lens(lens_calibration,master)
    if derot is not None:
        # TODO: Try difference betweeen rotating individual and all together
        master = scipy.ndimage.rotate(master,2.4,reshape=False)
    if crop_y is not None:
        master = master[crop_y[0]:crop_y[1]:,::]
    if out_img!=None:
        np.save(out_img, master)
    else:
        return master

def master_bias(img_dir,out_dir):
    """Make master bias"""
    im = None
    count = 0 
    for i in os.listdir(img_dir):
        try:
            if im is None:
                im = spectral_images_to_data(os.path.join(img_dir,i),extra=False).astype(np.float64)
            else:
                im += spectral_images_to_data(os.path.join(img_dir,i),extra=False).astype(np.float64)
            count += 1
        except: pass
    master_bias = im/count
    np.save(os.path.join(out_dir,'master_bias.npy'), master_bias)

def master_dark(img_dir,out_dir, master_bias): #,master_bias='cal_images/master_bias.csv'
    """Make master dark"""
    im = None
    count = 0
    for i in os.listdir(img_dir):
        try:
            if im is None:
                im = spectral_images_to_data(os.path.join(img_dir,i),extra=False).astype(np.float64)
            else:
                im += spectral_images_to_data(os.path.join(img_dir,i),extra=False).astype(np.float64)
            count += 1
        except: pass
    if type(master_bias)!=np.ndarray : master_bias=np.load(master_bias)
    master_dark = im/count - master_bias
    np.save(os.path.join(out_dir,'master_dark.npy'), master_dark)

def master_flat(img_dir,out_dir, mbias,mdark):
    """Make master dark"""
    im = None
    count = 0
    for i in os.listdir(img_dir):
        try:
            if im is None:
                im = spectral_images_to_data(os.path.join(img_dir,i),extra=False).astype(np.float64)
            else:
                im += spectral_images_to_data(os.path.join(img_dir,i),extra=False).astype(np.float64)
            count += 1
        except: pass
    if type(mbias)!=np.ndarray and mbias!= None : master_bias=np.load(mbias).astype(np.float64)
    if type(mdark)!=np.ndarray and mdark!= None : master_dark=np.load(mdark).astype(np.float64)
    # Scale master flat between zero and 1
    for i in range(0,3):
        im[::,::,i]=im[::,::,i]/im[::,::,i].max()
    if im.min()<0.1:  print('Problem with flat images minimum value is to small')
    if np.sum(im==1)>im.size*0.01: print('Problem with flat images, to many pixels at maximum value')
    im = im.astype(np.float64)
    np.save(os.path.join(out_dir,'master_flat.npy'), im)

def get_master_cal(master_bias='cal_images/master_bias.npy', master_dark='cal_images/master_dark.npy'):
    return np.load(master_bias), np.load(master_dark)


def compute_lens_correction(img_dir,save=True):
    """
    The general code required to compute the lens correction
    This should be run in a jupyter notebook to double check the results
    of the corner fitting algorithm
    Largely taken from 
    https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html
    and a lot of stackoverflow but i closed the links
    -----
    img_dir : path to directory with images of well lit subject containing a rectilinear grid
    out_dir : Where to save intermediate files
    save : wheter or not to save the generated mtx and dist data
    Any grid might actually work check the docs of cv calibrateCamera
    """
    # Create averaged image we do this in here because we want rawpy to auto adjust brightness 
    # as the algorithm works better then 
    im = None
    count = 0 
    for i in os.listdir(img_dir):
        try:
            if im is None:
                im = rawpy.imread(os.path.join(img_dir,i)).postprocess().astype(np.float64)
            else:
                im += rawpy.imread(os.path.join(img_dir,i)).postprocess().astype(np.float64)
            count += 1
        except: pass
    lens_dist = im/count
    # switch back to standard image dtype for opencv
    lens_dist = np.array(np.round(lens_dist),dtype=np.uint8)

    #           The next bit should prob be first test run in a notebook for new data
    # Cubes width height (approx to be varied to make it work)
    # Calibration goes completely wrong if the numbers are increased (second can go to 22 but prob best not to )
    cubes=(30,20)
    # prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
    objp = np.zeros((cubes[1]*cubes[0],3), np.float32)
    objp[:,:2] = np.mgrid[0:cubes[0],0:cubes[1]].T.reshape(-1,2)
    # First we change the image to a type accepted by opencv
    lens_dist = lens_dist.astype(np.uint8)

    # Now we change to grayscale and add a blur to make detection easier
    gray = cv.cvtColor(lens_dist, cv.COLOR_BGR2GRAY)
    blur = cv.GaussianBlur(gray, (13,13), 0, 0)
    thresh = cv.adaptiveThreshold(blur, 255, 0, 1, 71, 12)
    # 31 corners per line 24 per column
    # detect corners with the goodFeaturesToTrack function.
    corners = cv.goodFeaturesToTrack(thresh, cubes[0]*cubes[1], 0.001, 65)
    corners = np.int0(corners)

    # Use the below to verify
    #for i in corners:
    #    x, y = i.ravel()
    #    cv.circle(lens_dist, (x, y), 5, 255, -1)

    # Refine the guess
    criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 100, 0.001)
    corners2 = cv.cornerSubPix(thresh,np.ascontiguousarray(corners,dtype=np.float32), (5,5), (-1,-1), criteria)
    corners2 = corners2.astype(np.int64)
    # Again plot to check 
    #for i in corners2:
    #    x, y = i.ravel()
    #    cv.circle(thresh, (x, y), 5, 255, -1)
    #plt.imshow(thresh)

    # And now we get to the last bit , we get the calibration data
    #       Arrays are odd this works --> May require some messing with the nesting
    ret, mtx, dist, rvecs, tvecs = cv.calibrateCamera([objp], [corners2.reshape((corners2.shape[0],2)).astype(np.float32)], gray.shape[::-1], None, None)
    # Dont know what ret is ->  its a sclar
    # mtx -> Camera matrix 
    # dist -> distance coefficience
    # rvecs, tvecs -> no clue 
    # dist is enough to map the lens correctly but you loose some information by using
    # mtx and dist in getOptimalNewCameraMatrix one apparently looses less information
    # TODO: Learn about the above and verify
    if save:
        with open(os.path.join(img_dir,'lens_calibration_data.json'),'w') as f:
            f.write(json.dumps({'mtx':mtx.tolist(),'dist':dist.tolist()}))
    else:
        return mtx,dist


def correct_lens(calibration,img):
    """
    calibration : os.path like or dictionary with the laoded data
    img : ndarray containing image data
    """
    if type(calibration)!=dict:
        with open(calibration,'r') as f:
            calibration=json.loads(f.read())

        for key in calibration:
            calibration[key]= np.array(calibration[key])

    h,  w = img.shape[:2]
    # This is required to keep the maximal amount of information ---> 
    # TODO: Figure out how to optimize alpha
    try:
        newcameramtx, roi = cv.getOptimalNewCameraMatrix(calibration['mtx'], calibration['dist'], (w,h), 1, (w,h))
    except: # In case one forgets to change the dtype
        for key in calibration:
            calibration[key]= np.array(calibration[key])
        newcameramtx, roi = cv.getOptimalNewCameraMatrix(calibration['mtx'], calibration['dist'], (w,h), 1, (w,h))
    dst = cv.undistort(img, calibration['mtx'], calibration['dist'], None, newcameramtx)
    return dst



def make_hdr(imdir,average = True):
    # First average all taken images (mainly for calibration)
    if average:
        # Create dictionary with paths and exp time as key
        img_dict = {}
        for i in os.listdir(imdir):
            if '_' in i: 
                e = int(i.split('_')[-2])
                if e in img_dict:
                    img_dict[e].append(os.path.join(imdir,i))
                else:
                    img_dict[e] = [os.path.join(imdir,i)]
        # If the files dont need moving
        if len(img_dict.keys()) ==0:
            for i in os.listdir(imdir):
                if os.path.isdir(os.path.join(imdir,i)) and 'hdr' not in i:
                    img_dict[int(i)] =[]


        # Save location for averaged images
        if not os.path.isdir(os.path.join(imdir,'hdr')): os.mkdir(os.path.join(imdir, 'hdr'))

        # Create average of each exposure 
        for key in img_dict:
            if not os.path.isdir(os.path.join(imdir, str(key))): os.mkdir(os.path.join(imdir, str(key)))
            # Move files
            for i in img_dict[key]:
                os.rename(str(i),os.path.join(*i.split('/')[:-1:], str(key), i.split('/')[-1]))
            # TODO; Uses deprecated
            preprocess_images(os.path.join(imdir, str(key)),out_img=os.path.join(imdir, 'hdr', str(key)+'.npy'),master_bias='/home/felix/KID_scripts/Spectroscope/cal_images/computed_cal_files/master_bias.npy')#
    
        fin = os.path.join(imdir, 'hdr')
    else: fin=imdir # TODO THis wont work either change imaging script or this, but lets see
    # Get image lsit for combining into hdr
    im_list = os.listdir(fin)
    # Convert and rescale to uint8
    img_list = [cv.convertScaleAbs(np.load(os.path.join(fin,fn)).astype(np.uint16), alpha=(255.0/65535.0)) for fn in im_list]
    
    # Debvec
    # time record in us
    exposure_times = np.array([float(i.strip('.npy'))*1e-6 for i in im_list])
    # Merge exposures to HDR image
    merge_debevec = cv.createMergeDebevec()
    hdr_debevec = merge_debevec.process(img_list, exposure_times)
    tonemap1 = cv.createTonemap(gamma=2.2)
    res_debevec = tonemap1.process(hdr_debevec)
    cv.imwrite("ldr_debvec.hdr", res_debevec)
    res_debevec_8bit = np.clip(res_debevec*255, 0, 255).astype('uint8')
    cv.imwrite("ldr_debvec.jpg", res_debevec_8bit)
    del exposure_times, merge_debevec,hdr_debevec,tonemap1,res_debevec,res_debevec_8bit
    #Robertson
    exposure_times = np.array([float(i.strip('.npy'))*1e-6 for i in im_list])
    merge_robertson = cv.createMergeRobertson()
    hdr_robertson = merge_robertson.process(img_list, exposure_times)
    # Tonemap HDR image
    tonemap2 = cv.createTonemap(gamma=1.3)
    res_robertson = tonemap2.process(hdr_robertson)
    cv.imwrite("ldr_robertson.hdr", res_robertson)
    res_robertson_8bit = np.clip(res_robertson*255, 0, 255).astype('uint8')
    cv.imwrite("ldr_robertson.jpg", res_robertson_8bit)
    del exposure_times, merge_robertson,hdr_robertson,tonemap2,res_robertson,res_robertson_8bit
    

    # Exposure fusion using Mertens
    merge_mertens = cv.createMergeMertens()
    res_mertens = merge_mertens.process(img_list)
    cv.imwrite("fusion_mertens.hdr", res_mertens)
    res_mertens_8bit = np.clip(res_mertens*255, 0, 255).astype('uint8')
    cv.imwrite("fusion_mertens.jpg", res_mertens_8bit)

    return 


def compute_rel_change(nf_data,wf_data,binning=(2,2),noprint=False):
    """Computes the relative change data
    and returns it for each color channel with std"""
    rgb = [(wf_data/nf_data)[::,::,i] for i in range(0,3)]
    if not noprint:
        print('\n{} total datapoints'.format(rel_change.size))
        print('{} faulty datapoints : {:.2}%'.format(np.sum(np.isinf(rel_change)),np.sum(np.isinf(rel_change))/rel_change.size))
        # The nan data arrises from the filter lens combination being opaque so we set it to 0 
        print('{} opaque data points : {:.2}%\n'.format(np.sum(np.isnan(rel_change)), np.sum(np.isnan(rel_change))/rel_change.size))
    for i in rgb:
        # We know that all divisions by zero will be opague to this wavelength so we can already predefine the individual wavlength acceptance range 
        i[np.isnan(i)] =0
        i[np.isinf(i)] = np.nan
    if binning is not None:
        for i in range(0,3):
            rgb[i] = skimage.measure.block_reduce(rgb[i], block_size=binning,func=np.mean,cval=0)
    # Get the mean value along each column and its standard deviation
    rgb_y = [np.nanmean(c_dat, axis=0) for c_dat in rgb]
    rgb_std = [np.nanstd(c_dat, axis=0) for c_dat in rgb]
    return rgb_y, rgb_std