import os


def get_artifact(fname):
    """
    Return the artifact path in the artifact folder
    """
    fpath = os.path.join(get_artifact_folder(), fname)
    if os.path.isfile(fpath):
        return fpath
    return


def get_artifact_folder():
    return os.path.join(os.path.dirname(__file__), "artifacts")


def get_backup_folder():
    return os.path.join(os.path.dirname(__file__), "artifacts", "ios_backup")

def init_setup():
    """
    init data to have a clean state before testing
    """
    try:
        del os.environ['MVT_STIX2']
    except KeyError:
        pass
