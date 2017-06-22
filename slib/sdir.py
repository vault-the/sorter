#! /usr/bin/env python3

import os
import shutil
import re
import hashlib
import ctypes
from glob import iglob
from data.filegroups import typeGroups, typeList
from data.settings import SORTER_IGNORE_FILENAME


def has_signore_file(path, filename=SORTER_IGNORE_FILENAME):
    try:
        open(os.path.join(path, filename), 'r').close()
    except FileNotFoundError:
        return False
    else:
        return True


class Directory(object):
    """Define a directory instance - a file or folder.

    Methods:
    in_hidden_path
    has_hidden_attribute

    Attributes:
    path - The absolute path to the Directory instance
    name - The file/folder name inclusive of the extension (if any).
    parent - The parent folder.
    hidden_path - Boolean value determining whether the Directory instance
        occurs in a path where one of the folders is hidden.
    """

    def __init__(self, path):
        self._path = os.path.abspath(path)
        self._name = os.path.basename(self.path)
        self._parent = os.path.dirname(self.path)
        self._hidden_path = self.in_hidden_path(self.path)

    @property
    def path(self):
        return self._get_path()

    @path.setter
    def path(self, value):
        self._set_path(value)

    @property
    def name(self):
        return self._name

    @property
    def parent(self):
        return self._parent

    @property
    def hidden_path(self):
        return self._hidden_path

    def _get_path(self):
        return self._path

    def _set_path(self, value):
        self._path = value
        self._name = os.path.basename(self.path)
        self._parent = os.path.dirname(self.path)
        self._hidden_path = self.in_hidden_path(self.path)

    def in_hidden_path(self, full_path):
        paths = full_path.split(os.sep)

        if os.name == 'nt':
            for i in range(len(paths) + 1):
                path = str(os.sep).join(paths[:i])
                if self.has_hidden_attribute(path):
                    return True
        else:
            for i in range(len(paths) + 1):
                path = str(os.sep).join(paths[:i])
                base_name = os.path.basename(path)
                if base_name.startswith('.') or base_name.startswith('__'):
                    return True

        return False

    def has_hidden_attribute(self, filepath):
        """For Windows Systems, return True is attribute 'hidden' is set."""
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(filepath))
            assert attrs != -1
            result = bool(attrs & 2)
        except (AttributeError, AssertionError):
            result = False

        return result


class File(Directory):
    """A file instance.

    Inherits from Directory.

    Methods:
    get_category
    find_suitable_name
    move_to

    Attributes:
    extension - The file extension (mp4, mp3, etc)
    category - The category to which the file belongs as defined in filegroups.py
        (image, document, etc)
    exists - Boolean value determined by os.path.isdir()

    This class does not validate whether the given path is a file or a folder.
    Folders may be accepted during instantiation but the object may not function
    as intended.
    """

    filename_pattern = re.compile(r'\-\sdup[\s\(\d\)]+')

    def __init__(self, path):
        super(File, self).__init__(path)
        self._extension = self._get_extension()
        self._category = self.get_category(self.extension)
        self._exists = os.path.isfile(self.path)

    @property
    def extension(self):
        return self._extension

    @property
    def category(self):
        return self._category

    @property
    def exists(self):
        return self._exists

    def _set_path(self, value):
        super(File, self)._set_path(value)
        self._extension = self._get_extension()
        self._category = self.get_category(self.extension)
        self._exists = os.path.isfile(self.path)

    def _get_extension(self):
        extension = 'undefined'
        result = os.path.splitext(self.name)[1][1:]
        if result:
            extension = result
        return extension

    def get_category(self, extension):
        """Return the category of the file instance as determined by its extension.

        Categories are determined in filegroups.py
        """
        if extension:
            file_extension = extension.upper()
            for key in typeGroups.keys():
                common = set(typeGroups[key]) & set([file_extension])
                if common:
                    return key
        return 'UNDEFINED'

    def find_suitable_name(self, file_path, count=1):
        """Validate whether a file with the same name exists, return a name
        indicating that it is a duplicate, else return the given file name.

        A fix is provided in case file renaming errors occur. Check comments.
        """
        filename = os.path.basename(file_path)
        # Fix when renaming errors occusr
        # fix_filename = re.sub(r'[\-\s]*dup[\s\(\d\)\-]+', '', filename)
        # filename = fix_filename
        # Things happen :P
        if os.path.exists(file_path):
            split_data = os.path.splitext(filename)
            new_filename = ''
            if count == 1:
                new_filename = '{0} - dup ({1}){2}'.format(
                    split_data[0], count, split_data[1])
            else:
                sub_value = '- dup (%s)' % count
                new_filename = re.sub(
                    self.filename_pattern, sub_value, filename)

            new_file_path = os.path.join(
                os.path.dirname(file_path), new_filename)
            count += 1
            try:
                filename = self.find_suitable_name(new_file_path, count)
            except RuntimeError:
                filename = hashlib.md5(filename.encode('utf-8')).hexdigest()
        return filename

    def _set_extension_destination(self, root_path, group):
        if group:
            group_dst = os.path.join(root_path, self.category)

            if not os.path.isdir(group_dst):
                os.mkdir(group_dst)
            extension_dst = os.path.join(group_dst, self.extension.upper())
        else:
            extension_dst = os.path.join(root_path, self.extension.upper())

        if not os.path.isdir(extension_dst):
            os.mkdir(extension_dst)
        new_dst = os.path.join(extension_dst, self.name)
        suitable_name = self.find_suitable_name(new_dst)
        final_dst = os.path.join(os.path.dirname(new_dst),
                                 suitable_name)

        return final_dst

    def move_to(self, dst_root_path, group=False):
        """Move the file instance to a location relative to the 
        specified dst_root_path.

        dst_root_path is the root folder from where files will be organised
        by their extension.

        If dst_root_path = '/home/User/'
        final destination may be 
            '/home/User/<extension>/<filename>'

            or

            '/home/User/<category>/<extension>/<filename>'
        """
        final_destination = self._set_extension_destination(
            dst_root_path, group)
        if not os.path.dirname(self.path) == os.path.dirname(final_destination):
            try:
                shutil.move(self.path, final_destination)
            except PermissionError as e:
                print('Could not move "{0}": {1}'.format(self.path, e))
            else:
                self.path = final_destination


