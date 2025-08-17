.. Core Utilities documentation master file, created by
   sphinx-quickstart
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to XXXX documentation!
==============================
Say something about your code base here


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   module <module>

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Installation
============
This package is loaded on the PyPi repository and can be installed via the following method

#. Create a python virtual environment ``python -m venv /path/to/new/virtual/environment``
#. Activate the virtual environment with the following command;

.. table:: Activation Commands for Virtual Environments

   +----------------------+------------------+-------------------------------------------+
   | Platform             | Shell            | Command to activate virtual environment   |
   +======================+==================+===========================================+
   | POSIX                | bash/zsh         | ``$ source <venv>/bin/activate``          |
   +                      +------------------+-------------------------------------------+
   |                      | fish             | ``$ source <venv>/bin/activate.fish``     |
   +                      +------------------+-------------------------------------------+
   |                      | csh/tcsh         | ``$ source <venv>/bin/activate.csh``      |
   +                      +------------------+-------------------------------------------+
   |                      | Powershell       | ``$ <venv>/bin/Activate.ps1``             |
   +----------------------+------------------+-------------------------------------------+
   | Windows              | cmd.exe          | ``C:\> <venv>\\Scripts\\activate.bat``    |
   +                      +------------------+-------------------------------------------+
   |                      | PowerShell       | ``PS C:\\> <venv>\\Scripts\\Activate.ps1``|
   +----------------------+------------------+-------------------------------------------+

.. rst-class:: numbered-list

#. Install poetry globally on your computer. Follow the instructions from the
   `Poetry <https://python-poetry.org/docs/>`_ web site
#. Set the poetry virtual environment with the following command ``poetry config virtualenvs.in-project true``
#. Ensure you have .git installed on your computer.
#. At your desired location create a directory titled  ``xx``
#. Open a terminal (Bash, zsh or DOS) and cd to the ``xx`` directory
#. Type ``git clone https://github.com/Jon-Webb-79/xx.git``
#. Install packages with ``poetry install``


Usage
=====
The user instructions for this application is shown in :doc:`module`.


Contributing
============
Pull requests are welcome.  For major changes, please open an issue first to discuss what
you would like to change.  Please make sure to include and update tests as well
as relevant cod-strings and sphinx updates.

License
=======
This project uses a basic MIT license
