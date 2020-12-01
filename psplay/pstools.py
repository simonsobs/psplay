import os
import time
from copy import deepcopy

import numpy as np
from pixell import enmap
from pspy import flat_tools, pspy_utils, so_cov, so_map, so_mcm, so_spectra, so_window, sph_tools
from scipy.ndimage.morphology import distance_transform_edt


class Timer:
    def __init__(self):
        self.t0 = None

    def start(self, prefix="Starting..."):
        self.t0 = time.time()
        print(prefix, end=" ")

    def stop(self, prefix="done"):
        print("{} in {:.2f} s".format(prefix, time.time() - self.t0))


timer = Timer()


def create_window(
    patch,
    maps_info_list,
    apo_radius_survey=1,
    res_arcmin=0.5,
    galactic_mask=None,
    source_mask=None,
    compute_T_only=False,
    use_rmax=True,
    use_kspace_filter=False,
):
    """Create a window function for a patch

    Parameters

    ----------
    patch: dict
      a dict containing the patch type and coordinates
      if patch_type is "Rectangle" the coordinates are expected to be the 4 corners
      if patch_type is "Disk" we expect the coordinates of the center and the radius in degree
    maps_info_list: list of dicts describing the data maps
      dictionnary should contain the name, the data type ("IQU" or "I") and optionally a calibration
      factor to apply to the map. Note that all map in the list should have the same data type
    apo_radius_survey: float
      the apodisation radius in degree (default: 1 degree)
    res_arcmin: float
      the angular resolution of the map in arcminutes (default: 0.5 arcminutes)
    source_mask: dict
      a dict containing an optional source mask and its properties
      the dictionnary should contain the name, the type of apodisation and the radius of apodisation
    galactic_mask: fits file
      an optional galactic mask to apply
    compute_T_only: boolean
      only use temperature field
    use_rmax: boolean
      apply apodization up to the apodization radius
    use_kspace_filter: boolean
      create a binary mask to be only used when applying kspace filter to maps
    """
    timer.start("Create window...")

    if patch["patch_type"] == "Rectangle":
        car_box = patch["patch_coordinate"]
        window = so_map.read_map(maps_info_list[0]["name"], car_box=car_box)
        if maps_info_list[0]["data_type"] == "IQU":
            window.data = window.data[0]
            window.ncomp = 1
        window.data[:] = 0
        window.data[1:-1, 1:-1] = 1
        apo_type_survey = "C1"

    elif patch["patch_type"] == "Disk":
        dec_c, ra_c = patch["center"]
        radius = patch["radius"]
        eps = 0.1
        car_box = [
            [dec_c - radius - eps, ra_c - radius - eps],
            [dec_c + radius + eps, ra_c + radius + eps],
        ]
        window = so_map.read_map(maps_info_list[0]["name"], car_box=car_box)
        if maps_info_list[0]["data_type"] == "IQU":
            window.data = window.data[0]
            window.ncomp = 1

        window.data[:] = 1
        y_c, x_c = enmap.sky2pix(
            window.data.shape, window.data.wcs, [dec_c * np.pi / 180, ra_c * np.pi / 180]
        )
        window.data[int(y_c), int(x_c)] = 0
        dist = distance_transform_edt(window.data) * res_arcmin * 1 / 60
        window.data[dist < radius] = 0
        window.data = 1 - window.data
        apo_type_survey = "C1"

    if galactic_mask is not None:
        gal_mask = so_map.read_map(galactic_mask["name"], car_box=car_box)
        window.data *= gal_mask.data
        del gal_mask

    for map_info in maps_info_list:
        split = so_map.read_map(map_info["name"], car_box=car_box)
        if compute_T_only and map_info["data_type"] == "IQU":
            split.data = split.data[0]
            split.ncomp = 1

        if split.ncomp == 1:
            window.data[split.data == 0] = 0.0

        else:
            for i in range(split.ncomp):
                window.data[split.data[i] == 0] = 0.0

    # Binary mask for kspace filter
    binary = window.copy() if use_kspace_filter else None

    window = so_window.create_apodization(
        window, apo_type=apo_type_survey, apo_radius_degree=apo_radius_survey, use_rmax=use_rmax
    )

    if source_mask is not None:
        ps_mask = so_map.read_map(source_mask["name"], car_box=car_box)
        if use_kspace_filter:
            binary.data *= ps_mask.data
        ps_mask = so_window.create_apodization(
            ps_mask, apo_type=source_mask["apo_type"], apo_radius_degree=source_mask["apo_radius"]
        )
        window.data *= ps_mask.data
        del ps_mask

    timer.stop()
    return car_box, window, binary


