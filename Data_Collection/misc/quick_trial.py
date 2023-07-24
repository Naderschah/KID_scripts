from data_collection import *



config = Config_Handler(path=os.path.join(CODE_DIR,'config.ini'))


if config.camera['Brand'] in ["Canon", "Nikon"]: # Add the other ones if required
    ROOTLOGGER.info("Using gphoto2 as backend")
    camera = Camera_Handler_gphoto(config)
elif config.camera['Brand'] == "ZWO": 
    ROOTLOGGER.info("Using zwo asi sdk backend (not sure what asi stands for)")
    camera = Camera_Hanlder_ZWO(config)

camera.capture_image_and_download()

camera.finish()