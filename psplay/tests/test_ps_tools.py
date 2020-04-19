import ps_tools
import time
import pylab as plt, numpy as np

map0_info = {"name": "split0_IQU.fits", "data_type": "IQU", "id": "split0", "cal": None}
map1_info = {"name": "split1_IQU.fits", "data_type": "IQU", "id": "split1", "cal": None}

source_mask = {"name": "source_mask.fits", "apo_type": "C1", "apo_radius": 0.3}
galactic_mask = "mask_galactic_equatorial_car_halfarcmin.fits"

patch = {"patch_type": "Rectangle", "patch_coordinate": [[-10, -20], [10, 20]]}
patch = {"patch_type": "Disk", "center": [0, 0], "radius": 10}

maps_info_list = [map0_info, map1_info]

ps_method = "master"
error_method = "master"
master_threshold = 500
compute_T_only = True
lmax = 1000

t = time.time()
spectra, spec_name_list, lb, ps_dict, cov_dict = ps_tools.compute_ps(
    patch,
    maps_info_list,
    ps_method=ps_method,
    error_method=error_method,
    beam=None,
    binning_file=None,
    bin_size=40,
    type="Dl",
    source_mask=source_mask,
    galactic_mask=galactic_mask,
    apo_radius_survey=1,
    compute_T_only=compute_T_only,
    lmax=lmax,
    master_threshold=master_threshold)

print("time: %f s" % (time.time() - t))

if ps_method == "master" or ps_method == "pseudo":

    clth = {}
    lth, clth["TT"], clth["EE"], clth["BB"], clth["TE"] = np.loadtxt(
        "bode_almost_wmap5_lmax_1e4_lensedCls_startAt2.dat", unpack=True)
    clth["ET"] = clth["TE"]
    for spec in ["EB", "BE", "BT", "TB"]:
        clth[spec] = clth["TE"] * 0

    for spec in spectra:

        if spec == "TT":
            plt.semilogy()
            plt.plot(lth[:lmax + 500], clth[spec][:lmax + 500])
        if cov_dict is not None:
            plt.errorbar(lb,
                         ps_dict["split0xsplit1"][spec],
                         np.sqrt(np.diag(cov_dict["split0xsplit1"][spec])),
                         fmt=".")
        else:
            plt.errorbar(lb, ps_dict["split0xsplit1"][spec])
            plt.show()

elif ps_method == "2dflat":
    ps_dict["split0xsplit1"].plot()
