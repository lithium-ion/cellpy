import os
from pathlib import Path
import sys
import subprocess
import logging
import getpass
import click
import pkg_resources
import pathlib
from github import Github

from cellpy.parameters import prmreader
from cellpy.exceptions import ConfigFileNotWritten
import cellpy._version

DEFAULT_FILENAME_START = "_cellpy_prms_"
DEFAULT_FILENAME_END = ".conf"
DEFAULT_FILENAME = DEFAULT_FILENAME_START + "default" + DEFAULT_FILENAME_END
VERSION = cellpy._version.__version__
REPO = "jepegit/cellpy"
USER = "jepegit"
GITHUB_PWD_VAR_NAME = "GD_PWD"
GITHUB_SIZE_LIMIT = 1_000_000


def save_prm_file(prm_filename):
    """saves (writes) the prms to file"""
    prmreader._write_prm_file(prm_filename)


def get_package_prm_dir():
    """gets the folder where the cellpy package lives"""
    prm_dir = pkg_resources.resource_filename("cellpy", "parameters")
    return prm_dir


def get_default_config_file_path(init_filename=None):
    """gets the path to the default config-file"""
    prm_dir = get_package_prm_dir()
    if not init_filename:
        init_filename = DEFAULT_FILENAME
    src = os.path.join(prm_dir, init_filename)
    return src


def get_user_dir_and_dst(init_filename):
    """gets the name of the user directory and full prm filepath"""
    user_dir = get_user_dir()
    dst_file = os.path.join(user_dir, init_filename)
    return user_dir, dst_file


def get_user_dir():
    """gets the name of the user directory"""
    user_dir = os.path.abspath(os.path.expanduser("~"))
    return user_dir


def get_dst_file(user_dir, init_filename):
    dst_file = os.path.join(user_dir, init_filename)
    return dst_file


def get_user_name():
    """get the user name of the current user (cross platform)"""
    return getpass.getuser()


def create_custom_init_filename(user_name=None):
    """creates a custom prms filename"""
    if user_name is None:
        return DEFAULT_FILENAME_START + get_user_name() + DEFAULT_FILENAME_END
    else:
        return DEFAULT_FILENAME_START + user_name + DEFAULT_FILENAME_END


def check_if_needed_modules_exists():
    pass


def modify_config_file():
    pass


def create_cellpy_folders():
    pass


@click.group("cellpy")
def cli():
    pass


@click.command()
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    default=False,
    help="Allows you to specify div. folders and setting.",
)
@click.option(
    "--not-relative",
    "-nr",
    is_flag=True,
    default=False,
    help="If root-dir is given, put it directly in the root (/) folder"
    " i.e. don't put it in your home directory. Defaults to False. Remark"
    " that if you specifically write a path name instead of selecting the"
    " suggested default, the path you write will be used as is.",
)
@click.option(
    "--dry-run",
    "-dr",
    is_flag=True,
    default=False,
    help="Run setup in dry mode (only print - do not execute). This is"
    " typically used when developing and testing cellpy. Defaults to"
    " False.",
)
@click.option(
    "--reset",
    "-r",
    is_flag=True,
    default=False,
    help="Do not suggest path defaults based on your current configuration-file",
)
@click.option(
    "--root-dir",
    "-d",
    default=None,
    help="Use custom root dir. If not given, your home directory"
    " will be used as the top level where cellpy-folders"
    " will be put. The folder path must follow"
    " directly after this option (if used). Example:\n"
    " $ cellpy setup -d 'MyDir'",
)
@click.option(
    "--testuser", "-t", default=None, help="Fake name for fake user (for tesing)"
)
def setup(interactive, not_relative, dry_run, reset, root_dir, testuser):
    """This will help you to setup cellpy."""

    click.echo("[cellpy] (setup)")

    # generate variables
    init_filename = create_custom_init_filename()
    userdir, dst_file = get_user_dir_and_dst(init_filename)

    if testuser:
        if not root_dir:
            root_dir = os.getcwd()

        click.echo(f"[cellpy] (setup) DEV-MODE testuser: {testuser}")
        init_filename = create_custom_init_filename(testuser)
        userdir = root_dir
        dst_file = get_dst_file(userdir, init_filename)
        click.echo(f"[cellpy] (setup) DEV-MODE userdir: {userdir}")
        click.echo(f"[cellpy] (setup) DEV-MODE dst_file: {dst_file}")

    if not pathlib.Path(dst_file).is_file():
        reset = True

    if interactive:
        click.echo(" interactive mode ".center(80, "-"))
        _update_paths(root_dir, not not_relative, dry_run=dry_run, reset=reset)
        _write_config_file(userdir, dst_file, init_filename, dry_run)
        _check()

    else:
        _write_config_file(userdir, dst_file, init_filename, dry_run)
        _check()


