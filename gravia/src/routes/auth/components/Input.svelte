<script lang="ts">
    import * as Form from "$lib/components/ui/form/index.js";
    import { slide } from "$lib/utils/animations";

    let {
        type = "text",
        placeholder = "",
        iconname = "",
        name,
        value = $bindable(),
        form,
        errors,
        animate=true
    } = $props();
</script>

{#snippet Icon(name: string)}
    <span class="text-[#BDE3FF]">
        {#if name === "Mail"}
            <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                class="size-6"
            >
                <path
                    d="M1.5 8.67v8.58a3 3 0 0 0 3 3h15a3 3 0 0 0 3-3V8.67l-8.928 5.493a3 3 0 0 1-3.144 0L1.5 8.67Z"
                />
                <path
                    d="M22.5 6.908V6.75a3 3 0 0 0-3-3h-15a3 3 0 0 0-3 3v.158l9.714 5.978a1.5 1.5 0 0 0 1.572 0L22.5 6.908Z"
                />
            </svg>
        {:else if name === "Lock"}
            <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                class="size-6"
            >
                <path
                    fill-rule="evenodd"
                    d="M12 1.5a5.25 5.25 0 0 0-5.25 5.25v3a3 3 0 0 0-3 3v6.75a3 3 0 0 0 3 3h10.5a3 3 0 0 0 3-3v-6.75a3 3 0 0 0-3-3v-3c0-2.9-2.35-5.25-5.25-5.25Zm3.75 8.25v-3a3.75 3.75 0 1 0-7.5 0v3h7.5Z"
                    clip-rule="evenodd"
                />
            </svg>
        {:else if name === "User"}
            <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                class="size-6"
            >
                <path
                    fill-rule="evenodd"
                    d="M7.5 6a4.5 4.5 0 1 1 9 0 4.5 4.5 0 0 1-9 0ZM3.751 20.105a8.25 8.25 0 0 1 16.498 0 .75.75 0 0 1-.437.695A18.683 18.683 0 0 1 12 22.5c-2.786 0-5.433-.608-7.812-1.7a.75.75 0 0 1-.437-.695Z"
                    clip-rule="evenodd"
                />
            </svg>
        {/if}
    </span>
{/snippet}

<Form.Field {form} {name} class="w-full" id={name}>
    <div
        class="flex flex-col bg-slate-950/90 rounded-lg shadow-lg outline-1 {$errors[
            name
        ]
            ? 'outline-red-500'
            : 'outline-white/10'}  m-4 px-3 py-3 w-full max-h-24 min-h-18 hover:outline-2 hover:shadow-xl align-center justify-center transition-all"
        {...(animate ? { 'use:slide': true } : {})}
    >
        <div class="flex">
            <Form.Control>
                {#snippet children({ props })}
                    {#if iconname}
                        <div class="mr-3 ml-1">
                            {@render Icon(iconname)}
                        </div>
                    {/if}
                    <input
                        {type}
                        {placeholder}
                        {...props}
                        bind:value
                        class="w-full h-full bg-transparent text-white/70 text-lg font-normal placeholder:font-['Audiowide'] outline-none"
                    />
                {/snippet}
            </Form.Control>
        </div>

        {#if $errors[name]}
            <div class="mt-2 overflow-auto">
                <Form.FieldErrors class="font-mono" />
            </div>
        {/if}
    </div>
</Form.Field>
