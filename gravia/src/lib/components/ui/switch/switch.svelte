<script lang="ts">
	import { cn, type WithoutChildrenOrChild } from "$lib/utils.js";

	let {
		ref = $bindable(null),
		class: className,
		checked = $bindable(false),
		...restProps
	}: WithoutChildrenOrChild<SwitchPrimitive.RootProps> = $props();
</script>

<label class="switch">
	<input type="checkbox" bind:checked bind:this={ref} {...restProps} />
	<span class="slider"></span>
</label>

<style>
	/* From Uiverse.io by AbanoubMagdy1 */
	/* The switch - the box around the slider */
	.switch {
		font-size: 17px;
		position: relative;
		display: inline-block;
		width: 3.5em;
		height: 2em;
	}

	/* Hide default HTML checkbox */
	.switch input {
		opacity: 0;
		width: 0;
		height: 0;
	}

	/* The slider */
	.slider {
		position: absolute;
		cursor: pointer;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background-color: #474747;
		transition: 0.4s;
		border-radius: 30px;
	}

	.slider:before {
		position: absolute;
		content: "";
		height: 1.4em;
		width: 1.4em;
		border-radius: 20px;
		left: 0.3em;
		bottom: 0.3em;
		background-color: rgba(0, 0, 0, 0.90);
		transition: 0.3s cubic-bezier(0, 2.18, 0.64, 0.69);
	}

	input:checked + .slider {
		background-color: #31ecb4;
	}

	input:focus + .slider {
		box-shadow: 0 0 1px #22e4aa;
	}

	input:checked + .slider:before {
		transform: translateX(1.5em);
	}
</style>
