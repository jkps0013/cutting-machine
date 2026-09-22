import { createApp, ref, onMounted, onUnmounted } from 'vue';
import ControlPanel from './components/ControlPanel.js';
import AutoMode from './components/AutoMode.js';
import ActionScreen from './components/ActionScreen.js';

const App = {
    template: `
        <div>
            <h2>Pad Machine Control</h2>
            
            <ControlPanel 
                v-if="machineState === 'IDLE'" 
                @start-command="sendCommand" 
            />
            
            <AutoMode 
                v-else-if="machineState === 'AUTO_MODE'"
                :current="autoCurrent"
                :target="autoTarget"
                @stop-machine="stopMachine"
            />
            
            <ActionScreen 
                v-else 
                :state="machineState" 
                @stop-machine="stopMachine"
            />
        </div>
    `,
    components: { ControlPanel, AutoMode, ActionScreen },
    setup() {
        const machineState = ref('IDLE');
        const autoCurrent = ref(0);
        const autoTarget = ref(50);
        let pollInterval = null;

        const pollStatus = async () => {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                machineState.value = data.state;
                autoCurrent.value = data.current;
                autoTarget.value = data.target;
            } catch (err) {
                console.error("Server disconnected");
            }
        };

        const sendCommand = async (endpoint, data) => {
            // Optimistically update the UI instantly so fast tasks (like Feed X) still show a visual response!
            if (endpoint === '/api/home') machineState.value = 'HOMING';
            if (endpoint === '/api/test_x') machineState.value = 'TESTING_X';
            if (endpoint === '/api/test_crosscut') machineState.value = 'TESTING_CROSSCUT';
            if (endpoint === '/api/auto') machineState.value = 'AUTO_MODE';

            await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            pollStatus(); // Poll immediately after the request is sent
        };

        const stopMachine = async () => {
            await fetch('/api/stop', { method: 'POST' });
            setTimeout(pollStatus, 200);
        };

        onMounted(() => {
            pollStatus();
            pollInterval = setInterval(pollStatus, 500);
        });

        onUnmounted(() => {
            clearInterval(pollInterval);
        });

        return { machineState, autoCurrent, autoTarget, sendCommand, stopMachine };
    }
};

createApp(App).mount('#app');
