#!/usr/bin/env python

###############################################################################
# Copyright Kitware Inc. and Contributors
# Distributed under the Apache License, 2.0 (apache.org/licenses/LICENSE-2.0)
# See accompanying Copyright.txt and LICENSE files for details
###############################################################################


"""
Run CORE3D metrics.
"""

import argparse
import core3dmetrics
import datetime
import logging
import os
import shutil

import danesfield.metrics.config as config
from danesfield.metrics.coordinate_system import get_coordinate_system, convert_coordinate_system
from danesfield.metrics.datatype import convert_float32


def create_working_dir():
    """
    Create working directory for running metrics.
    All files generated by the metrics evaluation are written to this directory.
    """
    working_dir = 'metrics-' + str(datetime.datetime.now().timestamp()).split('.')[0]
    os.mkdir(working_dir)
    return working_dir


def generate_config_file(working_dir, ref_prefix, test_dsm, test_cls, test_mtl, test_dtm):
    """
    Generate metrics config file from a template.
    """
    # Populate config file template
    contents = config.get_template()
    contents = config.populate_template(contents, ref_prefix, test_dsm, test_cls, test_mtl,
                                        test_dtm)

    # Write config file
    # TODO: When more files than the DSM and CLS are scored, a shorter name convention
    # could be better.
    config_filename = os.path.join(working_dir, config.get_filename(test_dsm, test_cls))
    with open(config_filename, 'w') as f:
        f.write(contents)

    return config_filename


def main(args):
    # Configure argument parser
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory')
    parser.add_argument(
        '--ref-dir',
        type=str,
        required=True,
        help='Reference file directory')
    parser.add_argument(
        '--ref-prefix',
        type=str,
        required=True,
        help='Reference file prefix')
    parser.add_argument(
        '--dsm',
        type=str,
        required=True,
        help='Test Digital Surface Model (DSM) file')
    parser.add_argument(
        '--cls',
        type=str,
        required=True,
        help='Test Class Label (CLS) file')
    parser.add_argument(
        '--mtl',
        type=str,
        required=False,
        help='Test Material (MTL) file')
    parser.add_argument(
        '--dtm',
        type=str,
        required=False,
        help='Test Digital Terrain Model (DTM) file')

    # Parse arguments
    args = parser.parse_args(args)

    # Create working directory with timestamp
    if args.output_dir:
        # Create output directory
        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir)

        working_dir = args.output_dir
    else:
        working_dir = create_working_dir()

    # Get absolute image paths
    ref_dsm = os.path.join(args.ref_dir, args.ref_prefix + '-DSM.tif')
    test_dsm = os.path.join(working_dir, os.path.basename(args.dsm))
    test_cls = os.path.join(working_dir, os.path.basename(args.cls))

    # Copy test images to working directory
    shutil.copyfile(args.dsm, test_dsm)
    shutil.copyfile(args.cls, test_cls)

    # Handle optional inputs
    if args.mtl is not None:
        test_mtl = os.path.join(working_dir, os.path.basename(args.mtl))
        shutil.copyfile(args.mtl, test_mtl)
    else:
        test_mtl = ''
    if args.dtm is not None:
        test_dtm = os.path.join(working_dir, os.path.basename(args.dtm))
        shutil.copyfile(args.dtm, test_dtm)
    else:
        test_dtm = ''

    # Generate metrics config file
    config_filename = generate_config_file(working_dir, args.ref_prefix,
                                           test_dsm, test_cls, test_mtl, test_dtm)

    # Convert test images to use reference coordinate system.
    # This is necessary because align3d can fail ungracefully when the coordinate systems
    # of the reference and test DSM don't match.
    ref_proj4 = get_coordinate_system(ref_dsm)
    convert_coordinate_system(test_dsm, ref_proj4)
    convert_coordinate_system(test_cls, ref_proj4)
    if test_mtl:
        convert_coordinate_system(test_mtl, ref_proj4)
    if test_dtm:
        convert_coordinate_system(test_dtm, ref_proj4)

    # Ensure test DSM uses Float32 data type.
    # This is necessary because align3d doesn't read the Float64 data type.
    # See https://github.com/pubgeo/pubgeo/issues/22.
    convert_float32(test_dsm)

    # Run metrics
    core3dmetrics.main([
        '--config', config_filename,
        '--reference', args.ref_dir,
        '--test', working_dir,
        '--output', working_dir
    ])


if __name__ == '__main__':
    import sys
    loglevel = os.environ.get('LOGLEVEL', 'WARNING').upper()
    logging.basicConfig(level=loglevel)

    main(sys.argv[1:])
