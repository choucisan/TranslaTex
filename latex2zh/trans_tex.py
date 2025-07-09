#!/usr/bin/env python
import os
from .translatex import translate_single_tex_file
import subprocess


#Encapsulated as a function
def translate_tex_file(
    input_path,
    output_path=None,
    subdir=None,
    engine=None,
    lang_from=None,
    lang_to=None,
    debug=False,
    nocache=False,
    threads=4,
    overwrite=False,
    compile_pdf=True
):
    """
    Translate a LaTeX .tex file and optionally compile it to PDF.

    Returns:
        (output_tex_path, pdf_path): paths to translated .tex and compiled PDF (if enabled)
    """
    input_filename = os.path.splitext(os.path.basename(input_path))[0]
    subdir_name = subdir or input_filename
    output_dir = os.path.join("output", subdir_name)
    os.makedirs(output_dir, exist_ok=True)

    output_tex_path = output_path or os.path.join(output_dir, input_filename + ".tex")

    if os.path.abspath(input_path) == os.path.abspath(output_tex_path) and not overwrite:
        raise ValueError(f"[Error] Will overwrite input file: {output_tex_path}. "
                         f"Use overwrite=True to allow.")


    translate_single_tex_file(
        input_path=input_path,
        output_path=output_tex_path,
        engine=engine,
        l_from=lang_from,
        l_to=lang_to,
        debug=debug,
        nocache=nocache,
        threads=threads,
    )

    pdf_path = None
    if compile_pdf:
        try:
            cwd = os.getcwd()
            os.chdir(output_dir)

            tex_filename = os.path.basename(output_tex_path)
            result = subprocess.run(
                ["xelatex", "-interaction=nonstopmode", tex_filename],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            pdf_path = os.path.join(output_dir, input_filename + ".pdf")
            if not os.path.exists(pdf_path):
                raise RuntimeError(result.stderr.decode() or "PDF not generated.")

        except Exception as e:
            print(f"[Error] PDF compilation failed: {e}")
        finally:
            os.chdir(cwd)

    return output_tex_path, pdf_path