def _update_paths(
    custom_dir=None,
    relative_home=True,
    reset=False,
    dry_run=False,
    default_dir="cellpy_data",
):

    h = pathlib.Path.home()
    if custom_dir:
        if relative_home:
            h = h / custom_dir
        else:
            h = custom_dir

    if not reset:
        outdatadir = pathlib.Path(prmreader.prms.Paths.outdatadir)
        rawdatadir = pathlib.Path(prmreader.prms.Paths.rawdatadir)
        cellpydatadir = pathlib.Path(prmreader.prms.Paths.cellpydatadir)
        filelogdir = pathlib.Path(prmreader.prms.Paths.filelogdir)
        examplesdir = pathlib.Path(prmreader.prms.Paths.examplesdir)
        db_path = pathlib.Path(prmreader.prms.Paths.db_path)
        db_filename = prmreader.prms.Paths.db_filename
        notebookdir = pathlib.Path(prmreader.prms.Paths.notebookdir)
    else:
        outdatadir = "out"
        rawdatadir = "raw"
        cellpydatadir = "cellpyfiles"
        filelogdir = "logs"
        examplesdir = "examples"
        db_path = "db"
        db_filename = "cellpy_db.xlsx"
        notebookdir = "notebooks"
        if not custom_dir:
            h = h / default_dir

    outdatadir = h / outdatadir
    rawdatadir = h / rawdatadir
    cellpydatadir = h / cellpydatadir
    filelogdir = h / filelogdir
    examplesdir = h / examplesdir
    db_path = h / db_path
    notebookdir = h / notebookdir

    outdatadir = _ask_about_path(
        "where to output processed data and results", outdatadir
    )

    rawdatadir = _ask_about_path("where your raw data are located", rawdatadir)

    cellpydatadir = _ask_about_path("where to put cellpy-files", cellpydatadir)

    filelogdir = _ask_about_path("where to dump the log-files", filelogdir)

    examplesdir = _ask_about_path(
        "where to download cellpy examples and tests", examplesdir
    )

    db_path = _ask_about_path("what folder your db file lives in", db_path)

    db_filename = _ask_about_name("the name of your db-file", db_filename)

    notebookdir = _ask_about_path("where to put your jupyter notebooks", notebookdir)

    # update folders based on suggestions
    for d in [outdatadir, rawdatadir, cellpydatadir, filelogdir, examplesdir, db_path]:
        if not dry_run:
            _create_dir(d)
        else:
            click.echo(f" -> creating {d}")

    # update config-file based on suggestions
    prmreader.prms.Paths.outdatadir = str(outdatadir)
    prmreader.prms.Paths.rawdatadir = str(rawdatadir)
    prmreader.prms.Paths.cellpydatadir = str(cellpydatadir)
    prmreader.prms.Paths.filelogdir = str(filelogdir)
    prmreader.prms.Paths.examplesdir = str(examplesdir)
    prmreader.prms.Paths.db_path = str(db_path)
    prmreader.prms.Paths.db_filename = str(db_filename)
    prmreader.prms.Paths.notebookdir = str(notebookdir)


