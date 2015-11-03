#!/bin/env python

import os
import numpy as np

import lsst.daf.persistence as dafPersist
from astroquery.vizier import Vizier
import astropy.coordinates as coord
import astropy.units as u

repo_dir = os.getenv("HOME") + "/decam_NEO_repo"

if __name__ == "__main__":

    # Make these command line arguments later
    visit = 197391
    ccdnum = 10

    b = dafPersist.Butler(repo_dir)

    src = b.get("src", visit=visit, ccdnum=ccdnum)
    diff_src = b.get("deepDiff_diaSrc", visit=visit, ccdnum=ccdnum)

    print("Sources: ", src.getCalibFlux())
    print(src.getCalibFlux().max())

    center_ra = np.degrees(np.median(src.get('coord_ra')))
    center_dec = np.degrees(np.median(src.get('coord_dec')))
    print("Field center: {:.3f}, {:.3f}".format(center_ra, center_dec))


    # I/322A = UCAC4
    columns = ['RAJ2000', 'DEJ2000', 'f.mag', 'a.mag']
    vz = Vizier(columns=columns, row_limit=2000)
    ucac_results = vz.query_region(coord.SkyCoord(ra=center_ra, dec=center_dec,
                                                    unit=(u.deg, u.deg), frame='icrs'),
                                     radius=coord.Angle(0.3, "deg"),
                                     catalog='I/322A')

    ucac_catalog = coord.SkyCoord(ra=ucac_results[0]['RAJ2000'],
                                  dec=ucac_results[0]['DEJ2000'],
                                  unit=(u.deg, u.deg), frame="icrs")
    source_catalog = coord.SkyCoord(ra=src.get('coord_ra'),
                                    dec=src.get('coord_dec'),
                                    unit=(u.rad, u.rad), frame="icrs")
    idx, d2, _ = ucac_catalog.match_to_catalog_sky(source_catalog)

    sources_x = src.get('base_SdssCentroid_x')
    sources_y = src.get('base_SdssCentroid_y')

    # Objects that are close to the edge of the chip
    ucac_edge_object = (sources_x[idx] < 50) | \
                       (sources_x[idx] > 1950) | \
                       (sources_y[idx] < 50) | \
                       (sources_y[idx] > 3950)
    print("Total UCAC obj {:d}, ok obj {:d}".format(len(ucac_edge_object),
                                                    np.sum(~ucac_edge_object)))






