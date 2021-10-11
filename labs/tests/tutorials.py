import shutil
import os
from glob import glob
from pathlib import Path
from os import listdir
from os.path import isfile, join
import yaml
import re
import sys
from pprint import pprint

import nbformat
import nbconvert
from nbconvert.preprocessors import ClearOutputPreprocessor
from nbconvert.exporters import NotebookExporter
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert import RSTExporter, HTMLExporter
from nbparameterise import extract_parameters, parameter_values, replace_definitions
from nbconvert.nbconvertapp import NbConvertBase

from functools import partial
import builtins

script_path = os.path.abspath(__file__)
tests_dir, _ = os.path.split(script_path)
# set configuration options
RSTExporter.template_path = [tests_dir]
RSTExporter.template_file = 'rst_extended.tpl'
NbConvertBase.display_data_priority = [
    'application/vnd.jupyter.widget-state+json',
    'application/vnd.jupyter.widget-view+json',
    'application/javascript',
    'application/vnd.bokehjs_exec.v0+json',
    'text/html',
    'text/markdown',
    'image/svg+xml',
    'text/latex',
    'image/png',
    'image/jpeg',
    'text/plain'
]


output = []


def print(*args, **kwargs):
    """Overwrite print to allow recording of output."""
    builtins.print(*args, flush=True, **kwargs)
    output.append(' '.join(args))


class cd:
    """Context manager for changing current working directory.

    Args:
        path (str): The path to the directory to switch to.
    """
    def __init__(self, path):
        self.path = os.path.expanduser(path)

    def __enter__(self):
        self.saved_path = os.getcwd()
        os.chdir(self.path)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.saved_path)


def execute_notebook(nb_path, serial_number=None, baud=None, allow_errors=True, SCOPETYPE='OPENADC', PLATFORM='CWLITEARM', **kwargs):
    """Execute a notebook via nbconvert and collect output.
       :returns (parsed nb object, execution errors)
    """
    notebook_dir, file_name = os.path.split(nb_path)
    real_path = Path(nb_path).absolute()

    with open(real_path) as nbfile:
        nb = nbformat.read(nbfile, as_version=4)
        orig_parameters = extract_parameters(nb)
        params = parameter_values(orig_parameters, SCOPETYPE=SCOPETYPE, PLATFORM=PLATFORM, **kwargs)
        nb = replace_definitions(nb, params, execute=False)

        ep = ExecutePreprocessor(timeout=None, kernel_name='python3', allow_errors=allow_errors)

        if serial_number or baud:
            ip = InLineCodePreprocessor(notebook_dir)
            # inline all code before doing any replacements
            nb, resources = ip.preprocess(nb, {})

        replacements = {}

        if serial_number:
            replacements.update({
                r'cw.scope(\(\))': 'cw.scope(sn=\'{}\')'.format(serial_number),
                r'chipwhisperer.scope()': 'chipwhisperer.scope(sn=\'{}\')'.format(serial_number)
            })

        if baud:
            replacements.update({
                r'program_target\(((?:[\w=\+/*\s]+\s*,\s*)*[\w=+/*]+)': r"program_target(\g<1>, baud=38400"
            })

        # complete all regex subtitutions
        if replacements:
            rp = RegexReplacePreprocessor(replacements)
            nb, resources = rp.preprocess(nb, {})

        if notebook_dir:
            with cd(notebook_dir):
                nb, resources = ep.preprocess(nb, {'metadata': {'path': './'}})
        else:
            nb, resources = ep.preprocess(nb, {'metadata': {'path': './'}})

        errors = [[i + 1, output] for i, cell in enumerate(nb.cells) if "outputs" in cell
                  for output in cell["outputs"] \
                  if output.output_type == "error"]

        export_kwargs = {
            'SCOPETYPE': SCOPETYPE,
            'PLATFORM': PLATFORM
        }

        return nb, errors, export_kwargs


