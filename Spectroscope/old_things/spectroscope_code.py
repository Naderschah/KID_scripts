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