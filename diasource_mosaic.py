#!/bin/env python

from __future__ import print_function, division

import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

import lsst.daf.persistence as dafPersist


def zscale_image(input_img, contrast=0.25):
    """This emulates ds9's zscale feature. Returns the suggested minimum and
    maximum values to display."""

    samples = input_img.flatten()[::500]
    samples.sort()
    chop_size = int(0.10*len(samples))
    subset = samples[chop_size:-chop_size]

    i_midpoint = int(len(subset)/2)
    I_mid = subset[i_midpoint]

    fit = np.polyfit(np.arange(len(subset)) - i_midpoint, subset, 1)
    # fit = [ slope, intercept]

    z1 = I_mid + fit[0]/contrast * (1-i_midpoint)/1.0
    z2 = I_mid + fit[0]/contrast * (len(subset)-i_midpoint)/1.0
    return z1,z2

#
# This matches up which exposures were differenced against which templates,
# and is purely specific to this particular set of data.
#
template_catalog = {197790:  [197790, 197802, 198372, 198376, 198380, 198384],
                    197662:  [197662, 198668, 199009, 199021, 199033],
                    197408:  [197400, 197404, 197408, 197412],
                    197384:  [197384, 197388, 197392],
                    197371:  [197367, 197371, 197375, 197379]}
# Need to invert this to template_visit_catalog[exposure] = template
template_visit_catalog = {}
for templateid, visits in template_catalog.iteritems():
    for visit in visits:
        template_visit_catalog[visit] = templateid

def make_cutout(img, x, y, cutout_size=20):
    return img[(x-cutout_size/2):(x+cutout_size/2),(y-cutout_size/2):(y+cutout_size/2)]

def make_source_center(source):
    pos_x = source.get("ip_diffim_NaiveDipoleCentroid_pos_x")
    pos_y = source.get("ip_diffim_NaiveDipoleCentroid_pos_y")
    have_pos = not (np.isnan(pos_x)  or np.isnan(pos_y))

    neg_x = source.get("ip_diffim_NaiveDipoleCentroid_neg_x")
    neg_y = source.get("ip_diffim_NaiveDipoleCentroid_neg_y")
    have_neg = not (np.isnan(neg_x) or np.isnan(neg_y))

    if have_pos and have_neg:
        return (0.5*(pos_x + neg_x), 0.5*(pos_y + neg_y))
    elif not have_neg:
        return pos_x, pos_y
    else:
        return neg_x, neg_y

def group_items(items, group_length):
    for n in xrange(0, len(items), group_length):
        yield items[n:(n+group_length)]

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("repo_dir", help="Data Repository")
    parser.add_argument("visitid", type=int)
    parser.add_argument("--ccdnum", type=int, default=10)
    args = parser.parse_args()

    b = dafPersist.Butler(args.repo_dir)

    template_visit = template_visit_catalog[args.visitid]
    templateExposure = b.get("calexp", visit=template_visit, ccdnum=args.ccdnum, immediate=True)
    template_img,_,_ = templateExposure.getMaskedImage().getArrays()
    template_wcs = templateExposure.getWcs()

    sourceExposure = b.get("calexp", visit=args.visitid, ccdnum=args.ccdnum, immediate=True)
    source_img,_,_ = sourceExposure.getMaskedImage().getArrays()

    subtractedExposure = b.get("deepDiff_differenceExp", visit=args.visitid, ccdnum=args.ccdnum, immediate=True)
    subtracted_img,_,_ = subtractedExposure.getMaskedImage().getArrays()
    subtracted_wcs = subtractedExposure.getWcs()

    diaSources = b.get("deepDiff_diaSrc", visit=args.visitid, ccdnum=args.ccdnum, immediate=True)

    masked_img = subtractedExposure.getMaskedImage()
    img_arr, mask_arr, var_arr = masked_img.getArrays()
    z1, z2 = zscale_image(img_arr)

    cutout_size = 30

    for group_n, source_group in enumerate(group_items(diaSources, 21)):
        plt.figure(1).clear()
        top_level_grid = gridspec.GridSpec(7, 3)
        for source_n,source in enumerate(source_group):

            source_x, source_y = make_source_center(source)

            subgrid = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=top_level_grid[source_n], wspace=0)

            template_xycoord = template_wcs.skyToPixel(subtracted_wcs.pixelToSky(source_x, source_y))
            cutouts = [make_cutout(template_img, template_xycoord.getY(), template_xycoord.getX()),
                       make_cutout(source_img, source_y, source_x),
                       make_cutout(subtracted_img, source_y, source_x) ]

            for cutout_n, cutout in enumerate(cutouts):
                plt.subplot(subgrid[0,cutout_n])
                plt.imshow(cutout, vmin=z1, vmax=z2, cmap=plt.cm.gray)
                plt.gca().xaxis.set_ticklabels([])
                plt.gca().yaxis.set_ticklabels([])

        plt.savefig("diasource_mosaic_visit{:d}_ccd{:d}_{:d}.png".format(args.visitid, args.ccdnum, group_n))
        if group_n > 10:
            break

