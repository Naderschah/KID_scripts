
## This will take the pyasb module (within docker)
# and process the entire batch provided they are cr2 files

import sys, os 

# The path of the cloned and modified GIT repository
PYASB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pyasb')
OUTPUT_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),os.pardir, 'trial_out'))
IMAGE_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),os.pardir, 'trial_processing/6D/'))
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pyasb','config.cfg')
print(CONFIG_PATH)

# TODO: Add config generator - Code unreliable : Why


# Change working dir
os.chdir(PYASB_PATH)


#           Directory Mangement
if os.path.isdir(PYASB_PATH):
    pass
else:
    raise Exception('PyASB path does not exist/ is not accessible')


if os.path.isdir(OUTPUT_PATH):
    pass
else:
    print("Creating output storage directory")
    os.mkdir(OUTPUT_PATH)

if os.path.isdir(IMAGE_PATH):
    pass
else:
    raise Exception('Image Path does not exist/ is not accessible', IMAGE_PATH)


#           Create Image index
raw_image_list = os.listdir(IMAGE_PATH)
raw_image_list = [os.path.join(IMAGE_PATH, i) for i in raw_image_list if ".CR2" in i]

#           Create output direcory structure
for i in os.listdir(IMAGE_PATH):
    if ".CR2" in i:
        try:
            os.mkdir(os.path.join(OUTPUT_PATH, i.strip(".CR2")))
        except:
            pass
        try:
            os.mkdir(os.path.join(OUTPUT_PATH, i.strip(".CR2"), i.strip(".CR2")+"-R"))
        except:
            pass
        try:
            os.mkdir(os.path.join(OUTPUT_PATH, i.strip(".CR2"), i.strip(".CR2")+"-G"))
        except:
            pass
        try:
            os.mkdir(os.path.join(OUTPUT_PATH, i.strip(".CR2"), i.strip(".CR2")+"-B"))
        except:
            pass

#### TODO : Find out how to wait for cmd execution, specify config dir -Star Catalogue fucking up for some reason

#           Convert to individual band fits move to tmp
color_index = ['R','G','B']
raw_image_bands_dict = {}
for i in raw_image_list:
    print("Processing image: "+str(i))
    # Generate split fits image for each band (3bands)
    for j in range(0,3):
        print("Processing Band: "+color_index[j])
        os.system('python '+os.path.join(PYASB_PATH, 'pyasb/cr2fits.py')+' '+str(i)+' '+str(j))
        # Remove intermediate ppm file
        os.remove(i.strip('.CR2')+".ppm")
        # Define the generated filename and other required paths for execution
        file_name = i.strip('.CR2')+"-"+color_index[j]+".fits"
        pyasb_launcher = os.path.join(PYASB_PATH, 'pyasb', '__main__.py')
        # Path pointing to filename/filename-color/
        ji_output_dir = os.path.join(OUTPUT_PATH, i.split('/')[-1].strip(".CR2"),i.split('/')[-1].strip(".CR2")+'-'+color_index[j])
        # Use default naming:
        star_map_path = ji_output_dir
        photometric_table = ji_output_dir
        output_results_summary = ji_output_dir
        output_bouguerfit_graph = ji_output_dir
        output_cloudmap_image = ji_output_dir
        output_clouddata_table = ji_output_dir
        output_skybrightness_graph = ji_output_dir
        output_skybrightness_table = ji_output_dir
        # Now we do the processing TODO: Non standard config file add for each image
        os.system("python "+pyasb_launcher+" -i "+file_name+" -c "+CONFIG_PATH+" -om "+star_map_path+" -ot "+photometric_table+" -or "+output_results_summary+" -ob "+output_bouguerfit_graph+" -ocm "+output_cloudmap_image+" -oct "+output_clouddata_table+" -os "+output_skybrightness_graph+" -ost "+output_skybrightness_table)
        os.system("mv "+file_name+" "+ji_output_dir)
