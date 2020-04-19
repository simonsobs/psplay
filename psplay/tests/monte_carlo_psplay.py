import psplay
import time
import pylab as plt, numpy as np
from pspy import so_map, pspy_utils

# Sim parameters
clfile = "bode_almost_wmap5_lmax_1e4_lensedCls_startAt2.dat"
n_sims = 100
template_car = so_map.car_template(3, -10, 10, -10, 10, 0.5)
rms_uKarcmin_T = 8
map0_info = {"name":"split0_IQU.fits", "data_type":"IQU", "id":"split0", "cal" : None}
map1_info = {"name":"split1_IQU.fits", "data_type":"IQU", "id":"split1", "cal" : None}
maps_info_list = [map0_info, map1_info]

# Patch parameter
source_mask = {"name":"source_mask.fits", "apo_type":"C1" , "apo_radius": 0.3}
galactic_mask = "mask_galactic_equatorial_car_halfarcmin.fits"
patch = {"patch_type": "Disk", "center": [0,0], "radius": 8}
apo_radius_survey = 1

# Spectra parameters
ps_method = "master"
error_method = "master"
bin_size = 40
compute_T_only = False
lmax = 2000
type = "Dl"
master_threshold = None
lmax_pad = None
beam = None # Not ready yet


pspy_utils.create_binning_file(bin_size=bin_size, n_bins=1000, file_name="binning.dat")
binning_file = "binning.dat"


all_dict = []
for iii in range(n_sims):
    t = time.time()
    
    cmb = template_car.synfast(clfile)
    
    for i, info in enumerate(maps_info_list):
        split = cmb.copy()
        noise = so_map.white_noise(split, rms_uKarcmin_T=rms_uKarcmin_T)
        split.data += noise.data
        split.write_map(info["name"])

    del cmb
    del split
    del noise
    
    if iii == 0:
        car_box, window = psplay.create_window(patch,
                                               maps_info_list,
                                               apo_radius_survey,
                                               galactic_mask=galactic_mask,
                                               source_mask=source_mask,
                                               compute_T_only=compute_T_only)
                                
        mbb_inv = psplay.compute_mode_coupling(window,
                                               type,
                                               lmax,
                                               binning_file,
                                               ps_method=ps_method,
                                               beam=beam,
                                               lmax_pad=lmax_pad,
                                               master_threshold=master_threshold,
                                               compute_T_only=compute_T_only)
                          
                          
    spectra, spec_name_list, ells, ps_dict = psplay.get_spectra(window,
                                                                maps_info_list,
                                                                car_box,
                                                                type,
                                                                lmax,
                                                                binning_file,
                                                                ps_method=ps_method,
                                                                mbb_inv=mbb_inv,
                                                                compute_T_only=compute_T_only)

    
    if iii == 0:
        if ps_method == "master" or ps_method == "pseudo":
            if error_method is not None:
                cov_dict = psplay.get_covariance(window,
                                                 lmax,
                                                 spec_name_list,
                                                 ps_dict,
                                                 binning_file,
                                                 error_method=error_method,
                                                 master_threshold=master_threshold,
                                                 spectra=spectra,
                                                 mbb_inv=mbb_inv,
                                                 compute_T_only=compute_T_only)

    
    
        all_dict = {spec: [] for spec in spectra}
    
    if ps_method == "2dflat":
        for spec in spectra:
            all_dict[spec] += [ps_dict["split0xsplit1"].powermap[spec]]
    else:
        for spec in spectra:
            all_dict[spec] += [ps_dict["split0xsplit1"][spec]]
        
    print ("sim %03d done in : %0.2f s"  % (iii,time.time()-t))



if ps_method is not "2dflat":

    clth = {}
    lth, clth["TT"], clth["EE"], clth["BB"], clth["TE"] = np.loadtxt(clfile, unpack=True)
    clth["ET"] = clth["TE"]
    for spec in ["EB", "BE", "BT", "TB"]:
        clth[spec] = clth["TE"]*0

    for spec in spectra:
        mean = np.mean(all_dict[spec], axis=0)
        std = np.std(all_dict[spec], axis=0)
        plt.plot(lth[:lmax+50], clth[spec][:lmax+50])
        plt.errorbar(ells, mean, std, fmt= ".")
        plt.show()
        
        if error_method is not None:
            plt.semilogy()
            plt.errorbar(ells, std, fmt= ".")
            plt.plot(ells, np.sqrt(np.diag(cov_dict["split0xsplit1"][spec])))
            plt.show()
else:

    for spec in spectra:
        ps_dict["split0xsplit1"].powermap[spec] = np.mean(all_dict[spec], axis=0)
    ps_dict["split0xsplit1"].plot()
