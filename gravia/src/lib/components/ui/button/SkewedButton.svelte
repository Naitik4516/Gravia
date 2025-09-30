<script>
    import { fade } from "$lib/utils/animations";
    let { text = "Next", submitting = false, ...props } = $props();

</script>

<button
    class="md:text-lg text-md font-semibold text-black font-['Orbitron']  md:px-6 md:py-3 px-4 py-2 rounded transition-all duration-200 shadow-[0px_4px_94px_0px_rgba(43,107,138,1.00)] hover:scale-105 hover:shadow-xl cursor-pointer -skew-x-10 bg-[#40e0d0] hover:bg-[#4ee1e3] hover:-skew-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
    type="submit"
    disabled={submitting}
    {...props}
    {@attach fade}
>
    <span class="inline-flex items-center skew-x-10 hover:skew-x-3" >
        {#if submitting}
            Loading...
        {:else}
            {text}
        {/if}
        <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="2.5"
            stroke="currentColor"
            class="ml-2 w-5 h-5"
        >
            <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M13.5 4.5 21 12m0 0L13.5 19.5M21 12H3"
            />
        </svg>
    </span>
</button>
