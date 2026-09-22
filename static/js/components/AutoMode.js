import { ref } from 'vue';

export default {
    props: ['current', 'target'],
    template: `
        <div id="screen-auto">
            <div class="card">
                <div class="status-header">Auto Mode Running</div>
                <div class="progress-text">
                    <span style="color: #4CAF50;">{{ current }}</span> / <span>{{ target }}</span>
                </div>
                <button class="btn-stop" @click="stop">{{ buttonText }}</button>
            </div>
        </div>
    `,
    setup(props, { emit }) {
        const buttonText = ref("STOP MACHINE");
        
        const stop = () => {
            buttonText.value = "Stopping...";
            emit('stop-machine');
        };
        
        return { buttonText, stop };
    }
};
