Decam diffim processing 9/8/2015
======

This is a running log of my attempts to run image differencing on some sample Decam images. This is related to [DM-3213](https://jira.lsstcorp.org/browse/DM-3213) and I am starting from these branches. I have not sanitized this of self-inflicted mistakes.

Ingest Images
--

	
```shell
{0} lsst_dev % cd obs_decam
{0} obs_decam % setup -r . -t w_2015_36
{0} obs_decam % cd ~
{0} ~ % ingestImagesDecam.py decam_data/ -n --mode link --create
RuntimeError: No mapper provided and no _mapper available
{0} ~ % echo lsst.obs.decam.DecamInstcalMapper > decam_repo/_mapper
```

My mistake, the parameter order is `ingestImageDecam.py OUTPUT_REPO —params INPUT`

	{0} ~ % ingestImagesDecam.py decam_repo -n --mode link --create decam_data
	  File "/Users/ctslater/lsst_dev/obs_decam/config/ingest.py", line 2, in <module>
	    config.parse.retarget(DecamParseTask)
	NameError: name 'config' is not defined

This is because I needed to update pex_config to master, since obs_decam had been updated to follow a change in pex. Self-inflicted.

Ingest warnings:

	ingest.parse WARNING: Unable to find value for ccdnum (derived from CCDNUM)
	ingest.parse WARNING: Unable to find value for expTime (derived from EXPTIME)
	ingest.parse WARNING: Error reading decam_data/instcal/tu1734245.fits.fz extensions set(['N28', 'N19', 'N23', 'N22', 'N21', 'N27', 'N26', 'N24', 'N29', 'N13', 'N12', 'N10', 'N11', 'N16', 'N17', 'N18', 'N31'])

```shell
{0} ~ % processCcdDecam.py ./ --id visit=197395 ccdnum=10 \
	 --config calibrate.doPhotoCal=False \
	 calibrate.doAstrometry=False \
	 calibrate.measurePsf.starSelector.name="secondMoment" \
	 doWriteCalibrateMatches=False --clobber-config
```

Using visit=197391 ccdnum=10 and visit=197395 ccdnum=10, which overlap

side note:  eups declare  -t cts_decam -r ./

After setting up Yusra’s DM-3213 branches in pipe_tasks, obs_decam, and (another package):

```shell
{0} ~ % imageDifferenceDecam.py decam_repo --id visit=197391 ccdnum=10 \
	--config templateVisit=197395
```

## Issue 1 - Missing _pos in plugin name

	  File "/Users/ctslater/lsst/DarwinX86/meas_base/10.1-19-g72ed943+3/python/lsst/meas/base/baseMeasurement.py", line 224, in validate
	    raise ValueError("source centroid slot algorithm is not being run.")
	ValueError: source centroid slot algorithm is not being run.

The issue is in baseMeasurement.py:224,

    if self.slots.centroid is not None and self.slots.centroid not in self.plugins.names:
        raise ValueError("source centroid slot algorithm is not being run.")

From pdb:

	(Pdb) self.plugins.names
	['ip_diffim_NaiveDipoleFlux', 'base_PeakLikelihoodFlux', 'ip_diffim_NaiveDipoleCentroid', 'ip_diffim_PsfDipoleFlux']

but:

	(Pdb) self.slots.centroid
	'ip_diffim_NaiveDipoleCentroid_pos'

so I think it is confused by this additional “_pos” extention. I commented out this check and continued on.

imageDifferenceDecam.py decam_repo --id visit=197391 ccdnum=10 -L info --config templateVisit=197395 doPreConvolve=False --clobber-config

this took forever, and was hung up in convolveWithBruteForce so adding doPreConvolve=False made some progress.

## Issue 2 - Missing PointD

```pytb
ImageDifference FATAL: Failed on dataId={'visit': 197391, 'ccdnum': 10}: 'PointD'
  File "/Users/ctslater/lsst_dev/pipe_tasks/python/lsst/pipe/tasks/imageDifference.py", line 334, in run
    kcQa = KernelCandidateQa(nparam)
  File "/Users/ctslater/lsst_dev/ip_diffim/python/lsst/ip/diffim/kernelCandidateQa.py", line 45, in __init__
    self.fields.append(afwTable.Field["PointD"]("RegisterRefPosition",
KeyError: 'PointD'
```

ip_diffim is attempting to create a table field type PointD, but these types have been removed from afw as of a [commit May 11](https://github.com/lsst/afw/commit/98db935a7a3d51ee52fa5571e7aaea9272fc0867). “These have been superseded by FunctorKeys"

Commented out, proceeding on.

## Issue 3 - KernelCandidateQa deletes footprints

	ImageDifference: Source selection via src product
	measurement: Measuring 1 sources (1 parents, 0 children)
	Assertion failed: (px != 0), function operator->, file /Users/ctslater/lsst/DarwinX86/boost/1.55.0.1.lsst2+3/include/boost/smart_ptr/shared_ptr.hpp, line 653.
	[5]    63697 abort (core dumped)  imageDifferenceDecam.py decam_repo --id visit=197391 ccdnum=10 -L info

Backtrace:

	* thread #1: tid = 0x0000, 0x00007fff8efe1286 libsystem_kernel.dylib`__pthread_kill + 10, stop reason = signal SIGSTOP
	  * frame #0: 0x00007fff8efe1286 libsystem_kernel.dylib`__pthread_kill + 10
	    frame #1: 0x00007fff8fe589f9 libsystem_pthread.dylib`pthread_kill + 90
	    frame #2: 0x00007fff914369b3 libsystem_c.dylib`abort + 129
	    frame #3: 0x00007fff913fea99 libsystem_c.dylib`__assert_rtn + 321
	    frame #4: 0x0000000110cffe63 libmeas_algorithms.dylib`boost::shared_ptr<lsst::afw::detection::Footprint const>::operator->(this=0x00007fff5fbf8d00) const + 83 at shared_ptr.hpp:653
	    frame #5: 0x0000000110cfe253 libmeas_algorithms.dylib`lsst::meas::algorithms::PsfCandidate<float>::extractImage(this=0x00000001006ea460, width=21, height=21) const + 1699 at PsfCandidate.cc:214
	    frame #6: 0x0000000110cfdb0e libmeas_algorithms.dylib`lsst::meas::algorithms::PsfCandidate<float>::getMaskedImage(this=0x00000001006ea460, width=21, height=21) const + 190 at PsfCandidate.cc:304
	    frame #7: 0x0000000110cfda20 libmeas_algorithms.dylib`lsst::meas::algorithms::PsfCandidate<float>::getMaskedImage(this=0x00000001006ea460) const + 144 at PsfCandidate.cc:322
	    frame #8: 0x0000000110686fde _algorithmsLib.so`_wrap_PsfCandidateF_getMaskedImage__SWIG_0((null)=0x0000000000000000, args=0x0000000114f0e990) + 526 at algorithmsLib_wrap.cc:13560
	    frame #9: 0x00000001105ff1d8 _algorithmsLib.so`_wrap_PsfCandidateF_getMaskedImage(self=0x0000000000000000, args=0x0000000114f0e990) + 312 at algorithmsLib_wrap.cc:13703
	    frame #10: 0x00000001000c3772 libpython2.7.dylib`PyEval_EvalFrameEx + 24402

Crashes in "kernelSources = self.sourceSelector.selectStars(exposure, selectSources, matches=matches)”, pipe_tasks/…/imageDifference.py

	> /Users/ctslater/lsst/DarwinX86/meas_algorithms/10.1-17-g7ac7aee+10/python/lsst/meas/algorithms/secondMomentStarSelector.py(256)selectStars()
	-> im = psfCandidate.getMaskedImage().getImage()
	(Pdb)
	Assertion failed: (px != 0), function operator->, file /Users/ctslater/lsst/DarwinX86/boost/1.55.0.1.lsst2+3/include/boost/smart_ptr/shared_ptr.hpp, line 653.
	[2]    64023 abort (core dumped)  python -m pdb `which imageDifferenceDecam.py` decam_repo --id visit=197391  -

The offending line is meas_algorithms/…/PsfCandidate.cc:212

	CONST_PTR(afwDetection::Footprint) foot = getSource()->getFootprint();

This returns a null pointer, and the subsequent call to `foot->getPeaks();` fails.

In imageDifference.py, the catalog entries don’t have footprints when they get passed to selectStars, but they do if I just read the catalog directly. Disabling

The footprints seem to get dropped in `selectSources =
kcQa.addToSchema(selectSources)`. Disabling `doAddMetrics` eliminates the
issue. `getExposure()` should presumably fail more gracefully when
`getFootprint()` returns null.

## Issue #4 - Schema difference between imageDifference and sfm

	ImageDifference: Running diaSource detection
	ImageDifference.detection: Detected 1486 positive sources to 5 sigma.
	ImageDifference.detection: Detected 1328 negative sources to 5 sigma
	ImageDifference: Merging detections into 2474 sources
	ImageDifference: Running diaSource measurement
	ImageDifference FATAL: Failed on dataId={'visit': 197391, 'ccdnum': 10}:
	Traceback (most recent call last):
	  File "/Users/ctslater/lsst/DarwinX86/pipe_base/10.1-4-g6ba0cc7+27/python/lsst/pipe/base/cmdLineTask.py", line 320, in __call__
	    result = task.run(dataRef, **kwargs)
	  File "/Users/ctslater/lsst/DarwinX86/pipe_base/10.1-4-g6ba0cc7+27/python/lsst/pipe/base/timer.py", line 118, in wrapper
	    res = func(self, *args, **keyArgs)
	  File "/Users/ctslater/lsst_dev/pipe_tasks/python/lsst/pipe/tasks/imageDifference.py", line 525, in run
	    self.measurement.run(subtractedExposure, diaSources)
	  File "/Users/ctslater/lsst_dev/meas_base/python/lsst/meas/base/sfm.py", line 277, in run
	    assert measCat.getSchema().contains(self.schema)
	AssertionError

The in imageDifference.py:~517, the schema for diaSources fails the “.contains()” test with the schema for SingleFrameMeasurementTask.

If I edit imageDifference.py so that the makeSubtask argument passes the real schema instead of a new blank one, I get

    Field with name 'base_PeakLikelihoodFlux_flux' already present in schema. {0}
	lsst::pex::exceptions::InvalidParameterError: 'Field with name 'base_PeakLikelihoodFlux_flux' already present in schema.'

I removed the PeakLikelihoodFlux measurement, since it was the only conflict between the schemas, and then had sfm add its fields to the schema at the start. [This commit](https://github.com/lsst/pipe_tasks/commit/0b1970b38df7897bbb4a46824d0d50ad8e9fc760) is probably related.

## Issue #5 - Shape measurement

A million errors of the form:

	ImageDifference: Running diaSource detection
	ImageDifference.detection: Detected 1486 positive sources to 5 sigma.
	ImageDifference.detection: Detected 1328 negative sources to 5 sigma
	ImageDifference: Merging detections into 2474 sources
	ImageDifference: Running diaSource measurement
	ImageDifference.measurement: Measuring 2474 sources (2474 parents, 0 children) 
	...
	ImageDifference.measurement WARNING: Error in base_SdssCentroid.measure on record 84778831902150188:
	  File "src/SdssCentroid.cc", line 270, in void lsst::meas::base::(anonymous namespace)::doMeasureCentroidImpl(double *, double *, double *, double *, double *, double *, double *, MaskedImageXy_locatorT, double, lsst::meas::base::FlagHandler) [MaskedImageXy_locatorT = lsst::afw::image::MaskedImage<float, unsigned short, float>::MaskedImageLocator<boost::gil::memory_based_2d_locator<boost::gil::memory_based_step_iterator<boost::gil::pixel<float, boost::gil::layout<boost::mpl::vector1<boost::gil::gray_color_t>, boost::mpl::range_c<int, 0, 1> > > *> >, boost::gil::memory_based_2d_locator<boost::gil::memory_based_step_iterator<boost::gil::pixel<unsigned short, boost::gil::layout<boost::mpl::vector1<boost::gil::gray_color_t>, boost::mpl::range_c<int, 0, 1> > > *> >, boost::gil::memory_based_2d_locator<boost::gil::memory_based_step_iterator<boost::gil::pixel<float, boost::gil::layout<boost::mpl::vector1<boost::gil::gray_color_t>, boost::mpl::range_c<int, 0, 1> > > *> > >]
	    Object is not at a maximum: d2I/dx2, d2I/dy2 = -32.52 -59.0056 {0}
	lsst::meas::base::MeasurementError: 'Object is not at a maximum: d2I/dx2, d2I/dy2 = -32.52 -59.0056'

	ImageDifference.measurement WARNING: Error in base_GaussianFlux.measure on record 84778831902150188:
	  File "src/InputUtilities.cc", line 192, in afw::geom::ellipses::Quadrupole lsst::meas::base::SafeShapeExtractor::operator()(afw::table::SourceRecord &, const lsst::meas::base::FlagHandler &) const
	    base_GaussianFlux: Shape needed, and Shape slot measurement failed. {0}
	lsst::meas::base::MeasurementError: 'base_GaussianFlux: Shape needed, and Shape slot measurement failed.'

Also:

	  File "src/InputUtilities.cc", line 123, in afw::geom::Point2D lsst::meas::base::SafeCentroidExtractor::operator()(afw::table::SourceRecord &, const lsst::meas::base::FlagHandler &) const
	    base_CircularApertureFlux: Centroid slot value is NaN, but the Centroid slot flag is not set (is the executionOrder for base_CircularApertureFlux lower than that of the slot Centroid?) {0}
	lsst::pex::exceptions::RuntimeError: 'base_CircularApertureFlux: Centroid slot value is NaN, but the Centroid slot flag is not set (is the executionOrder for base_CircularApertureFlux lower than that of the slot Centroid?)'


## Subtracted Images

I moved the write-out of the subtracted images up ahead of measurement, so I could proceed without having to sort out the measurement issue. The subtracted image has mis-registered the two images by a long shot, even though the input WCS on both is excellent. Example:

![Subtracted image](images/bad_subtraction.png?raw=true)

Trying with doDebugRegister=True. That failed because the statistics expect to be able to separate blue from red objects, and we don't have that information.

Trying with doUseRegister=False. We really don't need to re-fit sources to register the images, which is what I think it was doing. 

Noted another problem along the way:

	ImageDifference.subtract: Matching Psf FWHM 28.57 -> 28.56 pix

Printing out the stars it used to measure the convolution kernel, they all seem ok (looking at them on the image). 

In pipe_tasks/.../imageDifference.py, ~279, the initial estimates of the PSF width are way off:

	scienceSigmaOrig 12.130
	templateSigma 12.134

This is coming straight from the exposure PSF, which looks good in ds9, into PsfAttributes.computeGaussianWidth(), which returns this giant number. If I pull up the psf directly, I wonder if X0 and Y0 are causing things downstream to behave weirdly? `PsfAttributes::computeGaussianWidth()` seems to make use of these values for centering, and that seems not right.

	>>> scipsf.computeImage().getBBox()
	Box2I(Point2I(974, 2791), Extent2I(25, 25))
	>>> scipsf.computeImage().getX0()
	974
	>>> scipsf.computeImage().getY0()
	2791


---

	ImageDifference.subtract: Template Wcs : 3.431725,-0.310506 -> 3.437166,-0.313098
	ImageDifference.subtract: Science Wcs : 3.431725,-0.310481 -> 3.437167,-0.313073
	ImageDifference.subtract: Astrometrically registering template to science image

What are these numbers?