def _ask_about_path(q, p):
    click.echo(f"\n[cellpy] (setup) input {q}:\n[cellpy] (setup) [{p}]")
    new_path = input("[cellpy] (setup) >>> ").strip()
    if not new_path:
        new_path = p
    return pathlib.Path(new_path)


def _ask_about_name(q, n):
    click.echo(f"[cellpy] (setup) input {q}:\n[cellpy] (setup) [{n}]")
    new_name = input("[cellpy] (setup) >>> ").strip()
    if not new_name:
        new_name = n
    return new_name


def _create_dir(path, confirm=True, parents=True, exist_ok=True):
    o = path.resolve()
    if not o.is_dir():
        o_parent = o.parent
        create_dir = True
        if confirm:
            if not o_parent.is_dir():
                create_dir = input(
                    f"[cellpy] (setup) {o_parent} does not exist." f" Create it [y]/n ?"
                )
                if not create_dir:
                    create_dir = True
                elif create_dir in ["y", "Y"]:
                    create_dir = True
                else:
                    create_dir = False

        if create_dir:
            o.mkdir(parents=parents, exist_ok=exist_ok)
        else:
            click.echo(f"[cellpy] (setup) Could not create {o}")
    return o


def _check_import_cellpy():
    try:
        import cellpy
        from cellpy import log
        from cellpy.readers import cellreader

        return True
    except:
        return False


def _check_import_pyodbc():
    from cellpy.parameters import prms
    import platform

    ODBC = prms._odbc
    SEARCH_FOR_ODBC_DRIVERS = prms._search_for_odbc_driver

    use_subprocess = prms.Instruments.Arbin.use_subprocess
    detect_subprocess_need = prms.Instruments.Arbin.detect_subprocess_need
    click.echo()
    click.echo(f" reading prms")
    click.echo(f" - ODBC: {ODBC}")
    click.echo(f" - SEARCH_FOR_ODBC_DRIVERS: {SEARCH_FOR_ODBC_DRIVERS}")
    click.echo(f" - use_subprocess: {use_subprocess}")
    click.echo(f" - detect_subprocess_need: {detect_subprocess_need}")
    click.echo(f" - stated office version: {prms.Instruments.Arbin.office_version}")

    click.echo(" checking system")
    is_posix = False
    is_macos = False
    if os.name == "posix":
        is_posix = True
        click.echo(f" - running on posix")
    current_platform = platform.system()
    if current_platform == "Darwin":
        is_macos = True
        click.echo(f" - running on a mac")

    python_version, os_version = platform.architecture()
    click.echo(f" - python version: {python_version}")
    click.echo(f" - os version: {os_version}")

    if not is_posix:
        if not prms.Instruments.Arbin.sub_process_path:
            sub_process_path = str(prms._sub_process_path)
        else:
            sub_process_path = str(prms.Instruments.Arbin.sub_process_path)
        click.echo(f" stated path to sub-process: {sub_process_path}")
        if not os.path.isfile(sub_process_path):
            click.echo(f" - OBS! missing")

    if is_posix:
        click.echo(" checking existence of mdb-export")
        sub_process_path = "mdb-export"
        from subprocess import PIPE, run

        command = ["command", "-v", sub_process_path]

        try:
            result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True)
            if result.returncode == 0:
                click.echo(f" - found it: {result.stdout}")
            else:
                click.echo(f" - failed finding it")

            if is_macos:
                driver = "/usr/local/lib/libmdbodbc.dylib"
                click.echo(f" looks like you are on a mac (driver set to\n {driver})")
                if not os.path.isfile(driver):
                    click.echo(" - but cannot find it!")
                    return False
            return True

        except AssertionError:
            click.echo(" - not found")
            return False

    # not posix - checking for odbc drivers
    # 1) checking if you have defined one
    try:
        driver = prms.Instruments.Arbin.odbc_driver
        if not driver:
            raise AttributeError
        click.echo("You have defined an odbc driver in your conifg file")
        click.echo(f"driver: {driver}")
    except AttributeError:
        click.echo("FYI: you have not defined any odbc_driver(s)")
        click.echo(
            "(The name of the driver from the configuration file is "
            "used as a backup when cellpy cannot locate a driver by itself)"
        )

    use_ado = False

    if ODBC == "ado":
        use_ado = True
        click.echo(" you stated that you prefer the ado loader")
        click.echo(" checking if adodbapi is installed")
        try:
            import adodbapi as dbloader
        except ImportError:
            use_ado = False
            click.echo(" Failed! Try setting pyodbc as your loader or install")
            click.echo(" adodbapi (http://adodbapi.sourceforge.net/)")

    if not use_ado:
        if ODBC == "pyodbc":
            click.echo(" you stated that you prefer the pyodbc loader")
            try:
                import pyodbc as dbloader
            except ImportError:
                click.echo(" Failed! Could not import it.")
                click.echo(" Try 'pip install pyodbc'")
                dbloader = None

        elif ODBC == "pypyodbc":
            click.echo(" you stated that you prefer the pypyodbc loader")
            try:
                import pypyodbc as dbloader
            except ImportError:
                click.echo(" Failed! Could not import it.")
                click.echo(" try 'pip install pypyodbc'")
                click.echo(" or set pyodbc as your loader in your prm file")
                click.echo(" (and install it)")
                dbloader = None

    click.echo(" searching for odbc drivers")
    try:
        drivers = [
            driver
            for driver in dbloader.drivers()
            if "Microsoft Access Driver" in driver
        ]
        click.echo(f"Found these: {drivers}")
        driver = drivers[0]
        click.echo(f"odbc driver: {driver}")
        return True

    except IndexError as e:
        logging.debug("Unfortunately, it seems the list of drivers is emtpy.")
        click.echo(
            "\nCould not find any odbc-drivers suitable for .res-type files. "
            "Check out the homepage of pydobc for info on installing drivers"
        )
        click.echo(
            "One solution that might work is downloading "
            "the Microsoft Access database engine "
            "(in correct bytes (32 or 64)) "
            "from:\n"
            "https://www.microsoft.com/en-us/download/details.aspx?id=13255"
        )
        click.echo(
            "Or install mdbtools and set it up " "(check the cellpy docs for help)"
        )
        click.echo("\n")
        return False


