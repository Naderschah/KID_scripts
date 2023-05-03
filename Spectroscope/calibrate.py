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
import matplotlib.pyplot as plt
# TODO: 
# Find this file and modify
# https://git.linuxtv.org/libcamera.git/tree/src/ipa/raspberrypi/data/imx477.json#n409
# Mentioned in https://github.com/raspberrypi/picamera2/issues/457

# TODO: Save dead pixel array as npy not json

# GLobal wheter or not to use custom debayer (find_crop and load images)
CUSTOM_DEBAYER = True

# Text colors
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Class to contain changable calibration limits (utility to not search through the file all the time)
class Cal_Limits:
    # Less than this in flat will be marked as dead px
    DEAD_PX_THRESHHOLD = 0.1

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
                            flat_img_dir=None,dead_px=None, rot=None ,crop=None,px_to_lambda=None):
        """Runs calibration with files available
        most inputs are directory paths
        dead_px needs to be set true and uses the flat images to generate the dead pixel map
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

        
        if flat_img_dir != None:
            master_flat(img_dir=flat_img_dir,out_dir=self.master_dir ,mbias=self.calib['mbias'],mdark=self.calib['mdark'])
            self.calib['mflat']=os.path.join(self.master_dir,'master_flat.npy')
        else:
            self.calib['mflat']=None

        if dead_px != None and flat_img_dir != None:
            # Nonzero returns index of where condition true --> argwhere but indexable
            self.calib['dead_px'] =np.load(self.calib['mflat']) < Cal_Limits.DEAD_PX_THRESHHOLD
            # Mask will be computed later

        print('Compute lens calibration --> Code should be double checked for new calibration data')
        if lens_img_dir != None: 
            self.calib['mtx'],self.calib['dist'] = compute_lens_correction(lens_img_dir, save=False, 
                                                                           calib=self.calib)
        if rot != None:
            if '.dng' in rot:
                im_dat = spectral_images_to_data(rot)
            elif '.npy' in rot:
                im_dat = np.load(rot)
            else:
                im_dat = preprocess_images(img_dir=rot)
            # If lens correction data is available apply first then compute rotation
            if 'dat' in self.calib: im_dat = correct_lens(self.calib,im_dat)
            res = find_rotation(im_dat, initial_guess =[0]).x[0]
            self.calib['Rotation'] = res
        
        if crop != None and rot!= None:
            # Apply rotation before finding crop
            im_dat = scipy.ndimage.rotate(im_dat,self.calib['Rotation'])
            self.calib['Crop_y'] = find_crop(self.calib['Rotation'],im_dat)
            if any(self.calib['Crop_y'])<10 : print('Crop seems wrong, double check and try with different image')
        elif rot == None and crop!=None:
            print('Not computing crop since rotation isnt computed')

        if "px_to_lambda" != None: #FIXME:
            self.calib['px_to_lambda'] =px_to_lambda

        if dead_px!=None:
            # Compute mask -- needs to be carried seperately as some processing steps cant handle nan values
            shape = np.load(self.calib['mflat']).shape
            msk = np.zeros(shape)
            msk[self.calib['dead_px']] = 1
            # Lens distort mask
            correct_lens(self.calib,msk)
            # Rotate mask
            msk = scipy.ndimage.rotate(msk,self.calib['Rotation'])
            # Crop
            msk = msk[self.calib['Crop_y'][0]:self.calib['Crop_y'][1]]
            # Make all larger 0 to 1 as those will be affected by deadpx/dust
            msk[msk>0] = 1
            np.save(os.path.join(self.master_dir,'dead_px.npy'),msk.astype(np.bool8).tolist())
            self.calib['dead_px_mask'] = os.path.join(self.master_dir,'dead_px.npy')
            self.calib['dead_px'] = self.calib['dead_px'].tolist()

        # Ndarray cant be saved
        for key in self.calib:
            if type(self.calib[key]) == np.ndarray:
                self.calib[key] = self.calib[key].tolist()
        self.save_config()

        return


    def load_calibration(self, cal_path=None):
        if cal_path == None: cal_path=os.path.join(self.master_dir, 'calibration.json')
        with open(cal_path,'r') as f:
            self.calib = json.loads(f.read())
        return


    def process_image_with_calibration(self,im_path):
        '''
        Image needs to be raw ie dng or preaveraged numpy array (preprocess_image only providing im dir)
        All loaded images are of type uint16
        Returns the calibrated image
        If dead px was set to true also returns a transformed mask array
        '''
        if '.dng' in im_path:
            im = spectral_images_to_data(im_path,extra=False)
        elif '.npy' in im_path:
            im = np.load(im_path)
        else:
            raise Exception('Dont know how to load this file --> Implement method')
        if np.sum(im<0)>0: 
                print('{} values negative in loaded image for {}'.format(np.sum(im<0),im_path.split('/')[-1]))
                print('{} of which in region of interest {}\n'.format(np.sum(im[self.calib['Crop_y'][0]:self.calib['Crop_y'][1]]<0),im_path.split('/')[-1]))
        if self.calib['mbias']!=None: 
            mbias = np.load(self.calib['mbias'])
            im = im - mbias
            if np.sum(im<0)>0: 
                print('{} values negative after bias for {}'.format(np.sum(im<0),im_path.split('/')[-1]))
                print('{} of which in region of interest {}\n'.format(np.sum(im[self.calib['Crop_y'][0]:self.calib['Crop_y'][1]]<0),im_path.split('/')[-1]))
        if self.calib['mdark']!=None : 
            mdark = np.load(self.calib['mdark'])
            im = im - mdark
            if np.sum(im<0)>0: 
                print('{} values negative after dark for {}'.format(np.sum(im<0),im_path.split('/')[-1]))
                print('{} of which in region of interest {}\n'.format(np.sum(im[self.calib['Crop_y'][0]:self.calib['Crop_y'][1]]<0),im_path.split('/')[-1]))
        
        if self.calib['mflat']!=None: 
            mflat = np.load(self.calib['mflat'])
            im = im/mflat
            if np.sum(im<0)>0: 
                print('{} values negative after flat for {}'.format(np.sum(im<0),im_path.split('/')[-1]))
                print('{} of which in region of interest {}\n'.format(np.sum(im[self.calib['Crop_y'][0]:self.calib['Crop_y'][1]]<0),im_path.split('/')[-1]))
        
        if 'dist' in self.calib: 
            lens_dir = {}
            lens_dir['mtx'] = self.calib['mtx']
            lens_dir['dist'] = self.calib['dist']
            im = correct_lens(lens_dir,im)
            if np.sum(im<0)>0: 
                print('{} values negative after lens correction for {}'.format(np.sum(im<0),im_path.split('/')[-1]))
                print('{} of which in region of interest {}\n'.format(np.sum(im[self.calib['Crop_y'][0]:self.calib['Crop_y'][1]]<0),im_path.split('/')[-1]))
        
        if 'Rotation' in self.calib: 
            im = scipy.ndimage.rotate(im,self.calib['Rotation'])
            if np.sum(im<0)>0: 
                print('{} values negative after rotation for {}'.format(np.sum(im<0),im_path.split('/')[-1]))
                print('{} of which in region of interest {}\n'.format(np.sum(im[self.calib['Crop_y'][0]:self.calib['Crop_y'][1]]<0),im_path.split('/')[-1]))
        
        if 'Crop_y' in self.calib: 
            im = im[self.calib['Crop_y'][0]:self.calib['Crop_y'][1]]
        
        print('Setting negatives to 0')
        im[im<0] = 0
        print('changing back to uint16')
        print('\nPx percentage above 90% exposure is {:.4}\n'.format(np.sum(im/np.iinfo('uint16').max*100 > 85)/im.size*100))
        # Set max value for components of image that are over exposed
        if np.sum(im[im>np.iinfo('uint16').max])>0:
            im[im>np.iinfo('uint16').max] = np.iinfo('uint16').max
            # TODO: For auto processing use the above as condition for retaking the image
            print(f"{bcolors.WARNING}Warning: Image overexposed{bcolors.ENDC}")
        return im.astype(np.uint16) 


    def process_spectrum(self, img,preproc=True, out=None, to_lambda=True):
        """Use calibration data to generate spectrum of image
        img :- image path
        """ # TODO: Docs and out
        if preproc:
            img = self.process_image_with_calibration(img)
        # Generate RGB order top level
        rgb = [(img)[::,::,i] for i in range(0,3)]
        # Get vertical mean and std
        rgb_y = [np.nanmean(c_dat, axis=0) for c_dat in rgb]
        rgb_std = [np.nanstd(c_dat, axis=0) for c_dat in rgb]

        if to_lambda:
            px_wavelengths = np.polyval(self.calib['px_to_lambda'],np.linspace(0,img.shape[1]-1,img.shape[1]))
            # Generate mean value for each px for each color
            return px_wavelengths,rgb_y,rgb_std
        else:
            return rgb_y,rgb_std
        
    def get_second_diff(self,IR_filtered_spectrum, save=False):
        """For images taken with an ir filter to identify where the second diffraction spectrum starts"""
        # Get spectrum in rgb
        IR_filtered_spectrum, std_w =self.process_spectrum(IR_filtered_spectrum, preproc=False, to_lambda=False)
        minimum = [scipy.signal.argrelextrema(i,np.less,order=100)[-1][-1] for i in IR_filtered_spectrum]
        colors = {0:'r',1:'g',2:'b'}
        fig = plt.figure(figsize=(8,8))
        axes = fig.subplots(nrows=1, ncols=1)
        axes.hlines(0,0,1400)
        axes.vlines(minimum,0,32000,color='black')
        for i in range(3):
            #plt.errorbar(x=np.linspace(0,len(rgb_no[i])-1,len(rgb_no[i])),y=rgb_no[i],yerr=std_no[i],label=colors[i]+' no Filter',color=colors[i], alpha=0.5)
            axes.errorbar(x=np.linspace(0,len(IR_filtered_spectrum[i])-1,len(IR_filtered_spectrum[i])),y=IR_filtered_spectrum[i],yerr=std_w[i],label=colors[i]+' with Filter',color=colors[i], alpha=0.5)
        axes.legend()
        if not save:
            return axes, np.mean(minimum)
        else:
            # Write new x crop upper limit --> TODO: See if the data in the upper range can still be used
            self.calib['Second_Diffraction'] = np.mean(minimum)
            self.save_config()
            return axes, np.mean(minimum)
        
    def get_one_known_line(self, processed_img, wavelength,save=False):
        """
        Computes px location of known wavelengths, should be checked before application to config
        """
        dat = processed_img
        mean = np.mean(dat[::,::,0],axis=0)
        px_loc = np.where(mean == np.max(mean))[0][0]
        if 'known_wavelength' in self.calib: self.calib['known_wavelength'][wavelength] = px_loc
        else:
            self.calib['known_wavelength'] = {wavelength:px_loc}
        if save:
            self.save_config()
        return px_loc
    
    def save_config(self):
        with open(os.path.join(self.master_dir, 'calibration.json'),'w') as f:
                f.write(json.dumps(self.calib))

def plot_rgb(img,title):
    """Makes 4 plots one of each color band"""
    colors = {0:'Red', 1:'Green',2:'Blue'}
    fig = plt.figure(figsize=(8,8))
    axes = fig.subplots(nrows=4, ncols=1)
    fig.suptitle(title)
    axes[0].imshow(cv.convertScaleAbs(img, alpha=(255.0/65535.0)))
    axes[0].set_title('RGB')
    for i in range(0,3):
        im=axes[i+1].imshow(cv.convertScaleAbs(img[::,::,i], alpha=(255.0/65535.0)))
        cbar = axes[i+1].figure.colorbar(im, ax=axes[i+1])
        cbar.ax.set_ylabel('', rotation=-90, va="bottom")
        axes[i+1].set_title(colors[i])
    return axes




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



def spectral_images_to_data(im_path,custom_debayer=CUSTOM_DEBAYER,extra=False):
    """
    Default is now to create effective pixels, if this limits resolution might be able
    to use debayering but im not sure its a good idea

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
            color_array = im.raw_colors
            im = im.raw_image_visible.copy()
            h,w = im.shape
            # create standard rgb image
            arr = np.zeros((h//2,w//2,3))
            # Assign data
            arr[::,::,0] = im[color_array==0].reshape((h//2,w//2))
            arr[::,::,1] = (im[color_array==1]/2+im[color_array==3]/2).reshape((h//2,w//2))
            arr[::,::,2] = im[color_array==2].reshape((h//2,w//2))
            # Change to uint16 scale
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


def find_crop(rotation,img,greyscale=False,custom_debayer = CUSTOM_DEBAYER):
    # Make greyscale
    if not greyscale: img= np.average(img,axis=-1)
    img = scipy.ndimage.rotate(img,rotation)
    # Downsample image
    if not custom_debayer: img=skimage.measure.block_reduce(img, block_size=(2,2),func=np.mean,cval=0)
    # Take row wise difference and remove first 5 and last 5 rows (spike there) 
    img = (img[:-1:]-img[1::])[5:-5:]
    # Find mean 
    mean = np.mean(img,axis=1)
    # Find peaks and multiply by 2 if we downsampled
    crop_y = (*np.where(mean == np.min(mean)),*np.where(mean == np.max(mean)))
    if not custom_debayer: crop_y = [int(i[0]*2) for i in crop_y]
    else: crop_y =  [int(i[0]) for i in crop_y]
    # This isnt great so shrink window a little
    return [crop_y[0]+30,crop_y[1]-30]



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
    im /= count
    if type(mbias)!=np.ndarray and mbias!= None : 
        master_bias=np.load(mbias).astype(np.float64)
        im -= master_bias
    if type(mdark)!=np.ndarray and mdark!= None : 
        master_dark=np.load(mdark).astype(np.float64)
        im -= master_dark
    # Scale master flat between zero and 1
    for i in range(0,3):
        im[::,::,i]=im[::,::,i]/im[::,::,i].max()
    if im.min()<0.1:  print('Problem with flat images minimum value is to small (or dead pixels)')
    if np.sum(im==1)>im.size*0.01: print('Problem with flat images, to many pixels at maximum value')
    im = im.astype(np.float64)
    np.save(os.path.join(out_dir,'master_flat.npy'), im)

def get_master_cal(master_bias='cal_images/master_bias.npy', master_dark='cal_images/master_dark.npy'):
    return np.load(master_bias), np.load(master_dark)


def compute_lens_correction(img_dir,save=True,calib=None):
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
    """ # TODO: Dtype scaling is wrong here fix at some point
    # Create averaged image we do this in here because we want rawpy to auto adjust brightness 
    # as the algorithm works better then 
    im = None
    count = 0 
    for i in os.listdir(img_dir):
        try:
            if im is None:
                im = spectral_images_to_data(os.path.join(img_dir,i)).astype(np.float64)
            else:
                im += spectral_images_to_data(os.path.join(img_dir,i)).astype(np.float64)
            count += 1
        except: pass
    lens_dist = im/count
    if 'mflat' in calib:
        mflat = np.load(calib['mflat'])
        lens_dist /= mflat 
    # switch back to standard image dtype for opencv
    lens_dist = cv.convertScaleAbs(lens_dist, alpha=(255.0/65535.0)).astype(np.uint8)
    del im, count

    #           The next bit should prob be first test run in a notebook for new data
    # Cubes width height (approx to be varied to make it work)
    # Calibration goes completely wrong if the numbers are increased (second can go to 22 but prob best not to )
    cubes=(19,14)
    # prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
    objp = np.zeros((cubes[1]*cubes[0],3), np.float32)
    objp[:,:2] = np.mgrid[0:cubes[0],0:cubes[1]].T.reshape(-1,2)
    # First we change the image to a type accepted by opencv
    lens_dist = lens_dist.astype(np.uint8)

    # Now we change to grayscale and add a blur to make detection easier
    gray = cv.cvtColor(lens_dist, cv.COLOR_BGR2GRAY)
    gray = cv.medianBlur(gray,11)
    blur = cv.GaussianBlur(gray, (3,3), 0, 0)
    # Perform median blur
    # Get rid of dead pixels, this requires the image to be properly exposed
    thresh = cv.adaptiveThreshold(blur, 255, 0, 1, 81, 15)
    #thresh = cv.adaptiveThreshold(blur, 255, 1, 1, 141, 16)
    # 31 corners per line 24 per column
    # detect corners with the goodFeaturesToTrack function.
    corners = cv.goodFeaturesToTrack(thresh, cubes[0]*cubes[1], 0.01, 55)
    corners = np.int0(corners)

    # Use the below to verify
    #for i in corners:
    #    x, y = i.ravel()
    #    cv.circle(lens_dist, (x, y), 5, 255, -1)
    #plt.imshow(lens_dist)
    # Refine the guess
    criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 1000, 0.001)
    corners2 = cv.cornerSubPix(thresh,np.ascontiguousarray(corners,dtype=np.float32), (15,15), (-1,-1), criteria)
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



def compute_rel_change(nf_data,wf_data,noprint=False):
    """Computes the relative change data
    and returns it for each color channel with std"""
    rgb = [(wf_data/nf_data)[::,::,i] for i in range(0,3)]
    if not noprint:
        print('\n{} total datapoints'.format(rgb.size))
        print('{} faulty datapoints : {:.2}%'.format(np.sum(np.isinf(rgb)),np.sum(np.isinf(rgb))/rgb.size))
        # The nan data arrises from the filter lens combination being opaque so we set it to 0 
        print('{} opaque data points : {:.2}%\n'.format(np.sum(np.isnan(rgb)), np.sum(np.isnan(rgb))/rgb.size))
    for i in rgb:
        # We know that all divisions by zero will be opague to this wavelength so we can already predefine the individual wavlength acceptance range 
        i[np.isnan(i)] =0
        i[np.isinf(i)] = np.nan
    # Get the mean value along each column and its standard deviation
    rgb_y = [np.nanmean(c_dat, axis=0) for c_dat in rgb]
    rgb_std = [np.nanstd(c_dat, axis=0) for c_dat in rgb]
    return rgb_y, rgb_std


def plotly_plot_img(img):
    """img : image as int dtype """
    import numpy as np
    import plotly.graph_objects as go
    import matplotlib.cm as cm

    # image dimensions (pixels)
    n1,n2,n3 = img.shape
    # Generate an image starting from a numerical function
    x, y = np.mgrid[0:n2:n2*1j,0:n1:n1*1j]
    fig = go.Figure(data=[
            go.Image(
                # Note that you can move the image around the screen
                # by setting appropriate values to x0, y0, dx, dy
                x0=x.min(),
                y0=y.min(),
                dx=(x.max() - x.min()) / n2,
                dy=(y.max() - y.min()) / n1,
                z=cv.convertScaleAbs(img, alpha=(255.0/np.iinfo(img.dtype).max))
            )
        ],
        layout={
            # set equal aspect ratio and axis labels
            "yaxis": {"scaleanchor": "x", "title": "y"},
            "xaxis": {"title": "x"}
        }
    )
    return fig