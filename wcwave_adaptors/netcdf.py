"""

"""
from jinja2 import Environment, FileSystemLoader
from subprocess import Popen

import numpy as np
import netCDF4 as nc
import os
import uuid
import utm


def ncgen_from_template(template_filename, ncout_filename,
                        cdl_output_filename=None, return_nc=True,
                        clobber=False,
                        **kwargs):
    """Generate a NetCDF file from a template. If no cdl output filename is
        given, a temporary file in /tmp will be used. This is slightly
        dangerous, but the resulting template files are not too large, and we
        do try to clean up afterwards.
    """
    # assign a random temp file name for
    if not cdl_output_filename:
        cdl_output_filename = '/tmp/' + str(uuid.uuid4()) + '.cdl'

    if os.path.isfile(cdl_output_filename) and not clobber:
        raise NCOError("CDL file %s already exists and clobber is false" %
                       cdl_output_filename)

    _build_cdl(template_filename, cdl_output_filename, **kwargs)

    nc = ncgen(cdl_output_filename, ncout_filename)

    if not cdl_output_filename:
        os.remove(cdl_output_filename)

    return nc


CDL_TEMPLATE_ENV = Environment(loader=FileSystemLoader(
                               os.path.join(os.path.dirname(__file__), 'cdl')))


def _build_cdl(template_path, cdl_output_filename, **kwargs):
    """Build a CDL for use in ncgen_from_template utility in conjunction with
        ncgen wrapper.

        (**kwargs) Template arguments appropriate for the type of template.
            TODO this is not super sustainable. As models are added, we should
            likely have Classes or some other data structure to represent the
            required fields for, say, iSNOBAL input or output, or PRMS in/out
    """
    template = CDL_TEMPLATE_ENV.get_template(template_path)

    rendered = template.render(**kwargs)

    if cdl_output_filename:
        open(cdl_output_filename, 'w').write(rendered)

    return rendered


def ncgen(cdl_path, output_path, return_nc=True):
    """Wrapper for the NCO tool of the same name. See
        https://www.mankier.com/1/ncgen
    """
    p = Popen('ncgen -o %s %s' % (output_path, cdl_path), shell=True)

    retvals = p.communicate()

    if p.returncode != 0:
        raise NCOError(
            "CDL file %s could not be made into a .nc with ncgen" % cdl_path
            + "\nnco stderr: %s", retvals[1])

    elif return_nc:
        # return dataset in 'append' mode. NC4 all day ery day (default)
        return nc.Dataset(output_path, 'a')


class NCOError(Exception):
    pass


def utm2latlon(bsamp=None, bline=None, dsamp=None, dline=None,
               nsamp=None, nline=None, utm_zone=11, utm_letter='T'):
    """Create latitude and longitude variables based on the bline and bsamp
       variables given. Default UTM zone is 11T, where Dry Crrek and Reynold's
       Creek are.

       Returns:
           2 x (nline * nsamp) array of lat/lon coordinates
    """
    lines = [bline + dline*i for i in range(nline)]
    samps = [bsamp + dsamp*i for i in range(nsamp)]

    latlon_arr = [utm.to_latlon(s, l, 11, 'U') for s in samps for l in lines]

    return np.array(latlon_arr)