def _check():
    click.echo(" checking ".center(80, "-"))
    failed_checks = 0
    number_of_checks = 0

    def sub_check(check_type, check_func):
        failed = 0
        click.echo(f"[cellpy] * - Checking {check_type}")
        if check_func():
            click.echo(f"[cellpy] -> succeeded!")
        else:
            click.echo("f[cellpy] -> failed!!!!")
            failed = 1
        return failed

    check_types = ["cellpy imports", "importing pyodbc"]
    check_funcs = [_check_import_cellpy, _check_import_pyodbc]

    for ct, cf in zip(check_types, check_funcs):
        try:
            failed_checks += sub_check(ct, cf)
        except Exception as e:
            click.echo(f"[cellpy] check raised an exception ({e})")
        number_of_checks += 1
    succeeded_checks = number_of_checks - failed_checks
    click.echo(f"[cellpy] Succeeded {succeeded_checks} of {number_of_checks} checks.")


def _write_config_file(userdir, dst_file, init_filename, dry_run):
    click.echo(" update configuration ".center(80, "-"))
    click.echo("[cellpy] (setup) Writing configurations to user directory:")
    click.echo(f"\n         {userdir}\n")

    if os.path.isfile(dst_file):
        click.echo("[cellpy] (setup) File already exists!")
        click.echo("[cellpy] (setup) Keeping most of the old configuration parameters")
    try:
        if dry_run:
            click.echo(
                f"*** dry-run: skipping actual saving of {dst_file} ***", color="red"
            )
        else:
            save_prm_file(dst_file)

    except ConfigFileNotWritten:
        click.echo("[cellpy] (setup) Something went wrong!" " Could not write the file")
        click.echo(
            "[cellpy] (setup) Trying to write a file"
            + f"called {DEFAULT_FILENAME} instead"
        )

        try:
            userdir, dst_file = get_user_dir_and_dst(init_filename)
            if dry_run:
                click.echo(
                    f"*** dry-run: skipping actual saving of {dst_file} ***",
                    color="red",
                )
            else:
                save_prm_file(dst_file)

        except ConfigFileNotWritten:
            _txt = "[cellpy] (setup) No, that did not work either.\n"
            _txt += "[cellpy] (setup) Well, guess you have to talk to the developers."
            click.echo(_txt)
    else:
        click.echo(f"[cellpy] (setup) Configuration file written!")
        click.echo(
            f"[cellpy] (setup) OK! Now you can edit it. For example by "
            f"issuing \n\n         [your-favourite-editor] {init_filename}\n"
        )