class Folder(Directory):
    """Define a folder instance.

    Inherits from Directory.

    Methods:
    is_sorter_folder
    group

    Attributes:
    exists - Boolean value determined by os.path.isdir()
    for_sorter - Boolean value determining whether the folder is generated by 
        Sorter (True) or not (False).
    category_folder - Category to which the folder should be moved to 
        as determined by filegroups.py and the name of the folder. This is 
        just the name, not the full path.

    This class does not validate whether the given path is a file or not.
    Folder.exists may return False when a file is provided but the other 
    methods and attributes may not behave as expected.
    """

    def __init__(self, path):
        super(Folder, self).__init__(path)
        self._exists = os.path.isdir(self.path)
        self._for_sorter = self.is_sorter_folder(self.path)
        self._category_folder = ''

    @property
    def exists(self):
        return self._exists

    @property
    def for_sorter(self):
        return self._for_sorter

    def _set_path(self, value):
        super(Folder, self)._set_path(value)
        self._exists = os.path.isdir(self.path)
        self._for_sorter = self.is_sorter_folder(self.path)
        self._category_folder = ''

    def is_sorter_folder(self, path):
        """Return True if Folder instance was generated by Sorter, else False."""
        if os.path.isdir(path):
            dirname = os.path.basename(path)
            if dirname.isupper():
                if dirname in typeList or dirname == 'FOLDERS':
                    return True
            else:
                if dirname in typeGroups.keys():
                    return True

        return False

    def _get_category_folder(self):
        # category folder is not full path
        if self.for_sorter:
            if self.name.upper() in typeList:
                category = [key for key in typeGroups.keys() if set(
                    typeGroups[key]) & set([self.name])][0]
                return os.path.join(category, self.name.upper())
            if self.name in typeGroups.keys():
                return os.path.basename(self.parent)

        return 'FOLDERS'

    def group(self, root_path):
        """Move folder to a location as determined by its category.

        Categories are defined in filegroups.py.
        # root_path is provided by user
        # root_path should be absoluted path
        # if folder is not a sorter folder (e.g. developer, PDF)
            move to category folder == FOLDERS.
        # if folder is a sorter folder (eg developer, PDF)
            move to category folder.
        """
        dst = os.path.join(root_path, self._get_category_folder())
        self._move_to(dst, root_path, group_content=True)

    def _move_to(self, dst, root_path, src=None, group_content=False):
        """Move the folder instance to a location relative to the 
        specified dst_root_path.

        src and dst should be absolute paths
        If src is not provided, the value of self.path is used.
        dst is the intended destination.
        root_path is the root folder from where files will be organised
        by their extension.
        Will not delete any folder that has contents in it.
        """
        if src is None:
            src = self.path

        if os.path.isdir(dst):
            self._move_contents(src, dst, root_path, group_content)
            try:
                os.rmdir(src)
            except OSError:
                print('Could not delete "%s". May contain hidden files.' % src)

        else:
            self.recreate(dst)
            shutil.move(src, dst)
        self.path = dst

    def _move_contents(self, src, dst, root_path, group_content=False):
        # move contents of src to dst
        # ignore folders
        files = [content for content in iglob(
            os.path.join(src, '*')) if os.path.isfile(content)]
        if files:
            for file_ in files:
                file_instance = File(os.path.join(src, file_))
                file_instance.move_to(
                    dst_root_path=root_path, group=group_content)

    def recreate(self, path=None):
        """Recreate folders (and parents) in the instance's path 
        if they do not exist."""

        full_path = path or self.path
        os.makedirs(full_path, exist_ok=True)
        if path is None:
            self.path = self.path


