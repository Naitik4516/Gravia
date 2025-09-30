<script lang="ts">
    import { toast } from "svelte-sonner";
    import { Button } from "$lib/components/ui/button/index.js";
    import { Textarea } from "$lib/components/ui/textarea/index.js";
    import { Input } from "$lib/components/ui/input/index.js";
    import * as Select from "$lib/components/ui/select/index.js";
    import * as Form from "$lib/components/ui/form/index.js";
    import { invalidateAll } from "$app/navigation";
    import { USER_PROFILE_URL } from "$lib/constants/api";

    let name = $state('');
    let email = $state('');
    let location = $state('');
    let bio = $state('');
    let dob = $state('');
    let gender = $state('');
    let submitting = $state(false);

    async function handleSubmit(event: Event) {
        event.preventDefault();
        if (submitting) return;

        submitting = true;
        try {
            const payload = {
                name,
                email,
                additional_info: {
                    location,
                    bio,
                    dob,
                    gender,
                },
            };

            const res = await fetch(USER_PROFILE_URL, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (res.ok) {
                toast.success("Profile updated successfully!");
                await invalidateAll();
            } else {
                toast.error("Failed to update profile");
            }
        } catch (error) {
            console.error("Profile update error:", error);
            toast.error("An error occurred while updating profile");
        } finally {
            submitting = false;
        }
    }
</script>

<div class="h-screen overflow-auto">
    <h1 class="text-5xl font-bold text-center mt-4">Profile</h1>
    <div class="flex flex-col items-center justify-center h-full">
        <form onsubmit={handleSubmit} class="grid grid-cols-2 gap-6 lg:w-3/5 w-4/5 mx-auto font-['Anta']">
            <Form.Field>
                <Form.Control>
                    {#snippet children({ props })}
                        <Form.Label>Full name</Form.Label>
                        <Input
                            placeholder="Your name"
                            {...props}
                            bind:value={name}
                        />
                        <Form.FieldErrors />
                    {/snippet}
                </Form.Control>
            </Form.Field>

            <Form.Field>
                <Form.Control>
                    {#snippet children({ props })}
                        <Form.Label>Email</Form.Label>
                        <Input
                            type="email"
                            placeholder="you@example.com"
                            {...props}
                            bind:value={email}
                        />
                        <Form.FieldErrors />
                    {/snippet}
                </Form.Control>
            </Form.Field>

            <Form.Field>
                <Form.Control>
                    {#snippet children({ props })}
                        <Form.Label>Date of Birth</Form.Label>
                        <Input
                            type="date"
                            {...props}
                            bind:value={dob}
                        />
                        <Form.FieldErrors />
                    {/snippet}
                </Form.Control>
            </Form.Field>

            <Form.Field>
                <Form.Control>
                    {#snippet children({ props })}
                        <Form.Label>Gender</Form.Label>
                        <Select.Root
                            type="single"
                            name={props.name}
                            bind:value={gender}
                        >
                            <Select.Trigger class="w-full" style="height: 56px;">
                                {gender || "Select"}
                            </Select.Trigger>
                            <Select.Content>
                                <Select.Item value="Male" label="Male" />
                                <Select.Item value="Female" label="Female" />
                                <Select.Item value="Other" label="Other" />
                            </Select.Content>
                        </Select.Root>
                        <Form.FieldErrors />
                    {/snippet}
                </Form.Control>
            </Form.Field>

            <Form.Field class="col-span-2">
                <Form.Control>
                    {#snippet children({ props })}
                        <Form.Label>Location</Form.Label>
                        <Input
                            placeholder="City, Country"
                            {...props}
                            bind:value={location}
                        />
                        <Form.FieldErrors />
                    {/snippet}
                </Form.Control>
            </Form.Field>

            <Form.Field class="col-span-2">
                <Form.Control>
                    {#snippet children({ props })}
                        <Form.Label>Bio</Form.Label>
                        <Textarea
                            rows={8}
                            placeholder="Tell us a bit about yourself"
                            class="h-30 resize-none"
                            {...props}
                            bind:value={bio}
                        />
                        <Form.FieldErrors />
                    {/snippet}
                </Form.Control>
            </Form.Field>

            <div class="col-span-2 flex justify-end gap-3 mt-4">
                <Button type="submit" disabled={submitting}>
                    {#if submitting}
                        Saving...
                    {:else}
                        Save Changes
                    {/if}
                </Button>
            </div>
        </form>
    </div>
</div>