@click.command()
@click.option("--version", "-v", is_flag=True, help="Print version information.")
@click.option(
    "--configloc", "-l", is_flag=True, help="Print full path to the config file."
)
@click.option("--params", "-p", is_flag=True, help="Dump all parameters to screen.")
@click.option(
    "--check",
    "-c",
    is_flag=True,
    help="Do a sanity check to see if things" " works as they should.",
)
def info(version, configloc, params, check):
    """This will give you some valuable information about your cellpy."""
    complete_info = True

    if check:
        complete_info = False
        _check()

    if version:
        complete_info = False
        _version()

    if configloc:
        complete_info = False
        _configloc()

    if params:
        complete_info = False
        _dump_params()

    if complete_info:
        _version()
        _configloc()


@click.command()
@click.option(
    "--journal",
    "-j",
    is_flag=True,
    help="Run a batch job defined in the given journal-file",
)
@click.option("--debug", "-d", is_flag=True, help="Run in debug mode.")
@click.option(
    "--silent", "-s", is_flag=True, help="Run in silent (i.e. no-plotting) mode."
)
@click.argument("file_name")
def run(journal, debug, silent, file_name):
    """Will in the future be used for running a cellpy process.

    You can use this to launch specific applications.

    Examples:

        edit your cellpy database

           cellpy run db

        run a batch job described in a journal file (not implemented yet)

           cellpy run -j my_experiment.json

    """

    click.echo(f" RUNNING {file_name} ".center(80, "*"))
    if not file_name:
        click.echo("[cellpy] (run) No filename provided.")
        return

    if debug:
        click.echo("[cellpy] (run) debug mode on")

    if silent:
        click.echo("[cellpy] (run) silent mode on")

    click.echo("[cellpy]\n")

    if journal:
        _run_journal(file_name, debug, silent)

    elif file_name.lower() == "db":
        _run_db(debug, silent)

    else:
        _run(file_name, debug, silent)


def _run_journal(file_name, debug, silent):
    click.echo(f"running journal {file_name}")
    click.echo(f" --debug [{debug}]")
    click.echo(f" --silent [{silent}]")


def _run(file_name, debug, silent):
    click.echo(f"running {file_name}")
    click.echo(f" --debug [{debug}]")
    click.echo(f" --silent [{silent}]")


def _run_db(debug, silent):
    from cellpy import prms
    import platform

    if not silent:
        click.echo(f"running database editor")
    if debug:
        click.echo("running in debug-mode, but nothing to tell")

    db_path = Path(prms.Paths.db_path) / prms.Paths.db_filename

    if platform.system() == "Windows":
        try:
            os.system(f'start excel "{str(db_path)}"')
        except Exception as e:
            click.echo("Something went wrong trying to open")
            click.echo(db_path)
            print()
            print(e)

    elif platform.system() == "Linux":
        print("RUNNING LINUX")
        # not tested
        subprocess.check_call(["open", "-a", "Microsoft Excel", db_path])

    elif platform.system() == "Darwin":
        click.echo(f" - running on a mac")
        subprocess.check_call(["open", "-a", "Microsoft Excel", db_path])

    else:
        print("RUNNING SOMETHING ELSE")
        print(platform.system())
        # not tested
        subprocess.check_call(["open", "-a", "Microsoft Excel", db_path])


