# CE3 Node.js Wrapper

This is a Node.js wrapper around ce3.py that provides a seamless experience for running the Claude Engineer v3 interface through Node.js.

## Installation

1. Make sure you have Node.js and Python installed
2. Run `npm install` to install dependencies
3. Ensure ce3.py is in the same directory

## Usage

Simply run:

```bash
npm start
```

This will start the CE3 interface through Node.js, maintaining the same interactive experience as the Python version.

## How it works

The wrapper uses python-shell to create a bidirectional communication channel between Node.js and the Python script, proxying all I/O seamlessly.