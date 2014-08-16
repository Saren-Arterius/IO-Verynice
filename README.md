IO-Verynice
===========

An IO version of verynice. This is for limiting IO for background batch jobs.

Dependencies
===========
- Any linux distro
- python3
- python3: jsbeautifier

Usage
===========
1. Run main.py as root
2. Exit main.py by Ctrl+C
3. Edit settings.json
4. Run main.py background/as daemon

settings.json
===========
- **classes**: you can define your own IO classes here. 
 - *prio_class* and *prio_data* please refer to **ionice**'s *--class* and *--class_data* parameter.


- **processes**: a list of processes (and their threads) to be monitored. 
 - *class* should be present at **classes**.
 - *process_name* is a process's basename.
 - *grep_string* must be present at a process's path or arguments.
 - *owner* must be the owner of the process define.
 - *grep_string*, *owner* could be null.
 - 1 out of *grep_string*, *owner* must be filled, else AssertionError will be raised.

- **other**:
 - *check_interval*: How often will the program check for existing processes and their threads, and apply ionice to them.