def export_notebook(nb, nb_path, output_dir, SCOPETYPE=None, PLATFORM=None):
    """Takes a notebook node and exports it to ReST and HTML

    Args:
        nb (notebook): The notebook returned by execute_notebook.
        nb_path (str): Path to intput notebook file. Used to generate the
            name of the output file.
        output_dir (str): The output directory for the ReST and HTML file.
        SCOPETYPE (str): Used to generate the output file name.
        PLATFORM (str): Used to generate the output file name.
    """
    notebook_dir, file_name = os.path.split(nb_path)
    file_name_root, _ = os.path.splitext(file_name)
    base_path = os.path.join(output_dir, file_name_root + "-{}-{}".format(SCOPETYPE, PLATFORM))
    rst_path = os.path.abspath(base_path + ".rst")
    html_path = os.path.abspath(base_path + ".html")

    with open(rst_path, "w", encoding='utf-8') as rst_file:
        rst_exporter = RSTExporter()

        body, res = rst_exporter.from_notebook_node(nb)

        rst_file.write(body)
        print('Wrote to: ', rst_path)

    with open(html_path, 'w', encoding='utf-8') as html_file:
        html_exporter = HTMLExporter()

        body, res = html_exporter.from_notebook_node(nb)

        html_file.write(body)
        print('Wrote to: ', html_path)


def _print_tracebacks(errors):
    # to escape ANSI sequences use regex
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    if errors == []:
        print("Passed all tests!")
    for error in errors:
        print("Test failed in cell {}: {}: {}".format(error[0], error[1]['ename'], error[1]['evalue']))
        for line in error[1]['traceback']:
            print(ansi_escape.sub('', line))


def _get_outputs(nb):
    return [[i, cell] for i, cell in enumerate(nb.cells) if "outputs" in cell]


def _print_stderr(nb):
    outputs = _get_outputs(nb)
    printed_output = [[cell[0], output] for cell in outputs for output in cell[1]['outputs'] if
                      ('name' in output and output['name'] == 'stderr')]
    for out in printed_output:
        print("[{}]:\n{}".format(out[0], out[1]['text']))


def _print_stdout(nb):
    outputs = _get_outputs(nb)
    printed_output = [[cell[0], output] for cell in outputs for output in cell[1]['outputs'] if
                      ('name' in output and output['name'] == 'stdout')]
    for out in printed_output:
        print("[{}]:\n{}".format(out[0], out[1]['text']))


def test_notebook(nb_path, output_dir, serial_number=None, export=True, allow_errors=True, print_first_traceback_only=True, print_stdout=False, print_stderr=False,
                  allowable_exceptions=None, baud=None, **kwargs):
    # reset output for next test
    output[:] = list()
    passed = False
    print()
    print("Testing: {}:...".format(os.path.abspath(nb_path)))
    print("with {}.".format(kwargs))
    if serial_number:
        print('on device with serial number {}.'.format(serial_number))
    else:
        print('No serial number specified... only bad if more than one device attached.')
    nb, errors, export_kwargs = execute_notebook(nb_path, serial_number, allow_errors=allow_errors, allowable_exceptions=allowable_exceptions, baud=baud, **kwargs)
    if not errors:
        print("PASSED")
        passed = True
        if export:
            export_notebook(nb, nb_path, output_dir, **export_kwargs)
    else:
        if allowable_exceptions:
            error_is_acceptable = [error[1]['ename'] in allowable_exceptions for error in errors]
            if all(error_is_acceptable):
                print("PASSED with expected errors")
                passed = True
                for error in errors:
                    print(error[1]['ename'], ':', error[1]['evalue'])
                if export:
                    export_notebook(nb, nb_path, output_dir, **export_kwargs)
            else:
                print("FAILED:")
                passed = False
                if print_first_traceback_only:
                    _print_tracebacks([error for i, error in enumerate(errors) if i == 0])
                else:
                    _print_tracebacks(errors)
        else:
            print("FAILED:")
            passed = False
            if print_first_traceback_only:
                _print_tracebacks([error for i, error in enumerate(errors) if i == 0])
            else:
                _print_tracebacks(errors)
    if print_stdout:
        _print_stdout(nb)
    if print_stderr:
        _print_stderr(nb)

    return passed, '\n'.join(output)