def compute_mode_coupling(
    window,
    type,
    lmax,
    binning_file,
    ps_method="master",
    beam_file=None,
    l_exact=None,
    l_band=None,
    l_toep=None,
    compute_T_only=False,
):
    """Compute the mode coupling corresponding the the window function

    Parameters
    ----------

    window: so_map
        the window function of the patch
    type: string
        the type of binning, either bin Cl or bin Dl
    lmax : integer
        the maximum multipole to consider for the spectra computation
    binning_file: text file
      a binning file with three columns bin low, bin high, bin mean
      note that either binning_file or bin_size should be provided
    ps_method: string
        the method for the computation of the power spectrum
        can be "master", "pseudo", or "2dflat" for now
    beam_file: text file
        file describing the beam of the map, expect bl to be the second column and start at l=0 (standard is : l,bl, ...)
    save_coupling: str
    compute_T_only: boolean
        True to compute only T spectra
    """

    if ps_method == "2dflat":
        return None

    timer.start("Compute MCM...")

    bin_lo, bin_hi, bin_c, bin_size = pspy_utils.read_binning_file(binning_file, lmax)
    n_bins = len(bin_hi)

    fsky = enmap.area(window.data.shape, window.data.wcs) / 4.0 / np.pi
    fsky *= np.mean(window.data)

    beam = None
    if beam_file is not None:
        beam_data = np.loadtxt(beam_file)
        if compute_T_only:
            beam = beam_data[:, 1]
        else:
            beam = (beam_data[:, 1], beam_data[:, 1])

    if compute_T_only:
        if ps_method == "master":
            mbb_inv, Bbl = so_mcm.mcm_and_bbl_spin0(
                window,
                binning_file,
                bl1=beam,
                lmax=lmax,
                type=type,
                niter=0,
                l_exact=l_exact,
                l_band=l_band,
                l_toep=l_toep,
            )

        elif ps_method == "pseudo":
            mbb_inv = np.identity(n_bins)
            mbb_inv *= 1 / fsky
    else:
        window = (window, window)
        if ps_method == "master":
            mbb_inv, Bbl = so_mcm.mcm_and_bbl_spin0and2(
                window,
                binning_file,
                bl1=beam,
                lmax=lmax,
                type=type,
                niter=0,
                l_exact=l_exact,
                l_band=l_band,
                l_toep=l_toep,
            )

        elif ps_method == "pseudo":
            mbb_inv = {}
            spin_list = ["spin0xspin0", "spin0xspin2", "spin2xspin0"]
            for spin in spin_list:
                mbb_inv[spin] = np.identity(n_bins)
                mbb_inv[spin] *= 1 / fsky
            mbb_inv["spin2xspin2"] = np.identity(4 * n_bins)
            mbb_inv["spin2xspin2"] *= 1 / fsky

    timer.stop()
    return mbb_inv


