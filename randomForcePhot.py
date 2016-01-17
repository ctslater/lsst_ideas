
from __future__ import print_function, division

import lsst
import lsst.meas.base as measBase
import lsst.afw.table as afwTable
import lsst.afw.geom as afwGeom
import lsst.afw.detection as afwDetect
import numpy as np

class RandomForcedConfig(lsst.pex.config.Config):
    """!Config class for forced measurement driver task."""

    measurement = lsst.pex.config.ConfigurableField(
        target=measBase.ForcedMeasurementTask,
        doc="subtask to do forced measurement"
        )
    def setDefaults(self):
        # TransformedCentroid takes the centroid from the reference catalog and uses it.
        self.measurement.plugins.names = ["base_TransformedCentroid", "base_PsfFlux"]
        self.measurement.slots.shape = None

class RandomForcePhotTask(lsst.pipe.base.CmdLineTask):

    ConfigClass = RandomForcedConfig
    _DefaultName = "randomForcePhotTask"

    def __init__(self, butler=None, **kwargs):
        super(lsst.pipe.base.CmdLineTask, self).__init__(**kwargs)

        self.ref_schema = afwTable.SourceTable_makeMinimalSchema()
        self.ref_schema.addField("centroid_x", type=float)
        self.ref_schema.addField("centroid_y", type=float)
        aliases = self.ref_schema.getAliasMap()
        aliases.set("slot_Centroid", "centroid")

        self.makeSubtask("measurement", refSchema=self.ref_schema)
        self.dataPrefix = ""


    def fetchReferences(self, exposure):
        """Makes a SourceCatalog of random points in exposure.
        """
        references = afwTable.SourceCatalog(self.ref_schema)

        wcs = exposure.getWcs()
        bbox = exposure.getBBox()
        n_sources = 200

        for n in xrange(n_sources):
            rec = references.addNew()
            x = np.random.rand() * bbox.getMaxX()
            y = np.random.rand() * bbox.getMaxY()
            rec.set(references.getCentroidKey(), afwGeom.Point2D(x,y))
            rec.updateCoord(wcs)

            fp = afwDetect.Footprint(afwGeom.Point2I(int(x),int(y)), 6.0, bbox)
            fp.addPeak(x, y, 20.0)
            rec.setFootprint(fp)

        return references

    def run(self, dataRef):
        """ Perform forced photometry on random positions within a chip.

        The run method is borrowed directly from ProcessImageForcedTask. It pulls a SourceCatalog
        containing random points from fetchReferences(), attaches footprints from the exposure, then
        runs the measurement plugins on those footprints.
        """

        exposure = dataRef.get()
        refWcs = exposure.getWcs()

        refCat = self.fetchReferences(exposure)
        measCat = self.measurement.generateMeasCat(exposure, refCat, refWcs)

        self.log.info("Performing forced measurement on %s" % dataRef.dataId)
        print(self.measurement.plugins)

        self.measurement.attachTransformedFootprints(measCat, refCat, exposure, refWcs)
        self.measurement.run(measCat, exposure, refCat, refWcs)
        self.writeOutput(dataRef, measCat)

    def writeOutput(self, dataRef, sources):
        """!Write forced source table
        @param dataRef  Data reference from butler; the forced_src dataset (with self.dataPrefix included)
                        is all that will be modified.
        @param sources  SourceCatalog to save
        """
        dataRef.put(sources, self.dataPrefix + "forced_src")

    @classmethod
    def _makeArgumentParser(cls):
        parser = lsst.pipe.base.ArgumentParser(name=cls._DefaultName)

        # Can I make an argument which is a dataset type?
        #parser.add_id_argument("--id", "calexp", help="data ID, with raw CCD keys" )
        parser.add_id_argument("--id", "deepDiff_differenceExp", help="data ID, with raw CCD keys" )
        return parser

    # Overriding these two functions prevent the task from attempting to save the config.
    def _getConfigName(self):
        return None
    def _getMetadataName(self):
        return None


if __name__ == "__main__":

    RandomForcePhotTask.parseAndRun()