def clear_notebook(path):
    real_path = Path(path)
    body = ""
    with open(real_path, "r", encoding="utf-8") as nbfile:
        nb = nbformat.read(nbfile, as_version=4)
        orig_parameters = extract_parameters(nb)
        params = parameter_values(orig_parameters, SCOPETYPE="OPENADC", PLATFORM="CWLITEARM")
        new_nb = replace_definitions(nb, params, execute=False)
        co = ClearOutputPreprocessor()

        exporter = NotebookExporter()
        node, resources = co.preprocess(new_nb, {'metadata': {'path': './'}})
        body, resources = exporter.from_notebook_node(node, resources)
    with open(real_path, "w", encoding="utf-8") as nbfile:
        nbfile.write(body)


def clear_outputs_in_dir(dirpath):
    filter_list = ["Test_Notebook.ipynb", "PA_TVLA_1-Performing_TVLA_Testing_for_Crypto_Validation.ipynb",
                   "PA_Profiling_1_Template_Attacks_HW_Assumption.ipynb", "PA_Intro_3-Measuring_SNR_of_Target.ipynb",
                   "PA_HW_CW305.ipynb", "PA_CPA_4-Hardware_Crypto_Attack.ipynb", "Helpful_Code_Blocks.ipynb",
                   "!!Suggested_Completion_Order!!.ipynb", "Fault_4-AES_Differential_Fault_Analysis_Attacks.ipynb"]
    notebook_files = [f for f in listdir("./") if
                      (isfile(join("./", f)) and f.endswith(".ipynb") and f not in filter_list)]
    for file in notebook_files:
        print("Clearing {}".format(file))
        clear_notebook(file)


def load_configuration(path):
    """Load the yaml configuration file for the tutorials.

    Args:
        path (str): The path to the configuration file.

    Returns:
        (tuple) Length two tuple (tutorials (dict), connected_hardware (dict))
    """
    with open(path, 'r') as config_file:
        config = yaml.full_load(config_file)
    tutorials = config['tutorials']
    connected_hardware = config['connected']
    return tutorials, connected_hardware


def matching_connected_configuration(config, connected):
    """
    Args:
        config (dict): With at least keys: scope, and target.
        connected (list): List of connected hardware configurations.
            Each configuration is a dict with at least scope, and target
            as keys.

    Returns:
        tuple: (bool, dict) Whether a match was found, and second the matching attached
         configuration. Returns False and None if matching connected device was not found.
    """
    check_keys = [
        'scope',
        'target'
    ]

    for connected_config in connected:
        check = [config[key] == connected_config[key] for key in check_keys]
        if all(check):
            connected = connected_config
            return True, connected
    return False, None


class RegexReplacePreprocessor(nbconvert.preprocessors.Preprocessor):
    """Preprocessor for replacing matched regex strings in nb cells

    Each regex will be used and replaced by the replacement in the repl iterable.
    Pairs of regex, and replacement strings are selected by index.

    Args:
        replacements (dict): A dictionary with regex strings as keys and replacement
            strings as values.
    Returns:
        notebook, resources: The modified notebook, and resources with all replacements applied.
    """

    def __init__(self, replacements, **kw):
        try:
            self.replacement_pairs = [(re.compile(regex), repl) for regex, repl in replacements.items()]
        except re.error as e:
            print('One of the regex compile failed, invalid regex.')
            sys.exit(0)
        super().__init__(**kw)

    def preprocess_cell(self, cell, resources, index):
        if cell['cell_type'] == 'code':
            for p, repl in self.replacement_pairs:
                cell['source'] = re.sub(p, repl, cell['source'])
        return cell, resources