def get_filtered_map(map, binary, vk_mask, hk_mask, normalize=False):
    """Filter the map in Fourier space removing modes in a horizontal and vertical band
    defined by hk_mask and vk_mask. Note that we mutliply the maps by a binary mask before
    doing this operation in order to remove pathological pixels

    Parameters
    ---------
    orig_map: ``so_map``
        the map to be filtered
    binary:  ``so_map``
        a binary mask removing pathological pixels
    vk_mask: list with 2 elements
        format is fourier modes [-lx,+lx]
    hk_mask: list with 2 elements
        format is fourier modes [-ly,+ly]
    """

    if map.ncomp == 1:
        map.data *= binary.data
    else:
        map.data[:] *= binary.data

    lymap, lxmap = map.data.lmap()
    ly, lx = lymap[:, 0], lxmap[0, :]

    # filtered_map = map.copy()
    ft = enmap.fft(map.data, normalize=normalize)

    if vk_mask is not None:
        id_vk = np.where((lx > vk_mask[0]) & (lx < vk_mask[1]))
    if hk_mask is not None:
        id_hk = np.where((ly > hk_mask[0]) & (ly < hk_mask[1]))

    if map.ncomp == 1:
        if vk_mask is not None:
            ft[:, id_vk] = 0.0
        if hk_mask is not None:
            ft[id_hk, :] = 0.0

    if map.ncomp == 3:
        if vk_mask is not None:
            ft[:, :, id_vk] = 0.0
        if hk_mask is not None:
            ft[:, id_hk, :] = 0.0

    map.data[:] = np.real(enmap.ifft(ft, normalize=normalize))
    return map


def get_spectra(
    window,
    maps_info_list,
    car_box,
    type,
    lmax,
    binning_file,
    ps_method="master",
    mbb_inv=None,
    compute_T_only=False,
    vk_mask=None,
    hk_mask=None,
    transfer_function=None,
    binary=None,
):
    """Compute the power spectra in the patch

    Parameters
    ----------
    window: so_map
        the window function of the patch
    maps_info_list: list of dicts describing the data maps
      dictionnary should contain the name, the data type ("IQU" or "I") and optionally a calibration factor to apply to the map
      note that all map in the list should have the same data type
    car_box: 2x2 array
      an array of the form [[dec0,rac0],[dec1,ra1]] it encompasses the patch
      and we will only load in memory the map inside the box
    type: string
        the type of binning, either bin Cl or bin Dl
    lmax : integer
        the maximum multipole to consider for the spectra computation
    ps_method: string
      the method for the computation of the power spectrum
      can be "master", "pseudo", or "2dflat" for now
    binning_file: text file
      a binning file with three columns bin low, bin high, bin mean
      note that either binning_file or bin_size should be provided
    mbb_inv: 2d array
      the inverse mode coupling matrix, not in use for 2dflat
    compute_T_only: boolean
        True to compute only T spectra
    vk_mask: list
      the vertical band to filter out from 2D FFT (format is [-lx, +lx])
    hk_mask: list
      the horizontal band to filter out from 2D FFT (format is [-ly, +ly])
    transfer_function: str
      the path to the transfer function
    binary: so_map
      the binary mask to be used in the kspace filter process
    """

    ht_list = []
    name_list = []

    if not compute_T_only:
        window = (window, window)

    for map_info in maps_info_list:

        split = so_map.read_map(map_info["name"], car_box=car_box)

        if compute_T_only and map_info["data_type"] == "IQU":
            split.data = split.data[0]
            split.ncomp = 1

        if map_info["cal"] is not None:
            split.data *= map_info["cal"]

        use_kspace_filter = vk_mask is not None or hk_mask is not None
        if use_kspace_filter:
            timer.start("Filter {} in the patch...".format(os.path.basename(map_info["name"])))
            split = get_filtered_map(split, binary, vk_mask, hk_mask)
            timer.stop()

        if ps_method in ["master", "pseudo"]:
            timer.start("SPHT of {} in the patch...".format(os.path.basename(map_info["name"])))
            alms = sph_tools.get_alms(split, window, niter=0, lmax=lmax + 50)
            if use_kspace_filter:
                alms /= np.product(split.data.shape[-2:])
            ht_list += [alms]
            timer.stop()

        elif ps_method == "2dflat":
            timer.start("FFT of {} in the patch...".format(os.path.basename(map_info["name"])))
            ffts = flat_tools.get_ffts(split, window, lmax)
            ht_list += [ffts]
            timer.stop()

        name_list += [map_info["id"]]

    split_num = np.arange(len(maps_info_list))

    if compute_T_only:
        if ps_method in ["master", "pseudo"]:
            spectra = None
        elif ps_method == "2dflat":
            spectra = ["II"]
    else:
        if ps_method in ["master", "pseudo"]:
            spectra = ["TT", "TE", "TB", "ET", "BT", "EE", "EB", "BE", "BB"]
        elif ps_method == "2dflat":
            spectra = ["II", "IQ", "IU", "QI", "QQ", "QU", "UI", "UQ", "UU"]

    ps_dict = {}
    spec_name_list = []

    for name1, ht1, c1 in zip(name_list, ht_list, split_num):
        for name2, ht2, c2 in zip(name_list, ht_list, split_num):
            if c1 > c2:
                continue

            spec_name = "%sx%s" % (name1, name2)

            if ps_method in ["master", "pseudo"]:
                l, ps = so_spectra.get_spectra(ht1, ht2, spectra=spectra)
                ells, ps_dict[spec_name] = so_spectra.bin_spectra(
                    l, ps, binning_file, lmax, type=type, mbb_inv=mbb_inv, spectra=spectra
                )
                if use_kspace_filter:
                    _, _, tf, _ = np.loadtxt(transfer_function, unpack=True)
                    if compute_T_only:
                        ps_dict[spec_name] /= tf[np.where(ells < lmax)]
                    else:
                        for spec in spectra:
                            ps_dict[spec_name][spec] /= tf[np.where(ells < lmax)]

            elif ps_method == "2dflat":
                ells, ps_dict[spec_name] = flat_tools.power_from_fft(ht1, ht2, type=type)

            spec_name_list += [spec_name]

    if compute_T_only:
        # to make TT only behave the same as the other cases, make it a dictionnary
        if ps_method in ["master", "pseudo"]:
            spectra = ["TT"]
            for spec_name in spec_name_list:
                ps_dict[spec_name] = {"TT": ps_dict[spec_name]}

    return spectra, spec_name_list, ells, ps_dict


