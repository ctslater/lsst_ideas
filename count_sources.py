#!/bin/env/python

from __future__ import print_function, division

import numpy as np
import lsst.daf.persistence as dafPersist
import argparse
import pandas
from collections import namedtuple

#
# This loops over all of the source catalogs and image differencing catalogs in
# a repository and counts the number of entries, then saves these counts in an HDF5
# file.
#

counts_record = namedtuple("counts_record", "visitid ccdnum counts ra dec")

def count_file(source_catalog):
    count = len(source_catalog)
    ra = np.degrees(np.mean(source_catalog.get("coord_ra")))
    dec = np.degrees(np.mean(source_catalog.get("coord_dec")))
    return count, ra, dec

def count_dataset(dataset_type):

    visits = b.queryMetadata(dataset_type, "visit")

    src_records = []
    for visitid in visits:
        for visit_ccd_ref in b.subset(datasetType=dataset_type,  dataId={"visit": visitid}):
            ccdnum = visit_ccd_ref.dataId['ccdnum']
            # Sometimes the FITS file is missing, so we catch that error.
            # It would be better to test for it though.
            try:
                counts, ra, dec = count_file(visit_ccd_ref.get(dataset_type, immediate=True))
            except:
                continue
            src_records.append(counts_record(visitid=visitid, ccdnum=ccdnum, counts=counts,
                                             ra=ra, dec=dec))
    return src_records

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("repo_dir", help="Data Repository")
    parser.add_argument("output_file", help="h5 file to store results in")
    args = parser.parse_args()

    b = dafPersist.Butler(args.repo_dir)

    src_records = count_dataset("src")
    dia_records = count_dataset("deepDiff_diaSrc")

    h5_store = pandas.HDFStore(args.output_file)
    h5_store['Sources'] = pandas.DataFrame(src_records, columns=src_records[0]._fields)
    h5_store['diaSources'] = pandas.DataFrame(dia_records, columns=dia_records[0]._fields)
    h5_store.close()




