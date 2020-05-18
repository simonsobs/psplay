import numpy as np

from pspy import so_map


def healpix2car(
    input_file,
    fields=None,
    mask_file=None,
    output_file=None,
    resolution=0.5,
    bounding_box=(-180, 180, -75, 30),
    lmax=6000,
):
    """ Convert HEALPIX map to CAR map
    Parameters
    ----------
    input_file: fits file
      name of the input HEALPIX fits file
    fields: tuple
      HEALPIX fields to convert i.e. (0,) will keep only temperature field
    mask_file: fits file
      name of the HEALPIX mask file
    output_file: fits file
      name of the output CAR fits file
    resolution: string
      CAR final resolution in arcminutes
    bounding_box:  tuple
      (ra0, ra1, dec0, dec1) in degree

    """
    healpix_map = so_map.read_map(input_file, fields_healpix=fields)

    # CAR Template
    ra0, ra1, dec0, dec1 = bounding_box
    res = resolution
    car_template = so_map.car_template(healpix_map.ncomp, ra0, ra1, dec0, dec1, res)
    projected_map = so_map.healpix2car(healpix_map, car_template, lmax=lmax)

    if mask_file is not None:
        mask = so_map.read_map(mask_file)
        projected_mask = so_map.healpix2car(mask, car_template, lmax=lmax)
        if mask.ncomp == healpix_map.ncomp == 1:
            projected_map.data *= np.where(projected_mask.data < 0.5, 0, 1)
        elif mask.ncomp == 1:
            for i in range(healpix_map.ncomp):
                projected_map.data[i] *= np.where(projected_mask.data < 0.5, 0, 1)
        else:
            if healpix_map.ncomp != mask.ncomp:
                raise ValueError("Map and mask have different number of components")
            for i in range(mask.ncomp):
                projected_map.data[i] *= np.where(projected_mask.data[i] < 0.5, 0, 1)

    print("Writing '{}' file".format(output_file))
    projected_map.write_map(output_file)
    return projected_map


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="A python program to convert HEALPIX map into CAR map"
    )
    parser.add_argument(
        "-i",
        "--input-file",
        help="input FITS file corresponding to HEALPIX map",
        type=str,
        required=True,
        default=None,
    )
    parser.add_argument(
        "-o",
        "--output-file",
        help="output FITS file corresponding to CAR map",
        type=str,
        required=True,
        default=None,
    )
    parser.add_argument(
        "-f",
        "--fields",
        help="tuple that enables HEALPIX fields i.e. (0,) will only keep temperature field ",
        type=tuple,
        default=None,
    )
    parser.add_argument(
        "--bounding-box",
        help="set the bounding box (ra0, dec0, ra1, dec1) all in degrees",
        type=tuple,
        default=(-180, 180, -75, 30),
    )
    parser.add_argument(
        "--resolution", help="set the resolution in arcminutes", type=float, default=0.5
    )
    parser.add_argument(
        "--mask-file",
        help="set a mask file to apply to HEALPIX map before converting",
        type=str,
        default=None,
    )
    args = parser.parse_args()

    fields = args.fields
    if fields is not None:
        fields = ([int(i) for i in args.fields],)

    healpix2car(
        input_file=args.input_file,
        fields=fields,
        mask_file=args.mask_file,
        output_file=args.output_file,
        resolution=args.resolution,
        bounding_box=args.bounding_box,
    )


# script:
if __name__ == "__main__":
    main()