class CustomFolder(Folder):
    """Define a Folder instance with custom attributes.

    Inherits from Folder.

    Methods:
    move_to

    Attributes:
    group_folder
    """

    def __init__(self, path, group_folder_name):
        self._group_folder = group_folder_name.title()
        super(CustomFolder, self).__init__(path)

    @property
    def group_folder(self):
        return self._group_folder

    def _get_category_folder(self):
        # category folder is not full path
        return self._group_folder

    def _move_contents(self, src, dst, root_path, group_content=False):
        # move contents of src to dst
        # ignore folders
        files = [content for content in iglob(
            os.path.join(src, '*')) if os.path.isfile(content)]
        if files:
            for file_ in files:
                file_instance = CustomFile(
                    os.path.join(src, file_), self._group_folder)
                file_instance.move_to(
                    dst_root_path=root_path, group=group_content)

    def _move_to(self, dst, root_path, src=None, group_content=False):
        """Move the folder instance to a location relative to the 
        specified dst_root_path.

        Overrides Folder.move_to

        Creates an "ignore" file which prevents Sorter from regrouping 
        or deleting the folder in other operations.

        src and dst should be absolute paths
        If src is not provided, the value of self.path is used.
        dst is the intended destination.
        root_path is the root folder from where files will be organised
        by their extension.
        Will not delete any folder that has contents in it.
        """
        if src is None:
            src = self.path

        if os.path.isdir(dst):
            self._move_contents(src, dst, root_path, group_content)
            if not has_signore_file(dst):
                sorter_ignore_filepath = os.path.join(
                    dst, SORTER_IGNORE_FILENAME)
                open(sorter_ignore_filepath, 'w+').close()
                if os.name == 'nt':
                    # Hide file - Windows
                    ctypes.windll.kernel32.SetFileAttributesW(
                        sorter_ignore_filepath, 2)
            try:
                os.rmdir(src)
            except OSError:
                # TODO: Check if has empty subfolders, then delete
                print('Could not delete "%s". May contain hidden files.' % src)

        else:
            shutil.move(src, dst)
        self.path = dst


class CustomFile(File):
    """Define a file instance with custom attributes.

    Inherits from File.

    Methods:
    get_category

    Attributes:
    category
    """

    def __init__(self, path, group_folder_name):
        self._group_folder = group_folder_name.title()
        super(CustomFile, self).__init__(path)

    @property
    def category(self):
        return self._category

    @category.setter
    def category(self, value):
        self._category = value

    def get_category(self, extension):
        """Return a custom group folder name.

        Overrides File.get_category().
        """
        return self._group_folder

    def move_to(self, dst_root_path, group=True):
        """Move the file instance to a location relative to the 
        specified dst_root_path.

        dst_root_path is the root folder from where files will be organised
        by their extension.

        If dst_root_path = '/home/User/'
        final destination will be
            '/home/User/<category>/<extension>/<filename>'
        """
        final_destination = self._set_extension_destination(
            dst_root_path, group=True)
        if not os.path.dirname(self.path) == os.path.dirname(final_destination):
            try:
                shutil.move(self.path, final_destination)
            except PermissionError as e:
                print('Could not move "{0}": {1}'.format(self.path, e))
            else:
                self.path = final_destination


class CustomFileWithoutExtension(CustomFile):
    """Define a file instance with custom attributes excluding the
    extension from the path.

    Inherits from File. In this class, the file is grouped according to
    the group_folder_name and is not put in an extension folder. 

    That is to say, if root_path is /home/User then this file shall be
    grouped to /home/User/<search string>/<this file>
    """

    def _set_extension_destination(self, root_path, group=True):
        group_dst = os.path.join(root_path, self.category)

        if not os.path.isdir(group_dst):
            os.mkdir(group_dst)

        new_dst = os.path.join(group_dst, self.name)
        suitable_name = self.find_suitable_name(new_dst)
        final_dst = os.path.join(os.path.dirname(new_dst),
                                 suitable_name)

        return final_dst
