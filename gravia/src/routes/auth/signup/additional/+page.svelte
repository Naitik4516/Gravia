<script lang="ts">
    import Input from "../../components/Input.svelte";
    import * as Select from "$lib/components/ui/select/index.js";
    import { preferencesSchema } from "$lib/schemas";
    import {
        type SuperValidated,
        type Infer,
        superForm,
    } from "sveltekit-superforms";
    import { zodClient } from "sveltekit-superforms/adapters";

    import * as Form from "$lib/components/ui/form/index.js";
    import { Button } from "$lib/components/ui/button/index.js";
    import { toast } from "svelte-sonner";
    import { Progress } from "$lib/components/ui/progress/index.js";
    import { onMount } from "svelte";
    import { gsap } from "gsap";

    let {
        data,
    }: { data: { form: SuperValidated<Infer<typeof preferencesSchema>> } } =
        $props();

    const form = superForm(data.form, {
        validators: zodClient(preferencesSchema),
        onResult: ({ result }) => {
            submitting = false;
            if (result?.status && result.status >= 200 && result.status < 300) {
                toast.success("Preferences saved");
            } else if (result?.status) {
                toast.error("Failed to save preferences");
            }
        },
        onError: ({ result }) => {
            submitting = false;
            toast.error("Submission error");
        }
    });

    const { form: formData, enhance, errors } = form;

    const questions = [
        {
            name: "preferred_name" as keyof typeof $formData,
            question: "What would you like to be called?",
            hint: "e.g 'Sir', 'Dude', 'Champ', etc.",
            type: "text",
        },
        {
            name: "preferred_language" as keyof typeof $formData,
            question: "Which language do you feel most comfortable using?",
            hint: "e.g., English, Spanish, etc.",
            type: "text",
        },
        {
            name: "response_tone" as keyof typeof $formData,
            question: "How would you like me to sound when I reply?",
            type: "select",
            options: ["Formal", "Informal", "Neutral", "Professional", "Encouraging", "Optimistic", "Witty or Playful", "Sarcastic", "Empathetic"],
        },
        {
            // Match schema key: response_length (was preferred_length causing undefined)
            name: "response_length" as keyof typeof $formData,
            question: "How long should my responses be for you?",
            type: "select",
            options: ["brief", "moderate", "detailed", "dynamic"],
        },
        {
            name: "humour_level" as keyof typeof $formData,
            question: "How much humour would you like in my replies?",
            type: "select",
            options: ["serious", "slightly humorous", "balanced", "funny", "very humorous"],
        },
        {
            name: "custom_instructions" as keyof typeof $formData,
            question: "Any special instructions for me?",
            type: "textarea"
        }
    ];

    let currentStep = $state(0);
    const totalSteps = questions.length;

    let progress = $derived(Math.round(((currentStep + 1) / totalSteps) * 100));

    let currentQuestion = $derived(questions[currentStep]);
    let currentQuestionName = $derived(currentQuestion.name);

    // Debug: reactive log (comment out in production)
    $effect(() => {
        console.log("Current step question:", currentQuestionName, currentQuestion);
    });

    let isLastStep = $derived(currentStep === totalSteps - 1);
    let isFirstStep = $derived(currentStep === 0);

    const isFilled = (value: unknown) => {
        if (value === undefined || value === null) return false;
        if (typeof value === "string") return value.trim().length > 0;
        if (Array.isArray(value)) return value.length > 0;
        return true;
    };

    let currentValue = $derived($formData[currentQuestionName]);
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
            // NOTE: Removed unsupported gsap event callbacks (onInterrupt, onKill) to satisfy TS types

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
                console.log(currentStep);
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
    let submitting = $state(false);
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
    method="POST"
    class="flex flex-col justify-between items-center h-full w-full py-14"
    use:enhance={{
        onSubmit: async (event) => {
            const { cancel, formElement, formData } = event;
            if (submitting) {
                cancel();
                return;
            }
            submitting = true;
            // Let superforms proceed normally; no cancel => it handles fetch.
        }
    }}
    bind:this={formEl}
>
    <h1 class="form-title font-poppins text-white text-5xl font-black mb-10 text-center">
        {currentQuestion.question}
    </h1>
    <div class="form-content flex flex-col items-center lg:w-3/5 w-4/5">
            {#if currentQuestion.type === "text"}
                <Input
                    name={currentQuestionName}
                    type="text"
                    placeholder={currentQuestion.hint || ""}
                    bind:value={$formData[currentQuestionName]}
                    {form}
                    {errors}
                />

            {:else if currentQuestion.type === "select"}
                <Form.Field {form} name={currentQuestionName} class="w-full">
                    <Form.Control>
                        {#snippet children({ props })}
                            <Select.Root
                                type="single"
                                name={props.name}
                                onValueChange={(v) => {
                                    if (v) {
                                        $formData[currentQuestionName] = v;
                                    }
                                }}
                            >
                                <Select.Trigger
                                    class="w-full bg-slate-950/90  h-16 rounded-xl hover:bg-slate-950 hover:text-white outline-white/5 capitalize "
                                    style="height: 4rem;"
                                    {...props}
                                >
                                    {$formData[currentQuestionName]
                                        ? $formData[currentQuestionName]
                                        : "Select an option"}
                                </Select.Trigger>
                                <Select.Content>
                                    {#each currentQuestion.options || [] as option}
                                        <Select.Item
                                            value={option.toLowerCase()}
                                            label={option.toLocaleUpperCase()}
                                        />
                                    {/each}
                                </Select.Content>
                            </Select.Root>
                            <input
                                type="hidden"
                                name={currentQuestionName}
                                value={$formData[currentQuestionName] || ""}
                            />
                        {/snippet}
                    </Form.Control>
                    <Form.FieldErrors />
                </Form.Field>

            {:else if currentQuestion.type === "textarea"}
                <Form.Field {form} name={currentQuestionName} class="w-full">
                    <Form.Control>
                        {#snippet children({ props })}
                            <textarea
                                class="w-full bg-slate-950/90 rounded-xl p-4 text-white/70 text-lg font-normal placeholder:font-['Audiowide'] outline-white/5 hover:outline-2 hover:shadow-xl resize-none"
                                style="height: 8rem;"
                                placeholder={currentQuestion.hint || "Type your response here..."}
                                {...props}
                                bind:value={$formData[currentQuestionName]}
                            ></textarea>
                        {/snippet}
                    </Form.Control>
                    <Form.FieldErrors />
                </Form.Field>
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
