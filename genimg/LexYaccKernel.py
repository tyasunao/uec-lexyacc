from queue import Queue
from threading import Thread

from ipykernel.kernelbase import Kernel
import subprocess
import tempfile
import pexpect
import shutil

class RealTimeSubprocess(subprocess.Popen):
    """
    A subprocess that allows to read its stdout and stderr in real time
    """

    def __init__(self, cmd, write_to_stdout, write_to_stderr):
        """
        :param cmd: the command to execute
        :param write_to_stdout: a callable that will be called with chunks of data from stdout
        :param write_to_stderr: a callable that will be called with chunks of data from stderr
        """
        self._write_to_stdout = write_to_stdout
        self._write_to_stderr = write_to_stderr

        super().__init__(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)

        self._stdout_queue = Queue()
        self._stdout_thread = Thread(target=RealTimeSubprocess._enqueue_output, args=(self.stdout, self._stdout_queue))
        self._stdout_thread.daemon = True
        self._stdout_thread.start()

        self._stderr_queue = Queue()
        self._stderr_thread = Thread(target=RealTimeSubprocess._enqueue_output, args=(self.stderr, self._stderr_queue))
        self._stderr_thread.daemon = True
        self._stderr_thread.start()

    @staticmethod
    def _enqueue_output(stream, queue):
        """
        Add chunks of data from a stream to a queue until the stream is empty.
        """
        for line in iter(lambda: stream.read(4096), b''):
            queue.put(line)
        stream.close()

    def write_contents(self):
        """
        Write the available content from stdin and stderr where specified when the instance was created
        :return:
        """

        def read_all_from_queue(queue):
            res = b''
            size = queue.qsize()
            while size != 0:
                res += queue.get_nowait()
                size -= 1
            return res

        stdout_contents = read_all_from_queue(self._stdout_queue)
        if stdout_contents:
            self._write_to_stdout(stdout_contents)
        stderr_contents = read_all_from_queue(self._stderr_queue)
        if stderr_contents:
            self._write_to_stderr(stderr_contents)


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

    def _write_to_stdout(self, contents):
        self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': contents})

    def _write_to_stderr(self, contents):
        self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': contents})

    def create_jupyter_subprocess(self, cmd):
        return RealTimeSubprocess(cmd,
                                  lambda contents: self._write_to_stdout(contents.decode()),
                                  lambda contents: self._write_to_stderr(contents.decode()))

    def compile_with_lex(self, source_filename, options=[]):
        args = ['lex'] + options + [source_filename]
        return self.create_jupyter_subprocess(args)
    
    def compile_with_yacc(self, source_filename, options=[]):
        args = ['yacc', source_filename, "-Wcounterexamples"] + options
        return self.create_jupyter_subprocess(args)

    def compile_with_gcc(self, source_filename, options=[]):
        args = ['gcc', source_filename] + options + ['-w', '-ll', '-ly']
        return self.create_jupyter_subprocess(args)
    def compile_asm(self, source_filename):
        args = ['cc', '-no-pie', '-z', 'execstack', source_filename]
        return self.create_jupyter_subprocess(args)


    def do_execute(self, code, silent, store_history=True,
                    user_expressions=None, allow_stdin=False):

        lines = code.splitlines()
        if lines[0].startswith('/*') and lines[0].endswith('*/'):
            command = lines[0].split()[1]
            if command == 'lex':
                filename = lines[0].split()[2]
                options = lines[0].split()[3:-1]

                with open(filename, 'w') as f:
                    f.write('\n'.join(lines[1:]) + '\n')
                    f.flush()
                    p = self.compile_with_lex(f.name, options)
                    while p.poll() is None:
                        p.write_contents()
                    if p.returncode != 0:
                        self._write_to_stderr("[Lex] flex exited with code {}".format(p.returncode))
                    else:
                        self._write_to_stdout("[Lex] flex generates lex.yy.c successfully")
            elif command == 'yacc':
                filename = lines[0].split()[2]
                options = lines[0].split()[3:-1]
                with open(filename, 'w') as f:
                    f.write('\n'.join(lines[1:]) + '\n')
                    f.flush()
                    p = self.compile_with_yacc(f.name, options)
                    while p.poll() is None:
                        p.write_contents()
                    if p.returncode != 0:
                        self._write_to_stderr("[Yacc] bison exited with code {}".format(p.returncode))
                    else:
                        self._write_to_stdout("[Yacc] bison generates y.tab.c successfully")
            elif command == 'c':
                filename = lines[0].split()[2]
                options = lines[0].split()[3:-1]
                with open(filename, 'w') as f:
                    f.write('\n'.join(lines[1:]) + '\n')
                    f.flush()
                    p = self.compile_with_gcc(f.name, options)
                    while p.poll() is None:
                        p.write_contents()
                    if p.returncode != 0:
                        self._write_to_stderr("[C] gcc exited with code {}".format(p.returncode))
                    else:
                        self._write_to_stdout("[C] gcc generates a.out successfully")
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
                    '''
                    if p.exitstatus != 0:
                        self._write_to_stderr("[UECC] uecc exited with code {}".format(p.exitstatus))
                        return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [],
                                'user_expressions': {}}
                    '''
                        
                    self._write_to_stdout('\n'.join(diff))
                    
                    with open(filename + '.s', 'w') as f2:
                        f2.write('\n'.join(diff))
                    with open(filename + '.s', 'r') as f2:
                        p2 = self.compile_asm(filename + '.s')
                        while p2.poll() is None:
                            p2.write_contents()
                        if p2.returncode != 0:
                            self._write_to_stderr("[UECC] cc exited with code {}".format(p2.returncode))
                        else:
                            self._write_to_stdout("[UECC] cc generates a.out successfully")
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
