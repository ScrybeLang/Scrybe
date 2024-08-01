# `Scrybe`, the Other Scratch Compiler

Scrybe is a text-based langage implemented in Python that compiles into a Scratch project. This project is based on [PLY](https://pypi.org/project/ply/) and [ScratchGen](https://pypi.org/project/ScratchGen/), and was inspired by [goboscript](https://github.com/aspizu/goboscript).

Much like goboscript, Scrybe allows you to create Scratch projects with a text editor or IDE instead of manually dragging and dropping blocks together. This comes with the benefits of easier version control, code being easier to debug (Scrybe has error messages), and being familiar to programmers who are used to text-based coding.

Also similarly to goboscript, Scrybe does much more than simply map each line of code to a block in the script editor. It has features such as function return values, broadcast messages, and dynamic variable scoping. Additionally, the syntax is mostly similar to languages such as JavaScript and C++.
