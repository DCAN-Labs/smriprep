"""Interfaces for manipulating GIFTI files."""

import os

import nibabel as nb
from nipype.interfaces.base import File, SimpleInterface, TraitedSpec, isdefined, traits
from nipype.interfaces.workbench.base import WBCommand


class MetricMathInputSpec(TraitedSpec):
    subject_id = traits.Str(desc='subject ID')
    hemisphere = traits.Enum(
        'L',
        'R',
        mandatory=True,
        desc='hemisphere',
    )
    metric = traits.Str(desc='name of metric to invert')
    metric_file = File(exists=True, mandatory=True, desc='input GIFTI file')
    operation = traits.Enum(
        'invert',
        'abs',
        'bin',
        mandatory=True,
        desc='operation to perform',
    )


class MetricMathOutputSpec(TraitedSpec):
    metric_file = File(desc='output GIFTI file')


class MetricMath(SimpleInterface):
    """Prepare GIFTI metric file for use in MSMSulc

    This interface mirrors the action of the following portion
    of FreeSurfer2CaretConvertAndRegisterNonlinear.sh::

        wb_command -set-structure ${metric_file} CORTEX_[LEFT|RIGHT]
        wb_command -metric-math "var * -1" ${metric_file} -var var ${metric_file}
        wb_command -set-map-names ${metric_file} -map 1 ${subject}_[L|R]_${metric}
        # If abs:
        wb_command -metric-math "abs(var)" ${metric_file} -var var ${metric_file}

    We do not add palette information to the output file.
    """

    input_spec = MetricMathInputSpec
    output_spec = MetricMathOutputSpec

    def _run_interface(self, runtime):
        subject, hemi, metric = self.inputs.subject_id, self.inputs.hemisphere, self.inputs.metric
        if not isdefined(subject):
            subject = 'sub-XYZ'

        img = nb.GiftiImage.from_filename(self.inputs.metric_file)
        # wb_command -set-structure
        img.meta['AnatomicalStructurePrimary'] = {'L': 'CortexLeft', 'R': 'CortexRight'}[hemi]
        darray = img.darrays[0]
        # wb_command -set-map-names
        meta = darray.meta
        meta['Name'] = f'{subject}_{hemi}_{metric}'

        datatype = darray.datatype
        if self.inputs.operation == 'abs':
            # wb_command -metric-math "abs(var)"
            data = abs(darray.data)
        elif self.inputs.operation == 'invert':
            # wb_command -metric-math "var * -1"
            data = -darray.data
        elif self.inputs.operation == 'bin':
            # wb_command -metric-math "var > 0"
            data = darray.data > 0
            datatype = 'uint8'

        darray = nb.gifti.GiftiDataArray(
            data,
            intent=darray.intent,
            datatype=datatype,
            encoding=darray.encoding,
            endian=darray.endian,
            coordsys=darray.coordsys,
            ordering=darray.ind_ord,
            meta=meta,
        )
        img.darrays[0] = darray
        hemi_lower = hemi.lower()
        out_filename = os.path.join(runtime.cwd, f'{hemi_lower}h.{metric}.native.shape.gii')
        img.to_filename(out_filename)
        self._results['metric_file'] = out_filename
        return runtime

class MetricFillHolesInputSpec(TraitedSpec):
    """FILL HOLES IN AN ROI METRIC

    wb_command -metric-fill-holes
       <surface> - the surface to use for neighbor information
       <metric-in> - the input ROI metric
       <metric-out> - output - the output ROI metric

       [-corrected-areas] - vertex areas to use instead of computing them from
          the surface
          <area-metric> - the corrected vertex areas, as a metric

       Finds all connected areas that are not included in the ROI, and writes
       ones into all but the largest one, in terms of surface area."""

    surface_file = File(
        mandatory=True,
        exists=True,
        argstr="%s",
        position=1,
        desc="surface to use for neighbor information",
    )
    metric_file = File(
        mandatory=True,
        exists=True,
        argstr="%s",
        position=2,
        desc="input ROI metric",
    )
    out_file = File(
        name_template="%s_filled.shape.gii",
        name_source="metric_file",
        keep_extension=False,
        argstr="%s",
        position=3,
        desc="output ROI metric",
    )
    corrected_areas = File(
        exists=True,
        argstr="-corrected-areas %s",
        desc="vertex areas to use instead of computing them from the surface",
    )


class MetricFillHolesOutputSpec(TraitedSpec):
    out_file = File(desc="output ROI metric")


class MetricFillHoles(WBCommand):
    """Fill holes in an ROI metric.

    Examples

    >>> from niworkflows.interfaces.workbench import MetricFillHoles
    >>> fill_holes = MetricFillHoles()
    >>> fill_holes.inputs.surface_file = 'lh.midthickness.surf.gii'
    >>> fill_holes.inputs.metric_file = 'lh.roi.shape.gii'
    >>> fill_holes.cmdline  # doctest: +NORMALIZE_WHITESPACE
    'wb_command -metric-fill-holes lh.midthickness.surf.gii lh.roi.shape.gii \
    lh.roi.shape_filled.shape.gii'
    """

    input_spec = MetricFillHolesInputSpec
    output_spec = MetricFillHolesOutputSpec
    _cmd = "wb_command -metric-fill-holes"


class MetricRemoveIslandsInputSpec(TraitedSpec):
    """REMOVE ISLANDS IN AN ROI METRIC

    wb_command -metric-remove-islands
       <surface> - the surface to use for neighbor information
       <metric-in> - the input ROI metric
       <metric-out> - output - the output ROI metric

       [-corrected-areas] - vertex areas to use instead of computing them from
          the surface
          <area-metric> - the corrected vertex areas, as a metric

    Finds all connected areas in the ROI, and zeros out all but the largest
    one, in terms of surface area."""

    surface_file = File(
        mandatory=True,
        exists=True,
        argstr="%s",
        position=1,
        desc="surface to use for neighbor information",
    )
    metric_file = File(
        mandatory=True,
        exists=True,
        argstr="%s",
        position=2,
        desc="input ROI metric",
    )
    out_file = File(
        name_template="%s_noislands.shape.gii",
        name_source="metric_file",
        keep_extension=False,
        argstr="%s",
        position=3,
        desc="output ROI metric",
    )
    corrected_areas = File(
        exists=True,
        argstr="-corrected-areas %s",
        desc="vertex areas to use instead of computing them from the surface",
    )


class MetricRemoveIslandsOutputSpec(TraitedSpec):
    out_file = File(desc="output ROI metric")


class MetricRemoveIslands(WBCommand):
    """Remove islands in an ROI metric.

    Examples

    >>> from niworkflows.interfaces.workbench import MetricRemoveIslands
    >>> remove_islands = MetricRemoveIslands()
    >>> remove_islands.inputs.surface_file = 'lh.midthickness.surf.gii'
    >>> remove_islands.inputs.metric_file = 'lh.roi.shape.gii'
    >>> remove_islands.cmdline  # doctest: +NORMALIZE_WHITESPACE
    'wb_command -metric-remove-islands lh.midthickness.surf.gii \
    lh.roi.shape.gii lh.roi.shape_noislands.shape.gii'
    """

    input_spec = MetricRemoveIslandsInputSpec
    output_spec = MetricRemoveIslandsOutputSpec
    _cmd = "wb_command -metric-remove-islands"
