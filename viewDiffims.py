#!/bin/env python

from __future__ import print_function

#import math
#import numpy

import lsst.pex.config as pexConfig
import lsst.pipe.base as pipeBase
import lsst.afw.display as afwDisplay
#from lsst.ip.diffim import SourceFlagChecker
import lsst.ip.diffim.utils as diUtils


# This task runner just passes along command line arguments to be passed to run()
class TaskRunnerWithArgs(pipeBase.TaskRunner):
    @staticmethod
    def getTargetList(parsedCmd, **kwargs):
        return pipeBase.TaskRunner.getTargetList(parsedCmd,
                                                 show_diff=parsedCmd.show_diff,
                                                 **kwargs)

class ViewDiffimsTask(pipeBase.CmdLineTask):

    ConfigClass = pexConfig.Config
    RunnerClass = TaskRunnerWithArgs
    _DefaultName="ViewDiffimsTask"

    @classmethod
    def _makeArgumentParser(cls):
        """Create an argument parser
        """
        parser = pipeBase.ArgumentParser(name=cls._DefaultName)
        parser.add_id_argument("--id", "deepDiff_differenceExp", help="data ID, e.g. --id visit=12345 ccdnum=1")
        parser.add_argument("--show-diff", action="store_true")
        return parser

    def run(self, sensorRef, show_diff=False):

        display = afwDisplay.Display(frame=1)
        if show_diff:
            self.show_diff(sensorRef, display)

        diaSources = sensorRef.get("deepDiff_diaSrc", immediate=True)
        print("ccd {:02d}, {:d} sources".format(sensorRef.dataId['ccdnum'], len(diaSources)))

    def show_diff(self, sensorRef, display):

        subtractedExposure = sensorRef.get("deepDiff_differenceExp", immediate=True)
        diaSources = sensorRef.get("deepDiff_diaSrc", immediate=True)

        print(display._defaultMaskPlaneColor)
        display.mtv(subtractedExposure)

        mi = subtractedExposure.getMaskedImage()
        x0, y0 = mi.getX0(), mi.getY0()
        for s in diaSources:
            x, y = s.getX() - x0, s.getY() - y0
            # Measurement is currently a hodge-podge, and I don't know what flags are
            # working and which are not. Skipping this and displaying all sources.
            if False:
                if (s.get("flags.pixel.interpolated.center") or s.get("flags.pixel.saturated.center") or
                    s.get("flags.pixel.cr.center")):
                    ptype = "x"
                elif (s.get("flags.pixel.interpolated.any") or s.get("flags.pixel.saturated.any") or
                      s.get("flags.pixel.cr.any")):
                    ptype = "+"
                else:
                    ptype = "o"
            else:
                ptype = "x"

            display.dot(ptype, x, y, size=15)

        # This is broken, not sure if showDiaSources() is functional.
        if False:
            #flagChecker   = SourceFlagChecker(diaSources)
            #isFlagged     = [flagChecker(x) for x in diaSources]
            isFlagged = [False for x in diaSources]
            #isDipole      = [x.get("classification.dipole") for x in diaSources]
            isDipole = [False for x in diaSources]
            diUtils.showDiaSources(diaSources, diff_exposure, isFlagged, isDipole,
                                   frame=2)


    # Overriding these two functions prevent the task from attempting to save the config.
    def _getConfigName(self):
        return None
    def _getMetadataName(self):
        return None


if __name__ == "__main__":
    ViewDiffimsTask.parseAndRun()
