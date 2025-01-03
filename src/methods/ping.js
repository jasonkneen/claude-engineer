/**
 * Example MCP method implementation
 */

module.exports = async function ping(params = {}) {
    return {
        pong: Date.now(),
        echo: params
    };
};