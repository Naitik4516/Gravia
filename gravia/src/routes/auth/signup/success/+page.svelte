<script lang="ts">
    import SkewedButton from "$lib/components/ui/button/SkewedButton.svelte";
    import { goto } from "$app/navigation";
    import { onMount } from "svelte";
    import { gsap } from "gsap";
      import { relaunch } from '@tauri-apps/plugin-process';
import { emit } from '@tauri-apps/api/event';


    const handleSubmit = async () => {
        await emit('app-close');
        await relaunch();
    };

    onMount(() => {
        // Set initial states
        gsap.set(".success-circle", { scale: 0 });
        gsap.set(".checkmark-path", { strokeDasharray: "100", strokeDashoffset: "100" });
        gsap.set(".success-title", { opacity: 0, y: 30 });
        gsap.set(".success-description", { opacity: 0, y: 20 });
        gsap.set(".action-buttons", { opacity: 0, y: 40 });

        // Create timeline
        const tl = gsap.timeline();

        // Animate circle appearance
        tl.to(".success-circle", {
            scale: 1,
            duration: 0.6,
            ease: "back.out(1.7)"
        })
        // Animate checkmark drawing
        .to(".checkmark-path", {
            strokeDashoffset: 0,
            duration: 0.8,
            ease: "power2.inOut"
        }, "-=0.2")
        // Animate title
        .to(".success-title", {
            opacity: 1,
            y: 0,
            duration: 0.6,
            ease: "power2.out"
        }, "-=0.4")
        // Animate description
        .to(".success-description", {
            opacity: 1,
            y: 0,
            duration: 0.5,
            ease: "power2.out"
        }, "-=0.3")
        // Animate buttons
        .to(".action-buttons", {
            opacity: 1,
            y: 0,
            duration: 0.5,
            ease: "power2.out"
        }, "-=0.2");
    });
</script>

<div class="flex flex-col items-center justify-between py-10 w-full h-full">
    <!-- Success checkmark icon -->
    <div class="flex flex-col items-center">
        <div class="mb-10">
            <div
                class="success-circle flex items-center justify-center w-28 h-28 rounded-full bg-[#7CFF7C]"
            >
                <svg width="75" height="75" viewBox="0 0 40 40" fill="none">
                    <path
                        class="checkmark-path"
                        d="M10 20L16 26L30 12"
                        stroke="black"
                        stroke-width="4"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                    />
                </svg>
            </div>
        </div>

        <!-- Main heading -->
        <h1 class="success-title font-poppins text-white text-5xl font-black mb-3">
            Account Created !
        </h1>

        <!-- Description text -->
        <p
            class="success-description font-tekar text-[#B0B0B0] leading-tight mb-12 max-w-110 text-center"
        >
            Your account has been created. <br /> Add more details to personalize
            your experience, or skip for now.
        </p>
    </div>

    <!-- Action buttons -->
    <div
        class="action-buttons flex flex-row justify-between w-full mt-10 gap-8 flex-wrap items-end"
    >
        <button
            class="font-['Tektur'] text-lg tracking-wider text-gray-200 bg-none border-none cursor-pointer  hover:text-white hover:font-bold hover:drop-shadow-xl transition-all pb-1"
            onclick={handleSubmit}
        >
            Skip for now
        </button>
        <SkewedButton
            text="Personalize my experience"
            onclick={() => goto("/auth/signup/additional")}
        />
    </div>
</div>
