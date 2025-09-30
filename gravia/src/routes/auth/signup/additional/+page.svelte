<script lang="ts">
    import { SETTINGS_UPDATE_CATEGORY_URL } from "$lib/constants/api";
    import { toast } from "svelte-sonner";
    import { goto } from "$app/navigation";
    import { Button } from "$lib/components/ui/button/index.js";
    import { Progress } from "$lib/components/ui/progress/index.js";
    import { Input } from "$lib/components/ui/input/index.js";
    import * as Select from "$lib/components/ui/select/index.js";
    import { Textarea } from "$lib/components/ui/textarea/index.js";
    import { onMount } from "svelte";
    import { gsap } from "gsap";
      import { relaunch } from '@tauri-apps/plugin-process';
import { emit } from '@tauri-apps/api/event';


    let preferred_name = $state('');
    let preferred_language = $state('');
    let response_tone = $state('');
    let response_length = $state('');
    let humour_level = $state('');
    let custom_instructions = $state('');
    let submitting = $state(false);

    async function handleSubmit(event: Event) {
        event.preventDefault();
        if (submitting) return;

        submitting = true;
        try {
            const settings = {
                preferred_name,
                preferred_language,
                response_tone,
                response_length,
                humour_level,
                custom_instructions,
            };

            const res = await fetch(SETTINGS_UPDATE_CATEGORY_URL, {
                method: 'PUT',
                body: JSON.stringify({ category: "personalization", settings }),
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (res.ok) {
                toast.success('Preferences saved successfully');
                        await emit('app-close');
        await relaunch();
            } else {
                toast.error('Failed to save preferences');
            }
        } catch (error) {
            toast.error('An error occurred while saving preferences');
            console.error('Fetch error:', error);
        } finally {
            submitting = false;
        }
    }

    const questions = [
        {
            name: "preferred_name" as keyof typeof preferred_name,
            question: "What would you like to be called?",
            hint: "e.g 'Sir', 'Dude', 'Champ', etc.",
            type: "text",
        },
        {
            name: "preferred_language" as keyof typeof preferred_language,
            question: "Which language do you feel most comfortable using?",
            hint: "e.g., English, Spanish, etc.",
            type: "text",
        },
        {
            name: "response_tone" as keyof typeof response_tone,
            question: "How would you like me to sound when I reply?",
            type: "select",
            options: ["Formal", "Informal", "Neutral", "Professional", "Encouraging", "Optimistic", "Witty or Playful", "Sarcastic", "Empathetic"],
        },
        {
            name: "response_length" as keyof typeof response_length,
            question: "How long should my responses be for you?",
            type: "select",
            options: ["brief", "moderate", "detailed", "dynamic"],
        },
        {
            name: "humour_level" as keyof typeof humour_level,
            question: "How much humour would you like in my replies?",
            type: "select",
            options: ["serious", "slightly humorous", "balanced", "funny", "very humorous"],
        },
        {
            name: "custom_instructions" as keyof typeof custom_instructions,
            question: "Any special instructions for me?",
            type: "textarea"
        }
    ];

    let currentStep = $state(0);
    const totalSteps = questions.length;

    let progress = $derived(Math.round(((currentStep + 1) / totalSteps) * 100));

    let currentQuestion = $derived(questions[currentStep]);
    let currentQuestionName = $derived(currentQuestion.name as string);

    let isLastStep = $derived(currentStep === totalSteps - 1);
    let isFirstStep = $derived(currentStep === 0);

    const isFilled = (value: unknown) => {
        if (value === undefined || value === null) return false;
        if (typeof value === "string") return value.trim().length > 0;
        if (Array.isArray(value)) return value.length > 0;
        return true;
    };

    let currentValue = $derived(() => {
        switch (currentQuestionName) {
            case 'preferred_name': return preferred_name;
            case 'preferred_language': return preferred_language;
            case 'response_tone': return response_tone;
            case 'response_length': return response_length;
            case 'humour_level': return humour_level;
            case 'custom_instructions': return custom_instructions;
            default: return '';
        }
    });
    let hasValue = $derived(isFilled(currentValue));
    let canSkip = $derived(!hasValue);

    let isAnimating = $state(false);

    onMount(() => {
        gsap.set(".form-content", { opacity: 1, x: 0 });
        gsap.set(".form-title", { opacity: 1, y: 0 });
    });

    const animateStepChange = (direction: "next" | "prev") => {
        if (isAnimating) return;
        isAnimating = true;

        const tl = gsap.timeline({
            onComplete: () => {
                isAnimating = false;
            },
        });

        const slideOutX = direction === "next" ? -100 : 100;
        const slideInX = direction === "next" ? 100 : -100;

        // Slide out current content
        tl.to(".form-title", {
            opacity: 0,
            y: -20,
            duration: 0.3,
            ease: "power2.in",
        })
            .to(
                ".form-content",
                {
                    opacity: 0,
                    x: slideOutX,
                    duration: 0.3,
                    ease: "power2.in",
                },
                "-=0.2",
            )
            // Update step
            .call(() => {
                const delta = direction === "next" ? 1 : -1;
                const nextStep = currentStep + delta;
                currentStep = Math.min(Math.max(nextStep, 0), totalSteps - 1);
            })
            // Slide in new content
            .set(".form-content", { x: slideInX })
            .set(".form-title", { y: 20 })
            .to(".form-title", {
                opacity: 1,
                y: 0,
                duration: 0.4,
                ease: "power2.out",
            })
            .to(
                ".form-content",
                {
                    opacity: 1,
                    x: 0,
                    duration: 0.4,
                    ease: "power2.out",
                },
                "-=0.3",
            );
    };

    const nextStep = () => {
        if (currentStep < totalSteps - 1 && !isAnimating) {
            animateStepChange("next");
        }
    };

    const prevStep = () => {
        if (currentStep > 0 && !isAnimating) {
            animateStepChange("prev");
        }
    };

    let formEl: HTMLFormElement;
    const handleSkip = () => {
        if (isLastStep) {
            formEl?.requestSubmit();
        } else {
            nextStep();
        }
    };
</script>

<!-- Progress indicator -->
<Progress value={progress} />
<form
    onsubmit={handleSubmit}
    class="flex flex-col justify-between items-center h-full w-full py-14"
    bind:this={formEl}
>
    <h1 class="form-title font-poppins text-white text-5xl font-black mb-10 text-center">
        {currentQuestion.question}
    </h1>
    <div class="form-content flex flex-col items-center lg:w-3/5 w-4/5">
        {#if currentQuestion.type === "text"}
            {#if currentQuestionName === 'preferred_name'}
                <Input
                    type="text"
                    placeholder={currentQuestion.hint || ""}
                    bind:value={preferred_name}
                />
            {:else if currentQuestionName === 'preferred_language'}
                <Input
                    type="text"
                    placeholder={currentQuestion.hint || ""}
                    bind:value={preferred_language}
                />
            {/if}
        {:else if currentQuestion.type === "select"}
            {#if currentQuestionName === 'response_tone'}
                <Select.Root
                    type="single"
                    name="response_tone"
                    bind:value={response_tone}
                >
                    <Select.Trigger class="w-full">
                        {response_tone || "Select an option"}
                    </Select.Trigger>
                    <Select.Content>
                        {#each currentQuestion.options || [] as option}
                            <Select.Item value={option.toLowerCase()} label={option} />
                        {/each}
                    </Select.Content>
                </Select.Root>
            {:else if currentQuestionName === 'response_length'}
                <Select.Root
                    type="single"
                    name="response_length"
                    bind:value={response_length}
                >
                    <Select.Trigger class="w-full">
                        {response_length || "Select an option"}
                    </Select.Trigger>
                    <Select.Content>
                        {#each currentQuestion.options || [] as option}
                            <Select.Item value={option.toLowerCase()} label={option} />
                        {/each}
                    </Select.Content>
                </Select.Root>
            {:else if currentQuestionName === 'humour_level'}
                <Select.Root
                    type="single"
                    name="humour_level"
                    bind:value={humour_level}
                >
                    <Select.Trigger class="w-full">
                        {humour_level || "Select an option"}
                    </Select.Trigger>
                    <Select.Content>
                        {#each currentQuestion.options || [] as option}
                            <Select.Item value={option.toLowerCase()} label={option} />
                        {/each}
                    </Select.Content>
                </Select.Root>
            {/if}
        {:else if currentQuestion.type === "textarea"}
            <Textarea
                placeholder={currentQuestion.hint || "Type your response here..."}
                bind:value={custom_instructions}
                class="resize-none"
                rows={8}
            />
        {/if}
    </div>

    <!-- Navigation Buttons -->
    <div class="flex mt-10 justify-between pt-4 w-full px-3">
        {#if currentStep > 0}
            <Button
                type="button"
                variant="ghost"
                onclick={prevStep}
                disabled={isFirstStep || isAnimating}
                size="xl"
            >
                Back
            </Button>
        {/if}

        <div class="ml-auto flex gap-3">
            {#if isLastStep}
                <Button
                    type="submit"
                    size="xl"
                    disabled={isAnimating || submitting}
                >
                    {#if submitting}
                        Saving...
                    {:else}
                        Complete
                    {/if}
                </Button>
            {:else}
                {#if canSkip}
                    <Button
                        type="button"
                        variant="ghost"
                        onclick={handleSkip}
                        size="xl"
                        disabled={isAnimating}
                    >
                        Skip
                    </Button>
                {:else}
                    <Button
                        type="button"
                        onclick={nextStep}
                        class="text-lg"
                        size="xl"
                        disabled={isAnimating}
                    >
                        Next
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
                    </Button>
                {/if}
            {/if}
        </div>
    </div>
</form>
