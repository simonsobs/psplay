import argparse
import glob
import shlex

import numpy as np
from PIL import Image

from pixell import bunch, enmap, mpi


def define_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("ifiles", nargs="+")
    parser.add_argument("-b", "--nbyte", type=int, default=4)
    parser.add_argument(
        "-q",
        "--quantum",
        type=float,
        default=1,
        help="""The quantization to use in the fixed-point representation of the image data. Higher values reduce
      image size by discarding more noise and allows higher extremes in the map, but reduces the fidelity
      of the map. 1 uK, the current default, effectively increases the noise by 0.5% in the very deepest
      parts of our maps, and by less in shallower regions. Compared to a more conservative 0.1 it results
      in 25% smaller images. The quantization level is stored in the high bit of the first 32 pixels of
      the image.""",
    )
    parser.add_argument("--suffix", type=str, default="")
    parser.add_argument("--ext", type=str, default=".png")
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument(
        "-m",
        "--mask",
        type=float,
        default=0,
        help="Treat values exactly equal to this floating point value as masked",
    )
    return parser


arg_parser = define_arg_parser()


def parse_args(args, noglob=False):
    if isinstance(args, str):
        args = shlex.split(args)
    res, unkown = arg_parser.parse_known_args(args)
    res = bunch.Bunch(**res.__dict__)
    # Glob expansion
    if not noglob:
        ifiles = []
        for pattern in res.ifiles:
            matches = glob.glob(pattern)
            if len(matches) > 0:
                ifiles += matches
            else:
                ifiles.append(pattern)
        res.ifiles = ifiles
    return res


def pack(imap, mask, nbyte=4, quantum=1.0):
    # Flip y to match PIL pixel origin in top left corner
    imap = imap[..., ::-1, :]
    mask = mask[::-1]
    # Quantize
    qmap = np.round(imap / quantum).astype(np.int64)
    # Switch from twos complement to lest significant sign and mag
    neg = qmap < 0
    qmap[neg] = -qmap[neg]
    qmap = qmap.view(np.uint64)
    qmap <<= 1
    qmap |= neg
    # Mark masked values as all ff
    qmap[mask] = 0xFFFFFFFFFFFFFFFF
    # Express as bytes and truncate to requested number of bytes
    qmap = qmap.view(np.uint8).reshape(imap.shape + (8,))[..., :nbyte]
    # Reformat as byte planes
    qmap = np.moveaxis(qmap, -1, -3)
    # Stack planes in the y direction
    qmap = qmap.reshape(qmap.shape[:-3] + (-1, qmap.shape[-1]))
    # Add metadata row
    meta = np.concatenate(
        [np.array([nbyte], np.uint8), np.array([quantum], np.float64).view(np.uint8)]
    )
    omap = np.zeros(qmap.shape[:-2] + (qmap.shape[-2] + 1, qmap.shape[-1]), np.uint8)
    omap[..., 1:, :] = qmap
    omap[..., 0, : len(meta)] = meta
    return omap


def unpack(imap):
    # Read the metadata row
    meta, qmap = imap[0], imap[1:]
    nbyte = meta[0]
    quantum = meta[1:5].view(np.float32)[0]
    # Undo plane stacking
    qmap = qmap.reshape(nbyte, -1, qmap.shape[1])
    qmap = qmap.moveaxis(0, -1)
    mask = np.all(qmap == 0xFF, -1)
    wmap = np.zeros(qmap.shape[:2], 8)
    wmap[:, :, :nbyte] = qmap
    wmap = wmap.view(np.uint64)
    # Back to twos complement
    neg = (wmap & 1) == 1
    wmap >>= 1
    wmap = wmap.view(np.int64)
    wmap[neg] = -wmap[neg]
    # And to real units
    omap = wmap * quantum
    omap[mask] = 0
    omap, mask = omap[::-1], mask[::-1]
    return omap, mask


def plot(args):
    def get_num_digits(n):
        return int(np.log10(n)) + 1

    comm = mpi.COMM_WORLD
    ifiles = sum([sorted(glob.glob(ifile)) for ifile in args.ifiles], [])

    for ind in range(comm.rank, len(ifiles), comm.size):
        ifile = ifiles[ind]
        if args.verbose > 0:
            print(ifile)
        imap = enmap.read_map(ifile)

        N = imap.shape[:-2]
        ndigits = [get_num_digits(n) for n in N]
        for i, map in enumerate(imap.preflat):
            I = np.unravel_index(i, N) if len(N) > 0 else []  # noqa
            comp = (
                "_" + "_".join(["%0*d" % (ndig, ind) for ndig, ind in zip(ndigits, I)])
                if len(N) > 0
                else ""
            )
            ofile = ifile[:-5] + args.suffix + comp + args.ext

            # Quantize it
            mask = map == args.mask
            qmap = pack(map, mask, nbyte=args.nbyte, quantum=args.quantum)
            img = Image.fromarray(qmap, mode="L")
            img.save(ofile)
