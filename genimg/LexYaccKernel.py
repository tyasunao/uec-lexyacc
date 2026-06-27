from ipykernel.kernelbase import Kernel
import subprocess
import tempfile
import pexpect
import shutil
import shlex
import traceback

class LexYaccKernel(Kernel):
    implementation = 'lex yacc'
    implementation_version = '1.0'
    language = 'lex yacc'
    language_info = {'name': 'lex yacc',
                     'mimetype': 'text/plain'
    }
    banner = "Lex Yacc kernel.\n" \
             "Uses flex, bison and gcc\n"

    def __init__(self, *args, **kwargs):
        super(LexYaccKernel, self).__init__(*args, **kwargs)
        self.files = []
        # mastertemp = tempfile.mkstemp()
        # self.master_path = mastertemp[1]
        # filepath = path.dirname(path.realpath(__file__))
        # subprocess.call(['lex', filepath])

    # def cleanup_files(self):
    #    """Remove all the temporary files created by the kernel"""
    #    for file in self.files:
    #        os.remove(file)
    #     os.remove(self.master_path)



    def new_temp_file(self, **kwargs):
        """Create a new temp file to be deleted when the kernel shuts down"""
        # We don't want the file to be deleted when closed, but only when the kernel stops
        kwargs['delete'] = False
        kwargs['mode'] = 'w'
        file = tempfile.NamedTemporaryFile(**kwargs)
        self.files.append(file.name)
        return file

    def _to_text(self, contents):
        if isinstance(contents, bytes):
            return contents.decode('utf-8', errors='replace')
        return str(contents)

    def _write_to_stdout(self, contents):
        self.send_response(
            self.iopub_socket,
            'stream',
            {'name': 'stdout', 'text': self._to_text(contents)}
        )

    def _write_to_stderr(self, contents):
        self.send_response(
            self.iopub_socket,
            'stream',
            {'name': 'stderr', 'text': self._to_text(contents)}
        )

    def create_jupyter_subprocess(self, cmd):
        """Run a command, then send the complete stdout/stderr to the notebook."""
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
            )
        except FileNotFoundError:
            result = subprocess.CompletedProcess(
                cmd,
                127,
                '',
                '[Kernel] command not found: {}\n'.format(cmd[0]),
            )
        except Exception as e:
            result = subprocess.CompletedProcess(
                cmd,
                1,
                '',
                '[Kernel] failed to run {}: {}\n'.format(shlex.join(cmd), e),
            )

        if result.stdout:
            self._write_to_stdout(result.stdout)
        if result.stderr:
            self._write_to_stderr(result.stderr)

        return result

    def compile_with_lex(self, source_filename, options=None):
        options = options or []
        args = ['lex'] + options + [source_filename]
        return self.create_jupyter_subprocess(args)
    
    def compile_with_yacc(self, source_filename, options=None):
        options = options or []
        args = ['yacc', '-Wcounterexamples'] + options + [source_filename]
        return self.create_jupyter_subprocess(args)

    def compile_with_gcc(self, source_filename, options=None):
        options = options or []
        args = ['gcc', source_filename] + options + ['-w', '-ll', '-ly']
        return self.create_jupyter_subprocess(args)

    def compile_asm(self, source_filename):
        args = ['cc', '-no-pie', '-z', 'execstack', source_filename]
        return self.create_jupyter_subprocess(args)

    def _ok(self):
        return {
            'status': 'ok',
            'execution_count': self.execution_count,
            'payload': [],
            'user_expressions': {}
        }

    def _error(self, ename, evalue, traceback_lines=None):
        return {
            'status': 'error',
            'execution_count': self.execution_count,
            'ename': ename,
            'evalue': evalue,
            'traceback': traceback_lines or [evalue],
        }

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        try:
            return self._do_execute_impl(
                code,
                silent,
                store_history,
                user_expressions,
                allow_stdin,
            )
        except Exception:
            tb = traceback.format_exc()
            self._write_to_stderr('[Kernel] internal error:\n' + tb)
            return self._error(
                'KernelInternalError',
                'Unhandled exception in LexYaccKernel',
                tb.splitlines(),
            )
            
    def _do_execute_impl(self, code, silent, store_history=True,
                         user_expressions=None, allow_stdin=False):
        lines = code.splitlines()
        if not lines:
            return self._ok()
        
        if lines[0].startswith('/*') and lines[0].endswith('*/'):
            command = lines[0].split()[1]
            if command == 'lex':
                filename = lines[0].split()[2]
                options = lines[0].split()[3:-1]

                with open(filename, 'w') as f:
                    f.write('\n'.join(lines[1:]) + '\n')
                    f.flush()
                    p = self.compile_with_lex(f.name, options)
                    if p.returncode != 0:
                        self._write_to_stderr("[Lex] flex exited with code {}\n".format(p.returncode))
                    else:
                        self._write_to_stdout("[Lex] flex generates lex.yy.c successfully\n")
            elif command == 'yacc':
                filename = lines[0].split()[2]
                options = lines[0].split()[3:-1]
                with open(filename, 'w') as f:
                    f.write('\n'.join(lines[1:]) + '\n')
                    f.flush()
                    p = self.compile_with_yacc(f.name, options)
                    if p.returncode != 0:
                        self._write_to_stderr("[Yacc] bison exited with code {}\n".format(p.returncode))
                    else:
                        self._write_to_stdout("[Yacc] bison generates y.tab.c successfully\n")
            elif command == 'c':
                filename = lines[0].split()[2]
                options = lines[0].split()[3:-1]
                with open(filename, 'w') as f:
                    f.write('\n'.join(lines[1:]) + '\n')
                    f.flush()
                    p = self.compile_with_gcc(f.name, options)
                    if p.returncode != 0:
                        self._write_to_stderr("[C] gcc exited with code {}\n".format(p.returncode))
                    else:
                        self._write_to_stdout("[C] gcc generates a.out successfully\n")
            elif command == 'a.out':
                try :
                    p = pexpect.spawn('./a.out')
                except Exception as e:
                    self._write_to_stderr("[A.OUT] Error: a.out not found")
                    return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [],
                            'user_expressions': {}}
                    
                for line in lines[1:]:
                    p.sendline(line)
                p.sendeof()
                p.expect(pexpect.EOF)
                output_lines = p.before.decode().split('\n')
                i = 1
                diff = []
                for line in output_lines:
                    if i < len(lines) and lines[i].strip() == line.strip():
                        i = i + 1
                    else:
                        diff.append(line)

                self._write_to_stdout('\n'.join(diff))
                p.close()
            elif command == 'uecc':
                try :
                    shutil.copy('./a.out', './uecc')
                except Exception as e:
                    self._write_to_stderr("[UECC] Error: a.out not found")
                    return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [],
                            'user_expressions': {}}
                    
                filename = lines[0].split()[2]
                with open(filename, 'w') as f:
                    f.write('\n'.join(lines[1:]) + '\n')
                    f.flush()
                    p = pexpect.spawn('./uecc')
                    for line in lines[1:]:
                        p.sendline(line)
                    p.sendeof()
                    p.expect(pexpect.EOF)
                    output_lines = p.before.decode().split('\n')
                    i = 1
                    diff = []
                    for line in output_lines:
                        if i < len(lines) and lines[i].strip() == line.strip():
                            i = i + 1
                        else:
                            diff.append(line)
                    if p.isalive():
                        p.wait()

                    if p.exitstatus != 0:
                        self._write_to_stderr("[UECC] uecc exited with code {}".format(p.exitstatus))
                        return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [],
                                'user_expressions': {}}
                        
                    self._write_to_stdout('\n'.join(diff))
                    
                    with open(filename + '.s', 'w') as f2:
                        f2.write('\n'.join(diff))
                    with open(filename + '.s', 'r') as f2:
                        p2 = self.compile_asm(filename + '.s')
                        if p2.returncode != 0:
                            self._write_to_stderr("[UECC] cc exited with code {}\n".format(p2.returncode))
                        else:
                            self._write_to_stdout("[UECC] cc generates a.out successfully\n")
            else:
                self._write_to_stderr("[Kernel] Error: The code must be start with /* and the format is [/* (lex|yacc|c|uecc) filename */] or [/* a.out */]")
        else:
            self._write_to_stderr("[Kernel] Error: The code must start with '/*' and the format is [/* (lex|yacc|c|uecc) filename */] or [/* a.out */]")
        
        return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [],
                'user_expressions': {}}

    def do_shutdown(self, restart):
        """Cleanup the created source code files and executables when shutting down the kernel"""
        # self.cleanup_files()
        pass
        
if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=LexYaccKernel)