def get_covariance(
    window,
    lmax,
    spec_name_list,
    ps_dict,
    binning_file,
    error_method="master",
    spectra=None,
    l_exact=None,
    l_band=None,
    l_toep=None,
    mbb_inv=None,
    compute_T_only=False,
    transfer_function=None,
):
    """Compute the covariance matrix of the power spectrum in the patch

     Parameters
     ----------

     window: so_map
       the window function of the patch
     lmax: integer
       the maximum multipole to consider for the spectra computation
     spec_name_list:  list
       the list of  power spectra
       For example : [split0xsplit0,split0xsplit1,split1xsplit1]
       note that for computing the error on PS(split0xsplit1) we need PS(split0xsplit0), PS(split0xsplit1), PS(split1xsplit1)
     ps_dict: dict
       a dict containing all power spectra
     binning_file: text file
       a binning file with three columns bin low, bin high, bin mean
       note that either binning_file or bin_size should be provided
     error_method: string
       the method for the computation of error
       can be "master" or "knox" for now
    approx_coupling: dict
    mbb_inv: 2d array
      the inverse mode coupling matrix, not in use for 2dflat
    compute_T_only: boolean
      True to compute only T spectra
    transfer_function: str
      the path to the transfer function
    """
    timer.start("Compute {} error...".format(error_method))

    bin_lo, bin_hi, bin_c, bin_size = pspy_utils.read_binning_file(binning_file, lmax)

    fsky = enmap.area(window.data.shape, window.data.wcs) / 4.0 / np.pi
    fsky *= np.mean(window.data)

    cov_dict = {}

    if error_method == "knox":
        for name in spec_name_list:
            m1, m2 = name.split("x")
            cov_dict[name] = {}
            for spec in spectra:
                X, Y = spec
                prefac = 1 / ((2 * bin_c + 1) * fsky * bin_size)
                # fmt: off
                cov_dict[name][X + Y] = np.diag(prefac * (
                    ps_dict["%sx%s" % (m1, m1)][X + X] * ps_dict["%sx%s" % (m2, m2)][Y + Y]
                    + ps_dict["%sx%s" % (m1, m2)][X + Y] ** 2
                ))
                # fmt: on

    elif error_method == "master":

        if not compute_T_only:
            mbb_inv = mbb_inv["spin0xspin0"]

        coupling_dict = so_cov.cov_coupling_spin0(
            window, lmax, niter=0, l_band=l_band, l_toep=l_toep, l_exact=l_exact
        )
        coupling = so_cov.bin_mat(coupling_dict["TaTcTbTd"], binning_file, lmax)

        for name in spec_name_list:
            m1, m2 = name.split("x")
            cov_dict[name] = {}
            for spec in spectra:
                X, Y = spec
                cov_dict[name][X + Y] = so_cov.symmetrize(
                    ps_dict["%sx%s" % (m1, m1)][X + X]
                ) * so_cov.symmetrize(ps_dict["%sx%s" % (m2, m2)][Y + Y])
                cov_dict[name][X + Y] += so_cov.symmetrize(ps_dict["%sx%s" % (m1, m2)][X + Y] ** 2)
                cov_dict[name][X + Y] *= coupling
                cov_dict[name][X + Y] = np.dot(np.dot(mbb_inv, cov_dict[name][X + Y]), mbb_inv.T)
                if transfer_function is not None:
                    _, _, tf, _ = np.loadtxt(transfer_function, unpack=True)
                    tf = tf[: len(bin_c)]
                    cov_dict[name][X + Y] /= np.outer(np.sqrt(tf), np.sqrt(tf))

    else:
        cov_dict = None

    timer.stop()
    return cov_dict


