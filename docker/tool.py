"""
QMENTA entry point for OXASL pipeline
"""

import os
import subprocess
import logging
import traceback

LOG = logging.getLogger(__name__)

def setup_fsl():
    """
    Populate environment variables from FSL setup as would happen if
    we sourced the setup script as normal
    """
    os.environ["FSLDIR"] = "/usr/local/fsl"
    command = 'env -i sh -c ". /usr/local/fsl/etc/fslconf/fsl.sh && env"'
    for line in subprocess.getoutput(command).split("\n"):
        try:
            key, value = line.split("=")
            os.environ[key]= value
        except ValueError:
            LOG.warning(f"Setting up FSL: failed to parse {line}")

def get_nifti_data(context, key, required=True):
    """
    Get input data in NIFTI format

    FIXME what if multiple data files provided?
    """
    file_handlers = context.get_files(key)
    if len(file_handlers) == 0:
        if required:
            raise RuntimeError(f"Required data {key} not provided")
        else:
            return None

    path = file_handlers[0].download('/root/data/')

    if not path.endswith(".nii") and not path.endswith(".nii.gz"):
        # Perform DCM->Nii conversion
        os.makedirs("/root/nifti", exist_ok=True)
        exit_code = os.system(f"dcm2niix -o /root/nifti -z y -b y -f {key} {path}")
        if exit_code == 0:
            return f"/root/nifti/{key}.nii.gz"
        else:
            raise RuntimeError(f"Failed to perform DCM-NII conversion on input data {key}")
    else:
        return path

def ls(context, dir, prog):
    files = str(os.listdir(dir))
    context.set_progress(value=prog, message=files)

def run(context):
    try:
        analysis_data = context.fetch_analysis_data()

        context.set_progress(value=0, message=f"Setting up FSL")
        setup_fsl()
        
        settings = context.get_settings()
        
        context.set_progress(value=10, message=f"Getting input data in NIFTI format")
        asl_path = get_nifti_data(context, 'input')
        context.set_progress(value=11, message=f"Got ASL data: {asl_path}")
        oxasl_cmd = f"oxasl -i {asl_path} -o oxasl_output --debug"

        struc_path = get_nifti_data(context, 'struc', required=False)
        if struc_path:
            context.set_progress(value=12, message=f"Got structural data: {struc_path}")
            oxasl_cmd += f" -s {struc_path}"

        context.set_progress(value=20, message=f"Getting input parameters")
        labelling = settings['labelling'].lower().strip()
        context.set_progress(value=21, message=f"labelling={labelling}")
        casl = labelling.lower() == "pcasl"
        if casl:
            oxasl_cmd += f" --casl"

        plds = settings['plds']
        if casl:
            context.set_progress(value=21, message=f"PLDS={plds}")
            oxasl_cmd += f" --plds {plds}"
        else:
            context.set_progress(value=21, message=f"TIs={plds}")
            oxasl_cmd += f" --tis {plds}"

        # Capture stdout as useful in event of error before logging starts
        oxasl_cmd += " 2>&1 >oxasl_stdout.txt"

        ls(context, "/root/nifti", 29)

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