@click.command()
@click.option("--tests", "-t", is_flag=True, help="Download test-files from repo.")
@click.option(
    "--examples", "-e", is_flag=True, help="Download example-files from repo."
)
@click.option("--clone", "-c", is_flag=True, help="Clone the full repo.")
@click.option("--directory", "-d", default=None, help="Save into custom directory DIR")
@click.option("--password", "-p", default=None, help="Password option for the repo")
def pull(tests, examples, clone, directory, password):
    """Download examples or tests from the big internet."""
    if directory is not None:
        click.echo(f"[cellpy] (pull) custom directory: {directory}")
    else:
        directory = pathlib.Path(prmreader.prms.Paths.examplesdir)

    if password is not None:
        click.echo("DEV MODE: password provided")
    if clone:
        _clone_repo(directory, password)
    else:
        if tests:
            _pull_tests(directory, password)
        if examples:
            _pull_examples(directory, password)


def _clone_repo(directory, password):
    txt = "[cellpy] The plan is that this "
    txt += "[cellpy] cmd will pull (clone) the cellpy repo.\n"
    txt += "[cellpy] For now it only prins the link to the git-hub\n"
    txt += "[cellpy] repository:\n"
    txt += "[cellpy]\n"
    txt += "[cellpy] https://github.com/jepegit/cellpy.git\n"
    txt += "[cellpy]\n"
    click.echo(txt)


def _pull_tests(directory, pw=None):
    txt = (
        "[cellpy] (pull) Pulling tests from",
        " https://github.com/jepegit/cellpy.git",
    )
    click.echo(txt)
    _pull(gdirpath="tests", rootpath=directory, pw=pw)
    _pull(gdirpath="testdata", rootpath=directory, pw=pw)


def _pull_examples(directory, pw):
    txt = (
        "[cellpy] (pull) Pulling examples from",
        " https://github.com/jepegit/cellpy.git",
    )
    click.echo(txt)
    _pull(gdirpath="examples", rootpath=directory, pw=pw)


def _version():
    txt = "[cellpy] version: " + str(VERSION)
    click.echo(txt)


def _configloc():
    config_file_name = prmreader._get_prm_file()
    click.echo("[cellpy] ->%s\n" % config_file_name)
    if not os.path.isfile(config_file_name):
        click.echo("[cellpy] File does not exist!")


def _dump_params():
    click.echo("[cellpy] Dumping parameters to screen:\n")
    prmreader.info()


def _download_g_blob(name, local_path):
    import urllib.request

    dirs = local_path.parent
    if not dirs.is_dir():
        click.echo(f"[cellpy] (pull) creating dir: {dirs}")
        dirs.mkdir(parents=True)

    filename, headers = urllib.request.urlretrieve(
        name.download_url, filename=local_path
    )
    click.echo(f"[cellpy] (pull) downloaded blob: {filename}")


def _download_g_file(repo, name, local_path):
    file_content = repo.get_file_contents(name)
    dirs = local_path.parent

    if not dirs.is_dir():
        click.echo(f"[cellpy] (pull) creating dir: {dirs}")
        dirs.mkdir(parents=True)
    with local_path.open("wb") as ofile:
        ofile.write(file_content.decoded_content)
        click.echo(f"[cellpy] (pull) downloaded: {name}")


def _parse_g_dir(repo, gdirpath):
    """parses a repo directory two-levels deep"""
    for f in repo.get_contents(gdirpath):
        if f.type == "dir":
            for sf in repo.get_contents(f.path):
                yield sf
        else:
            yield f


