#!/bin/env python

from __future__ import print_function

#import math
#import numpy
import pdb

import lsst.pex.config as pexConfig
import lsst.pipe.base as pipeBase
import lsst.afw.display as afwDisplay
#from lsst.ip.diffim import SourceFlagChecker
from lsst.pipe.tasks.coaddBase import SelectDataIdContainer
import lsst.ip.diffim.utils as diUtils


# This task runner just passes along command line arguments to be passed to run()
class TaskRunnerWithArgs(pipeBase.TaskRunner):
    @staticmethod
    def getTargetList(parsedCmd, **kwargs):
        return pipeBase.TaskRunner.getTargetList(parsedCmd,
                                                 show_diff=parsedCmd.show_diff,
                                                 show_threepanel=parsedCmd.show_threepanel,
                                                 templateRefList=parsedCmd.templateId.refList,
                                                 count_sources=parsedCmd.count_sources,
                                                 **kwargs)

class ViewDiffimsTask(pipeBase.CmdLineTask):

    ConfigClass = pexConfig.Config
    RunnerClass = TaskRunnerWithArgs
    _DefaultName="ViewDiffimsTask"

    #def __init__(self, **kwargs):
    #    pipeBase.CmdLineTask.__init__(self, **kwargs)
    #    self.source_count = 0


    @classmethod
    def _makeArgumentParser(cls):
        """Create an argument parser
        """
        parser = pipeBase.ArgumentParser(name=cls._DefaultName)
        parser.add_id_argument("--id", "deepDiff_differenceExp", help="data ID, e.g. --id visit=12345 ccdnum=1")
        parser.add_id_argument("--templateId", "calexp", help="template image ID, e.g. --templateId visit=6789 ccd=1",
                               ContainerClass=pipeBase.DataIdContainer)
        parser.add_argument("--show-diff", action="store_true")
        parser.add_argument("--show-threepanel", action="store_true")
        parser.add_argument("--count-sources", action="store_true", help="Count image sources instead of difference image sources")
        return parser

    def run(self, sensorRef, show_diff=False, show_threepanel=False, templateRefList=None, count_sources=False):

        display_n = 1

        if show_threepanel:
            display = afwDisplay.Display(frame=display_n)
            display_n += 1
            self.show_original(sensorRef, display)

            if templateRefList:
                display = afwDisplay.Display(frame=display_n)
                display_n += 1
                self.show_original(templateRefList[0], display)

        if show_diff or show_threepanel:
            display = afwDisplay.Display(frame=display_n)
            self.show_diff(sensorRef, display)

        if count_sources:
            sources = sensorRef.get("src", immediate=True)
            source_count = len(sources)
            print("ccd {:02d}, {:d} raw image sources".format(sensorRef.dataId['ccdnum'], source_count))
        else:
            # count_sources = False means count difference image sources. Not ideal terminology here.
            diaSources = sensorRef.get("deepDiff_diaSrc", immediate=True)
            source_count = len(diaSources)
            print("ccd {:02d}, {:d} raw DIA sources".format(sensorRef.dataId['ccdnum'], source_count))

        return source_count

    def is_valid_source(self, source):
        pdb.set_trace()
        print(source)

    def show_original(self, sensorRef, display):
        calexp = sensorRef.get("calexp", immediate=True)
        display.mtv(calexp)

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
    taskResults = ViewDiffimsTask.parseAndRun(doReturnResults=True)
    total_counts = sum(x.result for x in taskResults.resultList)
    print("Total sources: {:d}".format(total_counts))
