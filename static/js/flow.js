// Flow creation form handling
document.addEventListener('DOMContentLoaded', () => {
    const flowForm = document.getElementById('flow-form');
    const errorMessage = document.getElementById('error-message');

    flowForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorMessage.classList.add('hidden');

        try {
            // Validate and parse steps JSON
            let steps;
            try {
                steps = JSON.parse(document.getElementById('flow-steps').value);
                if (!Array.isArray(steps) || steps.length === 0) {
                    throw new Error('Steps must be a non-empty array');
                }
                // Validate step format
                steps.forEach(step => {
                    if (!step.type || !step.content) {
                        throw new Error('Each step must have type and content fields');
                    }
                });
            } catch (parseError) {
                throw new Error('Invalid steps format. Please use JSON array format: [{"type": "action", "content": "step description"}]');
            }

            const flowData = {
                name: document.getElementById('flow-name').value,
                type: document.getElementById('flow-type').value,
                description: document.getElementById('flow-description').value,
                steps: steps
            };

            const response = await fetch('/create-flow', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(flowData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to create flow');
            }

            // Clear form on success
            flowForm.reset();
            // Show success message
            const successMessage = document.createElement('div');
            successMessage.className = 'text-green-600 dark:text-green-400 text-sm mt-2';
            successMessage.textContent = 'Flow created successfully!';
            errorMessage.parentNode.insertBefore(successMessage, errorMessage);
            setTimeout(() => successMessage.remove(), 3000);

        } catch (error) {
            console.error('Error creating flow:', error);
            errorMessage.textContent = error.message;
            errorMessage.classList.remove('hidden');
        }
    });
});
