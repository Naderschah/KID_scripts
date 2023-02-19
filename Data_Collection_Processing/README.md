Here will live all the code related to data collection, file management, and data processing 



TODO:
- Do we want to process as images come in, or do we want to have daily weekly etc bulk processing

- Do we want to start the imaging task using a cronjob or the like whose execution time is updated everyday at the end of a run or do we let the code run indefinetly

- How will we transfer images from the pi to the processing machine (sftp, wired, monthly manual?)

- Will we delete images after processing or store them?

- How will the cameras be powered? DId we remember to get some sort of direct power connection for the cameras?
        We cant turn them off and on from the software - only works manual  

- How does whitebalance work in raw files : /main/imgsettings/whitebalance

Need to install
fitrst run update upgrade
gphoto
pip3 install suntime


gphoto behavior:
download/download-all : downloads to current working path 
capture-image-and-download : " and deletes from camera ---> odds are this is the preferred way of doing things