def theory_for_covariance(
    ps_dict, spec_name_list, spectra, lmax, beam_file=None, binning_file=None, force_positive=True
):

    ps_dict_for_cov = deepcopy(ps_dict)
    if force_positive:
        for name in spec_name_list:
            m1, m2 = name.split("x")
            for spec in spectra:
                X, Y = spec
                ps_dict_for_cov["%sx%s" % (m1, m1)][X + X] = np.abs(
                    ps_dict_for_cov["%sx%s" % (m1, m1)][X + X]
                )
                ps_dict_for_cov["%sx%s" % (m1, m1)][Y + Y] = np.abs(
                    ps_dict_for_cov["%sx%s" % (m2, m2)][Y + Y]
                )

    if beam_file is not None:
        beam_data = np.loadtxt(beam_file)
        l, bl = beam_data[:, 0], beam_data[:, 1]
        lb, bb = pspy_utils.naive_binning(l, bl, binning_file, lmax)
        for name in spec_name_list:
            for spec in spectra:
                ps_dict_for_cov[name][spec] *= bb ** 2

    return ps_dict_for_cov


def compute_ps(
    patch,
    maps_info_list,
    ps_method="master",
    error_method="master",
    type="Dl",
    binning_file=None,
    bin_size=None,
    beam_file=None,
    galactic_mask=None,
    source_mask=None,
    apo_radius_survey=1,
    compute_T_only=False,
    lmax=1000,
    l_exact=None,
    l_band=None,
    l_toep=None,
    vk_mask=None,
    hk_mask=None,
    transfer_function=None,
):
    """Compute spectra

    Parameters
    ----------
    patch: dict
      a dict containing the patch type and coordinates
      if patch_type is "Rectangle" the coordinate are expected to be the 4 corners
      if patch_type is "Disk" we expect the coordinate of the center and the radius in degree
    maps_info_list: list of dicts describing the data maps
      dictionnary should contain the name, the data type ("IQU" or "I") and optionally a calibration factor to apply to the map
      note that all map in the list should have the same data type
    beam_file: text file
      file describing the beam of the map, expect l,bl
    binning_file: text file
      a binning file with three columns bin low, bin high, bin mean
      note that either binning_file or bin_size should be provided
    bin_size: integer
      the bin size
      note that either binning_file or bin_size should be provided
    type: string
      the type of binning, either bin Cl or bin Dl
    source_mask: dict
      a dict containing an optional source mask and its properties
      the dictionnary should contain the name, the type of apodisation and the radius of apodisation
    galactic_mask: fits file
      an optional galactic mask to apply
    apo_radius_survey: float
      the apodisation radius in degree
    ps_method: string
      the method for the computation of the power spectrum
      can be "master", "pseudo", or "2dflat" for now
    error_method: string
      the method for the computation of error
      can be "master" or "knox" for now
    compute_T_only: boolean
      True to compute only T spectra, should always be true for data_type= "I"
    lmax: integer
      the maximum multipole to consider for the spectra computation
    vk_mask: list
      the vertical band to filter out from 2D FFT (format is [-lx, +lx])
    hk_mask: list
      the horizontal band to filter out from 2D FFT (format is [-ly, +ly])
    transfer_function: str
      the path to the transfer function
    """

    # Check computation mode
    for map_info in maps_info_list:
        if not compute_T_only and map_info["data_type"] == "I":
            raise ValueError(
                "Only temperature computation can be done given data type! Check your configuration."
            )

    # Check file path
    if binning_file is not None:
        if not os.path.exists(binning_file):
            raise ValueError("No binning file at '{}'".format(binning_file))
    if beam_file is not None:
        if not os.path.exists(beam_file):
            raise ValueError("No beam file at '{}'".format(beam_file))

    if binning_file is None and ps_method != "2dflat":
        if bin_size is None:
            raise ValueError("Missing binning size!")
        pspy_utils.create_binning_file(bin_size=bin_size, n_bins=1000, file_name="binning.dat")
        binning_file = "binning.dat"

    use_kspace_filter = False
    if vk_mask is not None or hk_mask is not None:
        if transfer_function is None:
            raise ValueError("Missing transfer function to correct for kpsace filter")
        use_kspace_filter = True

    car_box, window, binary = create_window(
        patch,
        maps_info_list,
        apo_radius_survey,
        galactic_mask=galactic_mask,
        source_mask=source_mask,
        compute_T_only=compute_T_only,
        use_kspace_filter=use_kspace_filter,
    )

    mbb_inv = compute_mode_coupling(
        window,
        type,
        lmax,
        binning_file,
        ps_method=ps_method,
        beam_file=beam_file,
        l_exact=l_exact,
        l_band=l_band,
        l_toep=l_toep,
        compute_T_only=compute_T_only,
    )

    spectra, spec_name_list, ells, ps_dict = get_spectra(
        window,
        maps_info_list,
        car_box,
        type,
        lmax,
        binning_file,
        ps_method=ps_method,
        mbb_inv=mbb_inv,
        compute_T_only=compute_T_only,
        vk_mask=vk_mask,
        hk_mask=hk_mask,
        transfer_function=transfer_function,
        binary=binary,
    )

    if ps_method == "2dflat" or error_method is None:
        return spectra, spec_name_list, ells, ps_dict, None

    ps_dict_for_cov = theory_for_covariance(
        ps_dict, spec_name_list, spectra, lmax, beam_file=beam_file, binning_file=binning_file
    )

    cov_dict = get_covariance(
        window,
        lmax,
        spec_name_list,
        ps_dict_for_cov,
        binning_file,
        error_method=error_method,
        l_exact=l_exact,
        l_band=l_band,
        l_toep=l_toep,
        spectra=spectra,
        mbb_inv=mbb_inv,
        compute_T_only=compute_T_only,
        transfer_function=transfer_function,
    )

    return spectra, spec_name_list, ells, ps_dict, cov_dict
