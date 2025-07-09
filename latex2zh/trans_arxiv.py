from latex2zh.latex_process import patch_tex_bibliography
from . import utils
from . import latex_process
from . import file_process
from .translatex import translate_single_tex_file
from .encode_process import get_file_encoding
from . import app_dir
import os
import sys
import shutil
import gzip
import zipfile
import tarfile
import tempfile
import urllib.request
from types import SimpleNamespace



def download_source(number, path):
    url = f'https://arxiv.org/e-print/{number}'
    print('trying to download from', url)
    urllib.request.urlretrieve(url, path)


def download_source_with_cache(number, path):
    cache_dir = os.path.join(app_dir, 'cache_arxiv')
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, 'last_downloaded_source')
    cache_number_path = os.path.join(cache_dir, 'last_arxiv_number')
    if os.path.exists(cache_path) and os.path.exists(cache_number_path):
        last_number = open(cache_number_path).read()
        if last_number == number:
            shutil.copyfile(cache_path, path)
            return
    download_source(number, path)
    shutil.copyfile(path, cache_path)
    open(cache_number_path, 'w').write(number)


def is_pdf(filename):
    return open(filename, 'rb').readline()[0:4] == b'%PDF'


def loop_files(dir):
    all_files = []
    for root, dirs, files in os.walk(dir):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files


def zipdir(dir, output_path):
    # ziph is zipfile handle
    zipf = zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED)
    for file in loop_files(dir):
        rel_path = os.path.relpath(file, dir)
        zipf.write(file, arcname=rel_path)


def translate_dir(dir, options):
    files = loop_files(dir)
    texs = [f[0:-4] for f in files if f.endswith('.tex')]
    bibs = [f[0:-4] for f in files if f.endswith('.bib')]
    bbls = [f[0:-4] for f in files if f.endswith('.bbl')]
    no_bib = len(bibs) == 0
    print('main tex files found:')
    complete_texs = []

    for tex in texs:
        path = f'{tex}.tex'
        input_encoding = get_file_encoding(path)
        content = open(path, encoding=input_encoding).read()
        content = latex_process.remove_tex_comments(content)
        complete = latex_process.is_complete(content)
        if complete:
            print(path)

            if no_bib and (tex in bbls):
                patch_tex_bibliography(f"{tex}.tex", tex)

            file_process.merge_complete(tex)

            if no_bib and (tex in bbls):
                file_process.add_bbl(tex)

            complete_texs.append(tex)

    if len(complete_texs) == 0:
        return False

    for basename in texs:
        if basename in complete_texs:
            continue
        os.remove(f'{basename}.tex')
    for basename in bbls:
        os.remove(f'{basename}.bbl')

    if options.notranslate:
        return True

    for filename in complete_texs:
        print(f'Processing {filename}')
        file_path = f'{filename}.tex'
        translate_single_tex_file(
            file_path,
            file_path,
            options.engine,
            options.l_from,
            options.l_to,
            options.debug,
            options.nocache,
            options.threads
        )
    return True


#Encapsulated as a function
def translate_arxiv_file(
    number,
    output_path=None,
    subdir=None,
    engine=None,
    lang_from=None,
    lang_to=None,
    debug=False,
    nocache=False,
    threads=4,
    overwrite=False,
    compile_pdf=True):


    print('arxiv number:', number)

    subdir = subdir if subdir else number.replace('/', '-')
    output_base = os.path.join("output", subdir)
    os.makedirs(output_base, exist_ok=True)

    zip_output_path = output_path if output_path else f'output/{subdir}.zip'
    pdf_path = os.path.join(output_base, "main.pdf")

    success = True
    cwd = os.getcwd()

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            print('temporary directory', temp_dir)

            os.chdir(temp_dir)

            if os.path.isdir(number):
                shutil.copytree(number, temp_dir, dirs_exist_ok=True)
            else:
                try:
                    download_source_with_cache(number, "downloaded")
                except Exception as e:
                    print(' Cannot download source. Check network or arXiv ID.')
                    return None

                if is_pdf("downloaded"):
                    print("Only PDF available. Cannot process.")
                    return None

                try:
                    content = gzip.decompress(open("downloaded", "rb").read())
                    with open("downloaded", "wb") as f:
                        f.write(content)
                except Exception as e:
                    print(f" Error decompressing downloaded file: {e}")
                    return None

                try:
                    with tarfile.open("downloaded", mode='r') as tar:
                        tar.extractall()
                    os.remove("downloaded")
                except tarfile.ReadError:
                    print(' This is a pure text file. Renaming to main.tex.')
                    shutil.move("downloaded", 'main.tex')


            options = {
                "engine": engine,
                "l_from": lang_from,
                "l_to": lang_to,
                "debug": debug,
                "nocache": nocache,
                "threads": threads,
                "overwrite": overwrite,
                "notranslate": False,
            }


            options = SimpleNamespace(**options)

            success = translate_dir('.', options)
            os.chdir(cwd)

            if success:
                for fname in os.listdir(temp_dir):
                    src = os.path.join(temp_dir, fname)
                    dst = os.path.join(output_base, fname)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)


                tex_files = [f for f in os.listdir(output_base) if f.endswith('.tex')]
                assert len(tex_files) == 1

                main_filename = tex_files[0]
                main_basename = os.path.splitext(main_filename)[0]
                main_tex_path = os.path.join(output_base, main_filename)

                if compile_pdf and os.path.exists(main_tex_path):
                    print(f" Compiling {main_filename} using XeLaTeX...")
                    os.chdir(output_base)

                    pdf_path = os.path.join(output_base, f"{main_basename}.pdf")

                    os.system(f'xelatex -interaction=nonstopmode {main_basename}.tex')

                    bib_files = [f for f in os.listdir('.') if f.endswith('.bib')]
                    bbl_files = [f for f in os.listdir('.') if f.endswith('.bbl')]

                    if bib_files:
                        print(" Running bibtex on all bib entries...")

                        aux_files = [f for f in os.listdir('.') if f.endswith('.aux')]
                        for aux in aux_files:
                            base = os.path.splitext(aux)[0]
                            if os.path.exists(aux):
                                print(f"  -> bibtex {base}")
                                os.system(f"bibtex {base}")
                    elif bbl_files:
                        print(" .bbl file(s) detected, skipping bibtex.")
                    else:
                        print(" No .bib or .bbl file found. Skipping bibliography phase.")


                    os.system(f'xelatex -interaction=nonstopmode {main_basename}.tex')
                    os.system(f'xelatex -interaction=nonstopmode {main_basename}.tex')

                    os.chdir(cwd)


    except Exception as e:
        print(f" Exception occurred during translation: {e}")
        os.chdir(cwd)
        return None

    if success and os.path.exists(pdf_path):
        print(' Translation succeeded.')
        print(' Zip file saved to:', zip_output_path)
        print(' PDF saved to:', pdf_path)
        return pdf_path
    else:
        print(' Translation failed or PDF not generated.')
        return None