def _get_user_name():
    return "jepegit"


def _get_pw(method):
    if method == "ask":
        return getpass.getpass()
    elif method == "env":
        return os.environ.get(GITHUB_PWD_VAR_NAME, None)

    else:
        return None


def _pull(gdirpath="examples", rootpath=None, u=None, pw=None):

    if rootpath is None:
        rootpath = prmreader.prms.Paths.examplesdir

    ndirpath = rootpath / gdirpath

    if pw is not None:
        click.echo(" DEV MODE ".center(80, "-"))
        u = _get_user_name()
        if pw == "ask":
            click.echo("   - ask for password")
            pw = _get_pw(pw)
        elif pw == "env":
            click.echo("   - check environ for password ")
            pw = _get_pw(pw)
            click.echo("   - got something")
            if pw is None:
                click.echo("   - only None")
                u = None

    g = Github(u, pw)
    repo = g.get_repo(REPO)

    click.echo(f"[cellpy] (pull) pulling {gdirpath}")
    click.echo(f"[cellpy] (pull) -> {ndirpath}")

    if not ndirpath.is_dir():
        click.echo(f"[cellpy] (pull) creating dir: {ndirpath}")
        ndirpath.mkdir(parents=True)

    for gfile in _parse_g_dir(repo, gdirpath):
        gfilename = pathlib.Path(gfile.path)
        nfilename = rootpath / gfilename

        if gfile.size > GITHUB_SIZE_LIMIT:
            _download_g_blob(gfile, nfilename)

        else:
            _download_g_file(repo, gfilename.as_posix(), nfilename)


@click.command()
@click.option(
    "--template",
    "-t",
    default="standard",
    help="what template to use ('standard', 'gitt', or 'single').",
)
@click.option("--directory", "-d", default=None, help="Create in custom directory DIR")
@click.option("--serve", "-s", is_flag=True, help="Run Jupyter.")
@click.option("--lab", "-l", is_flag=True, help="Use Jupyter Lab instead of Notebook")
def new(template, directory, serve, lab):
    """Will in the future be used for setting up a batch experiment."""
    if lab:
        server = "lab"
    else:
        server = "notebook"
    try:
        import cookiecutter.main
        import cookiecutter.exceptions
        import cookiecutter.prompt
    except ModuleNotFoundError:
        click.echo("Could not import cookiecutter.")
        click.echo("Try installing it with. For example by writing:")
        click.echo("\npip install cookiecutter\n")

    from cellpy.parameters import prms

    templates = {"standard": "https://github.com/jepegit/cellpy_cookie_standard.git"}

    click.echo(f"Template: {template}")
    if not template.lower() in templates.keys():
        click.echo("This template does not exist. Aborting.")

    if directory is None:
        logging.debug("no dir given")
        directory = prms.Paths.notebookdir

    if not os.path.isdir(directory):
        click.echo("Sorry. This did not work as expected!")
        click.echo(f" - {directory} does not exist")
        return

    directory = Path(directory)

    project_dirs = [
        d.name for d in directory.iterdir() if d.is_dir() and not d.name.startswith(".")
    ]
    project_dirs.insert(0, "[create new dir]")

    project_dir = cookiecutter.prompt.read_user_choice(
        "Select project folder?", project_dirs
    )

    if project_dir == "[create new dir]":
        default_name = "cellpy_project"
        temp_default_name = default_name
        for j in range(999):
            if temp_default_name in project_dirs:
                temp_default_name = default_name + str(j + 1).zfill(3)
            else:
                default_name = temp_default_name
                break

        project_dir = cookiecutter.prompt.read_user_variable("New name", default_name)
        try:
            os.mkdir(directory / project_dir)
            click.echo(f"created {project_dir}")
        except FileExistsError:
            click.echo("OK - but this directory already exists!")

    os.chdir(directory / project_dir)

    try:
        cookiecutter.main.cookiecutter(
            templates[template.lower()], extra_context={"project_name": project_dir}
        )
    except cookiecutter.exceptions.OutputDirExistsException as e:
        click.echo("Sorry. This did not work as expected!")
        click.echo(" - cookiecutter refused to create the project")
        click.echo(e)

    if serve:
        os.chdir(directory)
        _serve(server)


