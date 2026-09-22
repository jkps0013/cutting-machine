import { computed } from 'vue';

export default {
    props: ['state'],
    template: `
        <div id="screen-action">
            <div class="card">
                <div class="status-header">{{ actionText }}</div>
                <div class="loader"></div>
                <p style="text-align:center; color:#888;">Please wait until the machine finishes.<br>The screen will return automatically.</p>
            </div>
        </div>
    `,
    setup(props) {
        const actionText = computed(() => {
            if (props.state === 'HOMING') return "Homing Crosscut...";
            if (props.state === 'TESTING_X') return "Testing Feed Motor...";
            if (props.state === 'TESTING_CROSSCUT') return "Testing Cutting Blade...";
            return "Working...";
        });

        return { actionText };
    }
};