class InLineCodePreprocessor(nbconvert.preprocessors.Preprocessor):
    """Preprocessor that in lines code instead of using %run in nb.

    The %run command is not ideal for regex replacing code because
    the notebooks are external and not accesible with a preprocessor.
    This preprocessor takes any %run notebook.ipynb instance in a cell
    exports the externel notebook to python code and in lines that code
    into the cell before returning this cell.

    This preprocessor should be run before the RegexReplacePreProcessor
    so all instances in external notebooks that are now inline are also
    processed.

    Args:
        notebook_dir (str): The path to the directory containing all the
            notebooks. Used to resolve the relative paths used by the
            %run command.

    Returns:
        notebook, resources: The modified notebook, and resources with all
            instances of the %run command in lined.
    """

    def __init__(self, notebook_dir, **kwargs):
        self.notebook_dir = notebook_dir
        super().__init__(**kwargs)

    def preprocess_cell(self, cell, resources, index):
        if cell['cell_type'] == 'code':
            if '%run' in cell['source']:
                # to deal with other notebooks being called from the source notebook
                # find the notebooks and export to python code and replace
                # the current cell source code with that python code before
                # replacing instances of cw.scope()
                p = re.compile(r"(%run\s*[\"']?(.*\.ipynb)[\"']?)")
                external_notebooks = re.findall(p, cell['source'])
                for full_match, ext_nb in external_notebooks:
                    ext_nb_path = os.path.join(self.notebook_dir, ext_nb)
                    ext_nb_node = nbformat.read(ext_nb_path, as_version=4)
                    python_exporter = nbconvert.exporters.PythonExporter()
                    python_code, _ = python_exporter.from_notebook_node(ext_nb_node)
                    cell['source'] = cell['source'].replace(full_match, '\n{}\n'.format(python_code))
        return cell, resources


def run_tests(config):
    tutorials, connected_hardware = load_configuration(config)

    nb_dir = '..'
    output_dir = '../../tutorials/'

    # copy the images from input to output directory
    # keeping them in the same relative directory
    image_input_dir = os.path.join(nb_dir, 'img')
    image_output_dir = os.path.join(output_dir, 'img')

    if not os.path.isdir(image_output_dir):
        os.mkdir(image_output_dir)

    print('Copying over image files...', end='')
    for image_path in glob(os.path.join(image_input_dir, '*')):
        _, image_name = os.path.split(image_path)
        shutil.copyfile(image_path, os.path.join(image_output_dir, image_name))
    print('Done')

    # Run each on of the tutorials with each supported hardware
    # configuration for that tutorial and export the output
    # to the output directory.

    # to keep track of test name and output for email
    tests = {}

    # to keep track of number of fails/run
    summary = {}
    summary['all'] = {}
    summary['all']['failed'] = 0
    summary['all']['run'] = 0
    for nb in tutorials.keys():
        for test_config in tutorials[nb]['configurations']:
            match, matched_config = matching_connected_configuration(test_config, connected_hardware)
            serial_number = None
            if match:
                serial_number = matched_config.get('serial number')
                path = os.path.join(nb_dir, nb)

                kwargs = {
                    'SCOPETYPE': test_config['scope'],
                    'PLATFORM': test_config['target'],
                    'CRYPTO_TARGET': test_config['firmware'],
                }

                tutorial_specific_kwargs = tutorials[nb].get('kwargs')
                connected_config_kwargs = matched_config.get('kwargs')

                # The connected configuration kwargs can be overwritten by
                # tutorial specific_kwargs
                if connected_config_kwargs:
                    kwargs.update(connected_config_kwargs)

                if tutorial_specific_kwargs:
                    kwargs.update(tutorial_specific_kwargs)


                passed, output = test_notebook(nb_path=path, output_dir=output_dir, serial_number=serial_number,
                                               **kwargs)
                if not summary.get(test_config['target']):
                    summary[test_config['target']] = {}
                    summary[test_config['target']]['failed'] = 0
                    summary[test_config['target']]['run'] = 0

                if not passed:
                    summary[test_config['target']]['failed'] += 1
                    summary['all']['failed'] += 1

                summary[test_config['target']]['run'] += 1
                summary['all']['run'] += 1

                if passed:
                    header = 'PASSED: {} using {}'.format(nb, test_config['target'])
                else:
                    header = 'FAILED: {} using {}'.format(nb, test_config['target'])
                tests[header] = output

    # clean up the projects created by running the tutorial notebooks.
    try:
        shutil.rmtree('projects')
    except FileNotFoundError:
        pass

    return summary, tests


if __name__ == '__main__':
    script, config_file_path = sys.argv
    run_tests(config_file_path)