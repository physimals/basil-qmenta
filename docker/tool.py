"""
QMENTA entry point for OXASL pipeline
"""

import os
import subprocess
import logging
import shutil
import traceback

import nibabel as nib

LOG = logging.getLogger(__name__)

def setup_fsl(context, progress):
    """
    Populate environment variables from FSL setup as would happen if
    we sourced the setup script as normal

    :param context: Run context
    :param progress: Progress percentage to report
    """
    os.environ["FSLDIR"] = "/usr/local/fsl"
    command = 'env -i sh -c ". /usr/local/fsl/etc/fslconf/fsl.sh && env"'
    try:
        for line in subprocess.check_output(command).split("\n"):
            try:
                key, value = line.split("=")
                os.environ[key]= value
            except ValueError:
                context.set_progress(value=progress, message=f"WARNING: Setting up FSL - failed to parse {line}")
        context.set_progress(value=progress, message=f"Set up FSL environment")
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"WARNING: Failed to execute FSL setup script: {exc.output}")

def get_input_data(oxasl_cmd, context, key, name, option, progress, required=True):
    """
    Get input data in NIFTI format

    Only a single file must be supplied for each key

    :param oxasl_cmd: List of oxasl command options to append to
    :param context: Run context
    :param key: Name of input data in settings json file
    :param name: Readable name of data, e.g. 'structural', 'ASL'
    :param option: Option flag for OXASL command line, e.g. -s
    :param progress: Progress percentage value to report
    :param required: If True, raise exception if data not found
    """
    try:
        file_handlers = context.get_files(key, file_filter_condition_name=f"c_files_{key}")
    except:
        file_handlers = []    
    if len(file_handlers) == 0:
        if required:
            raise RuntimeError(f"Required data {key} not provided")
        else:
            return
    if len(file_handlers) > 1:
        raise RuntimeError(f"Expected single input file for {key} - found {len(file_handlers)} instead")

    dicomdir = f"/root/dicom/{key}"
    niftidir = f"/root/nifti/{key}"
    os.makedirs(dicomdir, exist_ok=True)
    os.makedirs(niftidir, exist_ok=True)
    path = file_handlers[0].download(dicomdir)
    context.set_progress(value=progress, message=f"Downloaded {name} data: {path}")

    if path.endswith(".nii") or path.endswith(".nii.gz"):
        shutil.copy(path, niftidir)
        path = os.path.join(niftidir, os.path.basename(path))
    else:
        # Assume we have DICOMs and perform DCM->Nii conversion
        for fname in os.listdir(path):
            context.set_progress(value=progress, message=f"DCM file found in {path}: {fname}")
        
        try:
            subprocess.check_output(["dcm2niix", "-o", niftidir, "-z", "y", "-b", "y", "-f", key, path])
            for fname in os.listdir(niftidir):
                context.set_progress(value=progress, message=f"DCM2NIIX on {name} output: {fname}")
            path = f"{niftidir}/{key}.nii.gz"
            nii = nib.load(path)
            context.set_progress(value=progress, message=f"Dimensions of {path}: {nii.shape}")
            context.upload_file(path, f"{key}.nii.gz")
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"Failed to perform DCM-NII conversion on {key}: {exc.output}")

    context.set_progress(value=progress, message=f"Got {name} data: {path}")
    oxasl_cmd.extend([option, path])

def get_labelling(oxasl_cmd, context, progress):
    """
    Get labelling options for OXASL

    :param oxasl_cmd: List of oxasl command options to append to
    :param context: Run context
    :param progress: Progress percentage to report
    """
    settings = context.get_settings()
    labelling = settings['labelling'].lower().strip()
    context.set_progress(value=progress, message=f"labelling={labelling}")
    casl = labelling.lower() == "pcasl"
    if casl:
        oxasl_cmd.append("--casl")

def get_timings(oxasl_cmd, context, progress):
    """
    Get TI/PLD timing command line options for OXASL

    :param oxasl_cmd: List of oxasl command options to append to
    :param context: Run context
    :param casl: True if labelling is CASL. This affects whether the timings are PLDs or TIs
    :param progress: Progress percentage to report
    """
    settings = context.get_settings()
    plds = settings['plds']
    if "--casl" in oxasl_cmd:
        context.set_progress(value=progress, message=f"PLDS={plds}")
        oxasl_cmd.extend(["--plds", plds])
    else:
        context.set_progress(value=progress, message=f"TIs={plds}")
        oxasl_cmd.extend(["--tis", plds])

def run(context):
    """
    Main entry point for OXASL analysis tool

    :param context: Run context object for obtaining settings and input data
    """
    try:
        try:
            with open("version.txt", "r") as f:
                version = f.read()
        except:
            traceback.print_exc()
            version = "(unknown)"
        context.set_progress(value=0, message=f"Running OXASL analysis tool v{version}")
        analysis_data = context.fetch_analysis_data()
        setup_fsl(context, 1)

        # Capture stdout as useful in event of error before logging starts
        oxasl_cmd = ["oxasl", "-o", "oxasl_output", "--debug"]

        context.set_progress(value=10, message=f"Getting input data in NIFTI format")
        get_input_data(oxasl_cmd, context, 'asl', "ASL", "-i", 11)
        get_input_data(oxasl_cmd, context, 'struc', 'structural', '-s', 12, required=False)

        context.set_progress(value=20, message=f"Getting input parameters")
        get_labelling(oxasl_cmd, context, 21)
        get_timings(oxasl_cmd, context, 22)

        context.set_progress(value=30, message=f"Running OXASL: {oxasl_cmd}")
        try:
            subprocess.check_output(oxasl_cmd)
            context.set_progress(value=50, message=f"OXASL completed")
            context.set_progress(value=70, message=f"Uploading OXASL output data")
            for idx, fname in enumerate(os.listdir("oxasl_output/output/native")):
                context.set_progress(value=71+idx, message=f"Uploading {fname}")
                context.upload_file(os.path.join("oxasl_output/output/native", fname), fname)
        except subprocess.CalledProcessError as exc:
            if os.path.exists("oxasl_output/logfile"):
                context.set_progress(value=60, message=f"OXASL command failed - logfile found")
            else:
                context.set_progress(value=60, message=f"OXASL command failed - using stdout as log")
                with open("oxasl_output/logfile", "w") as f:
                    f.write(exc.output)

        context.set_progress(value=80, message=f"Uploading OXASL logfile")
        context.upload_file("oxasl_output/logfile", 'logfile.txt')

        context.set_progress(value=100, message="Complete!")
    except:
        msg = traceback.format_exc()
        context.set_progress(value=100, message=f"Failed: {msg}")
