<script lang="ts">
    import {
        type SuperValidated,
        type Infer,
        superForm,
    } from "sveltekit-superforms";
    import { zodClient } from "sveltekit-superforms/adapters";
    import { toast } from "svelte-sonner";
    import { Button } from "$lib/components/ui/button/index.js";
    import DOBPicker from "$lib/components/ui/dob_picker.svelte";
    import { Textarea } from "$lib/components/ui/textarea/index.js";
    import { Input } from "$lib/components/ui/input/index.js";
    import * as Select from "$lib/components/ui/select/index.js";
    import * as Form from "$lib/components/ui/form/index.js";
    import { invalidateAll } from "$app/navigation";
    import { profileSchema as formSchema } from "$lib/schemas";

    let {
        data,
    }: {
        data: {
            form: SuperValidated<Infer<typeof formSchema>>;
            user?: any;
            profile?: any;
        };
    } = $props();

    // Build fallback initial values if server didn't provide a form
    const normalizeGender = (g: unknown) => {
        const v = (g as string | undefined)?.toLowerCase();
        if (v === "male") return "Male" as const;
        if (v === "female") return "Female" as const;
        return "Other" as const;
    };

    const flattenProfile = (p: any) => {
        const info = p?.additional_info ?? {};
        return {
            name: p?.name ?? "",
            email: p?.email ?? "",
            location: info?.location ?? "",
            bio: info?.bio ?? "",
            dob: info?.dob ?? "",
            gender: normalizeGender(info?.gender),
        };
    };

    const initialFallback = !data.form
        ? data.profile
            ? flattenProfile(data.profile)
            : data.user
              ? flattenProfile(data.user)
              : {
                    name: "",
                    email: "",
                    dob: "",
                    gender: "Other" as const,
                    location: "",
                    bio: "",
                }
        : undefined;

    const form = superForm(data.form ?? (initialFallback as any), {
        validators: zodClient(formSchema),
        resetForm: false, // Don't reset form after submission
        onSubmit: ({ formData, cancel }) => {
            console.log("🔥 Form submit triggered!");
            console.log(
                "Form data being submitted:",
                Object.fromEntries(formData),
            );
        },
        onUpdate: ({ form: f }) => {
            console.log("🔄 Form update triggered, valid:", f.valid);
            if (!f.valid) {
                toast.error("Please fix the errors in the form.");
            }
        },
        onResult: async ({ result }) => {
            console.log("📥 Profile form submit result:", result);
            if (result?.status === 200 || result?.status === 201) {
                toast.success("Profile updated successfully!");
                // Invalidate to refresh data
                await invalidateAll();
            } else if (result?.status && result.status >= 400) {
                toast.error("Failed to update profile");
            }
        },
        onError: ({ result }) => {
            console.log("❌ Form submission error:", result);
            toast.error("Form submission failed");
        },
    });

    const { form: formData, enhance } = form;
</script>

<div class="h-screen overflow-auto">
    <h1 class="text-5xl font-bold text-center mt-4">Profile</h1>
    <div class="flex flex-col items-center justify-center h-full">
        <form
            class="grid grid-cols-2 gap-6 lg:w-3/5 w-4/5 mx-auto font-['Anta']"
            method="POST"
            use:enhance
        >
            <Form.Field {form} name="name">
                <Form.Control>
                    {#snippet children({ props })}
                        <Form.Label>Full name</Form.Label>
                        <Input
                            placeholder="Your name"
                            {...props}
                            bind:value={$formData.name}
                        />
                        <Form.FieldErrors />
                    {/snippet}
                </Form.Control>
            </Form.Field>

            <Form.Field {form} name="email">
                <Form.Control>
                    {#snippet children({ props })}
                        <Form.Label>Email</Form.Label>
                        <Input
                            type="email"
                            placeholder="you@example.com"
                            {...props}
                            bind:value={$formData.email}
                        />
                        <Form.FieldErrors />
                    {/snippet}
                </Form.Control>
            </Form.Field>

            <DOBPicker {form} {formData} />

            <Form.Field {form} name="gender">
                <Form.Control>
                    {#snippet children({ props })}
                        <Form.Label>Gender</Form.Label>
                        <Select.Root
                            type="single"
                            name={props.name}
                            onValueChange={(v) => {
                                if (v) {
                                    $formData.gender = v as any;
                                }
                            }}
                        >
                            <Select.Trigger
                                class="w-full"
                                style="height: 56px;"
                                {...props}
                            >
                                {$formData.gender || "Select"}
                            </Select.Trigger>
                            <Select.Content>
                                <Select.Item value="Male" label="Male" />
                                <Select.Item value="Female" label="Female" />
                                <Select.Item value="Other" label="Other" />
                            </Select.Content>
                        </Select.Root>
                        <input
                            type="hidden"
                            name={props.name}
                            value={$formData.gender || ""}
                        />
                        <Form.FieldErrors />
                    {/snippet}
                </Form.Control>
            </Form.Field>

            <Form.Field {form} name="location" class="col-span-2">
                <Form.Control>
                    {#snippet children({ props })}
                        <Form.Label>Location</Form.Label>
                        <Input
                            placeholder="City, Country"
                            {...props}
                            bind:value={$formData.location}
                        />
                        <Form.FieldErrors />
                    {/snippet}
                </Form.Control>
            </Form.Field>

            <Form.Field {form} name="bio" class="col-span-2">
                <Form.Control>
                    {#snippet children({ props })}
                        <Form.Label>Bio</Form.Label>
                        <Textarea
                            rows={8}
                            placeholder="Tell us a bit about yourself"
                            class="h-30 resize-none"
                            {...props}
                            bind:value={$formData.bio}
                        />
                        <Form.FieldErrors />
                    {/snippet}
                </Form.Control>
            </Form.Field>

            <div class="col-span-2 flex justify-end gap-3 mt-4">
                <Button
                    type="submit"
                    onclick={() => {
                        console.log("🎯 Submit button clicked!");
                        console.log("Current formData:", $formData);
                    }}
                >
                    Save Changes
                </Button>
            </div>
        </form>
    </div>
</div>