def _serve(server):
    click.echo(f"serving with jupyter {server}")
    subprocess.run(["jupyter", server], check=True)
    click.echo("Finished serving.")


@click.command()
@click.option("--lab", "-l", is_flag=True, help="Use Jupyter Lab instead of Notebook")
@click.option("--directory", "-d", default=None, help="Start in custom directory DIR")
def serve(lab, directory):
    """Start a Jupyter server"""

    from cellpy.parameters import prms

    if directory is None:
        directory = prms.Paths.notebookdir
    elif directory == "home":
        directory = Path().home()
    elif directory == "here":
        directory = Path(os.getcwd())

    if not os.path.isdir(directory):
        click.echo("Sorry. This did not work as expected!")
        click.echo(f" - {directory} does not exist")
        return

    if lab:
        server = "lab"
    else:
        server = "notebook"

    os.chdir(directory)
    _serve(server)


cli.add_command(setup)
cli.add_command(info)
cli.add_command(pull)
cli.add_command(run)
cli.add_command(new)
cli.add_command(serve)


# tests etc
def _main_pull():
    if sys.platform == "win32":
        rootpath = pathlib.Path(r"C:\Temp\cellpy_user")
    else:
        rootpath = pathlib.Path("/Users/jepe/scripting/tmp/cellpy_test_user")
    _pull_examples(rootpath, pw="env")
    _pull_tests(rootpath, pw="env")
    # _pull(gdirpath="examples", rootpath=rootpath, u="ask", pw="ask")
    # _pull(gdirpath="tests", rootpath=rootpath, u="ask", pw="ask")
    # _pull(gdirpath="testdata", rootpath=rootpath, u="ask", pw="ask")


def _main():
    file_name = create_custom_init_filename()
    click.echo(file_name)
    user_directory, destination_file_name = get_user_dir_and_dst(file_name)
    click.echo(user_directory)
    click.echo(destination_file_name)
    click.echo("trying to save it")
    save_prm_file(destination_file_name + "_dummy")

    click.echo(" Testing setup ".center(80, "="))
    setup(["--interactive", "--reset"])


def _cli_setup_interactive():
    from click.testing import CliRunner

    if sys.platform == "win32":
        root_dir = r"C:\Temp\cellpy_user"
    else:
        root_dir = "/Users/jepe/scripting/tmp/cellpy_test_user"
    testuser = "tester"
    init_filename = create_custom_init_filename(testuser)
    dst_file = get_dst_file(root_dir, init_filename)
    init_file = pathlib.Path(dst_file)
    opts = list()
    opts.append("setup")
    opts.append("-i")
    # opts.append("-nr")
    opts.append("-r")
    opts.extend(["-d", root_dir])
    opts.extend(["-t", testuser])

    input_str = "\n"  # out
    input_str += "\n"  # rawdatadir
    input_str += "\n"  # cellpyfiles
    input_str += "\n"  # log
    input_str += "\n"  # examples
    input_str += "\n"  # dbfolder
    input_str += "\n"  # dbfile
    runner = CliRunner()
    result = runner.invoke(cli, opts, input=input_str)

    click.echo(" out ".center(80, "."))
    click.echo(result.output)
    from pprint import pprint

    pprint(prmreader.prms.Paths)
    click.echo(" conf-file ".center(80, "."))
    click.echo(init_file)
    click.echo()
    with init_file.open() as f:
        for line in f.readlines():
            click.echo(line.strip())


if __name__ == "__main__":
    click.echo("\n\n", " RUNNING MAIN PULL ".center(80, "*"), "\n")
    _main_pull()
    click.echo("ok")
