const { PythonShell } = require('python-shell');
const path = require('path');

class CE3Wrapper {
    constructor() {
        this.pythonPath = 'python'; // Assuming python is in PATH
        this.scriptPath = path.join(__dirname, 'ce3.py');
    }

    async run(input) {
        return new Promise((resolve, reject) => {
            const options = {
                mode: 'text',
                pythonPath: this.pythonPath,
                pythonOptions: ['-u'], // unbuffered output
                args: []
            };

            const pyshell = new PythonShell(this.scriptPath, options);

            // Handle output from Python script
            pyshell.on('message', function(message) {
                process.stdout.write(message);
            });

            // Handle input to Python script
            process.stdin.on('data', (data) => {
                pyshell.send(data.toString());
            });

            pyshell.on('error', function(err) {
                reject(err);
            });

            pyshell.on('close', function() {
                resolve();
            });

            // Send initial input if provided
            if (input) {
                pyshell.send(input);
            }
        });
    }
}

// Create instance and run
const wrapper = new CE3Wrapper();
wrapper.run().catch(console.error);
