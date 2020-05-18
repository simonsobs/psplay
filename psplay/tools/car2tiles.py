import os

import numpy as np

from pixell import enplot, mpi
from pspy import so_map

from . import tile_utils_sigurd, webplot


def car2tiles(
    input_file,
    mask_file=None,
    enplot_args=None,
    output_dir=None,
    delete_fits=True,
    use_webplot=True,
    pre_operation=None,
):
    """ Convert CAR map to PNG tiles
    Parameters
    ----------
    input_file: fits file
      name of the input CAR fits file
    mask_file: fits file
      name of the CAR mask file
    enplot_args:
      list of enplot/webplot options (see corresponding programs)
    output_dir: string
      name of the output directory holding PNG files
    delete_fits: boolean
      delete the FITS files corresponding to the tiles
    use_webplot: boolean
      use webplot in place of enplot program
    """
    enplot_args = enplot_args or []

    comm = mpi.COMM_WORLD
    if comm.rank == 0:
        if output_dir is None:
            output_dir = os.path.join("tiles", input_file)
        # Check if path to fits file are already stored
        fits_files = os.path.join(output_dir, "*/*.fits")
        if fits_files not in enplot_args:
            enplot_args.append(fits_files)

        if os.path.exists(output_dir):
            os.system("rm -rf %s" % output_dir)

        if mask_file is not None:
            car = so_map.read_map(input_file)
            mask = so_map.read_map(mask_file)

            # from pixell import wcsutils
            # if not wcsutils.is_compatible(mask.geometry[0], car.geometry[0]):
            #     raise ValueError("Map and mask must have compatible geometries")

            if mask.ncomp == car.ncomp == 1:
                car.data *= np.where(mask.data < 0.5, 0, 1)
            elif mask.ncomp == 1:
                for i in range(car.ncomp):
                    car.data[i] *= np.where(mask.data < 0.5, 0, 1)
            else:
                if mask.ncomp != car.ncomp:
                    raise ValueError("Map and mask have different number of components")
                for i in range(mask.ncomp):
                    car.data[i] *= np.where(mask.data[i] < 0.5, 0, 1)
            input_file += ".tmp"
            car.write_map(input_file)

        if pre_operation is not None:
            car = so_map.read_map(input_file)
            car.data = eval(pre_operation, {"m": car.data}, np.__dict__)
            input_file += ".tmp"
            car.write_map(input_file)

    if not mpi.disabled:
        comm.barrier()

    tile_utils_sigurd.leaftile(
        input_file,
        output_dir,
        verbose="-v" in enplot_args,
        comm=comm if not mpi.disabled else None,
        monolithic=True,
    )

    if use_webplot:
        args = webplot.parse_args(enplot_args)
        webplot.plot(args)
    else:
        args = enplot.parse_args(enplot_args)
        for plot in enplot.plot_iterator(*args.ifiles, comm=comm, **args):
            enplot.write(plot.name, plot)

    if comm.rank == 0:
        if mask_file is not None or pre_operation is not None:
            os.remove(input_file)

        if delete_fits:
            for fits in args.ifiles:
                os.remove(fits)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="A python program to produce Sigurd's plots and corresponding html pages",
        epilog="Additional options will be passed to enplot/webplot program",
    )
    parser.add_argument(
        "-i",
        "--input-file",
        help="input FITS file corresponding to CAR map",
        type=str,
        required=True,
        default=None,
    )
    parser.add_argument(
        "--mask-file",
        help="set a mask file to apply to HEALPIX map before converting",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--output-dir", help="output directory holding png files", type=str, default=None
    )
    parser.add_argument(
        "--use-enplot",
        help="use enplot routine (default use webplot)",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--keep-fits-files", help="keep intermediate FITS files", action="store_true", default=False
    )
    parser.add_argument(
        "--op",
        help="pre operation on the original CAR file. For instance, 'log(abs(m))' would give you a logarithmic map",
        type=str,
        default=None,
    )
    args, enplot_args = parser.parse_known_args()

    car2tiles(
        args.input_file,
        args.mask_file,
        enplot_args,
        output_dir=args.output_dir,
        delete_fits=not args.keep_fits_files,
        use_webplot=not args.use_enplot,
        pre_operation=args.op,
    )


# script:
if __name__ == "__main__":
    main()
