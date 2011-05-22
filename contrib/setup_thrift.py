from distutils.core import Command
from distutils.dist import Distribution
from distutils.command.build import build as _build
from distutils.errors import DistutilsFileError
from distutils.spawn import spawn
from distutils.util import execute
from distutils.dir_util import copy_tree, remove_tree

import os.path

class build(_build):
  """
  Subclass of distutils' "build" command that supports building thrift
  """
  def has_thrift(self):
    cmd = self.distribution.get_command_obj('build_thrift')
    if cmd is not None:
      return len(cmd.thrift_idls) > 0
    return False

  sub_commands = [('build_clib',    _build.has_c_libraries),
                  ('build_ext',     _build.has_ext_modules),
                  ('build_scripts', _build.has_scripts),
                  ('build_thrift',  has_thrift),
                  ('build_py',      _build.has_pure_modules),
                 ]


class build_thrift(Command):
  description = "\"build\" Python thrift bindings"

  def initialize_options(self):
    self.build_lib = None
    self.thrift_idls = []

  def finalize_options(self):
    self.set_undefined_options('build',
                               ('build_lib', 'build_lib'))

  def run(self):
    if self.thrift_idls:
      self.build_idls()

  def build_idls(self):
    for idl in self.thrift_idls:
      self.build_idl(idl)

  def build_idl(self, path):
    path = self.get_idl_path(path)
    if not os.path.isfile(path):
      raise DistutilsFileError('Unable to find idl file, "%s"' %
                               (path, ))

    # XXX "find" thrift instead of hardcoding the path here
    command = ['/usr/local/bin/thrift',
               '--gen', 'py',
               '-r',
               '-o', self.build_lib,
               path]

    spawn(command, dry_run=self.dry_run)
    
    # thrift puts everything in a gen-py folder... That's lame; let's
    # dump it into the buildroot instead.
    gen_path = os.path.join(self.build_lib, 'gen-py')
    for item in os.listdir(gen_path):
      src =os.path.join(gen_path, item)
      dst = os.path.join(self.build_lib, item)

      # Skip move of __init__.py files if there are already ones in the
      # build dir.  In that case, just delete them.
      if item == '__init__.py' and os.path.isfile(dst):
        execute(os.remove, (src, ), "skipping copy of %s" % dst,
                dry_run=self.dry_run)
        continue

      # Target directory already copy files into it.. and then remove
      # the old tree.
      if os.path.isdir(src):

        # After we worked so hard to not stomp the __init__.py up above,
        # We stomp everything already in the subtree... *sigh*.  We should
        # probably write our own copy_tree() at some point
        copy_tree(src, dst, dry_run=self.dry_run)
        remove_tree(src, dry_run=self.dry_run)
        continue

      # Target dir or file doesn't exist yet.  Just move it
      self.move_file(src, dst, dry_run=self.dry_run)
                     

    execute(os.rmdir, (gen_path, ), "cleaning up %s" % gen_path,
            dry_run=self.dry_run)

    

  def get_idl_path(self, idl_path):
    return idl_path


class ThriftDistribution(Distribution):
  """
  Subclass of distutils' Distribution class that supports thrift
  """
  def has_thrift():
    return self.scripts and len(self.scripts) > 0

  def get_command_class(self, command):
    if command == 'build':
      return build
    elif command == 'build_thrift':
      return build_thrift
    return Distribution.get_command_class(self, command)
