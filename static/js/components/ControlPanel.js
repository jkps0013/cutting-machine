import { ref } from 'vue';

export default {
    template: `
        <div id="screen-idle">
            <div class="card">
                <label>Tracepad Size</label>
                <select v-model="settings.size">
                    <option value="12.7">Small (12.7mm)</option>
                    <option value="30.0">Medium (30mm)</option>
                    <option value="42.0">Large (42mm)</option>
                </select>

                <label>Feed Speed (1-10)</label>
                <input type="number" v-model.number="settings.feed_speed" min="1" max="10" @blur="clampValues">
                <label>Feed Acceleration (1-10)</label>
                <input type="number" v-model.number="settings.feed_accel" min="1" max="10" @blur="clampValues">

                

                                <label>Steps per mm (Feed Calibration)</label>
                <input type="number" v-model.number="settings.steps_per_mm" step="0.001" min="0.001">

                <label>Quantity</label>
                <input type="number" v-model.number="settings.quantity" min="1">
            </div>

            <div class="card">
                <button class="btn-home" @click="emitCommand('/api/home')">1. Home Crosscut</button>
                <button class="btn-test" @click="emitCommand('/api/test_x')">Test: Feed X-Direction</button>
                <button class="btn-test" @click="emitCommand('/api/test_crosscut')">Test: One Crosscut</button>
                <button class="btn-auto" @click="emitCommand('/api/auto')">Start Auto Mode</button>
            </div>
        </div>
    `,
    setup(props, { emit }) {
        const settings = ref({
            size: "30.0",
            feed_speed: 8,
            feed_accel: 8,
            steps_per_mm: 0.795,
            quantity: 50
        });

        const clampValues = () => {
            settings.value.feed_speed = Math.max(1, Math.min(10, settings.value.feed_speed));
            settings.value.feed_accel = Math.max(1, Math.min(10, settings.value.feed_accel));
            
            
        };

        const emitCommand = (endpoint) => {
            clampValues();
            emit('start-command', endpoint, settings.value);
        };

        return { settings, clampValues, emitCommand };
    }
};

