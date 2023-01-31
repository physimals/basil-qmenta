"""
QMENTA entry point for OXASL pipeline
"""

import os
import subprocess
import logging
import traceback

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
    for line in subprocess.getoutput(command).split("\n"):
        try:
            key, value = line.split("=")
            os.environ[key]= value
        except ValueError:
            context.set_progress(value=progress, message=f"WARNING: Setting up FSL - failed to parse {line}")
    context.set_progress(value=progress, message=f"Set up FSL environment")

def get_input_data(context, key, name, option, progress, required=True):
    """
    Get input data in NIFTI format

    FIXME what if multiple data files provided?

    :param context: Run context
    :param key: Name of input data in settings json file
    :param name: Readable name of data, e.g. 'structural', 'ASL'
    :param option: Option flag for OXASL command line, e.g. -s
    :param progress: Progress percentage value to report
    :param required: If True, raise exception if data not found

    :return: Text to add to OXASL command line
    """
    try:
        file_handlers = context.get_files(key)
    except:
        file_handlers = []    
    if len(file_handlers) == 0:
        if required:
            raise RuntimeError(f"Required data {key} not provided")
        else:
            return ""

    path = file_handlers[0].download('/root/data/')
    if not path.endswith(".nii") and not path.endswith(".nii.gz"):
        # Perform DCM->Nii conversion
        os.makedirs("/root/nifti", exist_ok=True)
        exit_code = os.system(f"dcm2niix -o /root/nifti -z y -b y -f {key} {path}")
        if exit_code == 0:
            path = f"/root/nifti/{key}.nii.gz"
        else:
            raise RuntimeError(f"Failed to perform DCM-NII conversion on input data {key}")

    context.set_progress(value=progress, message=f"Got {name} data: {path}")
    return f" {option} {path}"

def get_labelling(context, progress):
    """
    Get labelling options for OXASL

    :param context: Run context
    :param progress: Progress percentage to report
    :return: OXASL command line options for labelling type
    """
    settings = context.get_settings()
    labelling = settings['labelling'].lower().strip()
    context.set_progress(value=progress, message=f"labelling={labelling}")
    casl = labelling.lower() == "pcasl"
    if casl:
        return " --casl"
    else:
        return ""

def get_timings(context, casl, progress):
    """
    Get TI/PLD timing command line options for OXASL

    :param context: Run context
    :param casl: True if labelling is CASL. This affects whether the timings are PLDs or TIs
    :param progress: Progress percentage to report
    :return: OXASL command line options for timings
    """
    settings = context.get_settings()
    plds = settings['plds']
    if casl:
        context.set_progress(value=progress, message=f"PLDS={plds}")
        return f" --plds {plds}"
    else:
        context.set_progress(value=progress, message=f"TIs={plds}")
        return f" --tis {plds}"

def run(context):
    """
    Main entry point for OXASL analysis tool

    :param context: Run context object for obtaining settings and input data
    """
    try:
        context.set_progress(value=0, message=f"Running OXASL analysis tool")
        analysis_data = context.fetch_analysis_data()
        setup_fsl(context, 1)
        
        # Capture stdout as useful in event of error before logging starts
        oxasl_cmd = f"oxasl -o oxasl_output --debug 2>&1 >oxasl_stdout.txt"

        context.set_progress(value=10, message=f"Getting input data in NIFTI format")
        oxasl_cmd += get_input_data(context, 'input', "ASL", "-i", 11)
        oxasl_cmd += get_input_data(context, 'struc', 'structural', '-s', 12, required=False)

        context.set_progress(value=20, message=f"Getting input parameters")
        oxasl_cmd += get_labelling(context, 21)
        oxasl_cmd += get_timings(context, "--casl" in oxasl_cmd, 22)

        context.set_progress(value=30, message=f"Running OXASL: {oxasl_cmd}")
        exit_code = os.system(oxasl_cmd)

        context.set_progress(value=50, message=f"Completed - exit code {exit_code}")
        if exit_code == 0:
            context.set_progress(value=60, message=f"Uploading OXASL logfile")
            context.upload_file("oxasl_output/logfile", 'logfile.txt')
            context.set_progress(value=70, message=f"Uploading OXASL output data")
            for idx, fname in enumerate(os.listdir("oxasl_output/output/native")):
                context.set_progress(value=71+idx, message=f"Uploading {fname}")
                context.upload_file(os.path.join("oxasl_output/output/native", fname), fname)
        elif os.path.exists("oxasl_output/logfile"):
            context.set_progress(value=60, message=f"Failed - uploading OXASL logfile")
            context.upload_file("oxasl_output/logfile", 'logfile.txt')
        else:
            context.set_progress(value=60, message=f"Failed - uploading OXASL stdout")
            context.upload_file("oxasl_stdout.txt", 'logfile.txt')

        context.set_progress(value=100, message="Complete!")
    except:
        msg = traceback.format_exc()
        context.set_progress(value=100, message=f"Failed: {msg}")
