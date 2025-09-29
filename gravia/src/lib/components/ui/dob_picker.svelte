<script lang="ts">
    import { cn } from "$lib/utils.js";
    import { buttonVariants } from "$lib/components/ui/button/index.js";
    import Calendar from "$lib/components/ui/calendar/calendar.svelte";
    import * as Popover from "$lib/components/ui/popover/index.js";
    import * as Form from "$lib/components/ui/form/index.js";
    import CalendarIcon from "@lucide/svelte/icons/calendar";
    import {
        CalendarDate,
        DateFormatter,
        type DateValue,
        getLocalTimeZone,
        parseDate,
        today,
    } from "@internationalized/date";

    const { form, formData } = $props();
    
    const df = new DateFormatter("en-US", {
        dateStyle: "long",
    });

    let value = $derived($formData.dob ? parseDate($formData.dob) : undefined);

    let placeholder = $state<DateValue>(today(getLocalTimeZone()));
</script>

<Form.Field {form} name="dob" class="flex flex-col">
    <Form.Control>
        {#snippet children({ props })}
            <Form.Label>Date of birth</Form.Label>
            <Popover.Root>
                <Popover.Trigger
                    {...props}
                    class={cn(
                        buttonVariants({ variant: "outline" }),
                        "border-white/10 bg-gray-950/10 h-14 justify-start pl-5 text-left font-normal w-full",
                        !value && "text-muted-foreground",
                    )}
                >
                    {value
                        ? df.format(value.toDate(getLocalTimeZone()))
                        : "Pick a date"}
                    <CalendarIcon class="ml-auto size-4 opacity-50" />
                </Popover.Trigger>
                <Popover.Content class="w-auto p-0" side="top">
                    <Calendar
                        type="single"
                        value={value as DateValue}
                        bind:placeholder
                        minValue={new CalendarDate(1900, 1, 1)}
                        maxValue={today(getLocalTimeZone())}
                        calendarLabel="Date of birth"
                        captionLayout="dropdown"
                        onValueChange={(v: any) => {
                            if (v) {
                                $formData.dob = v.toString();
                            } else {
                                $formData.dob = "";
                            }
                        }}
                    />
                </Popover.Content>
            </Popover.Root>
            <Form.FieldErrors />
            <input hidden value={$formData.dob} name={props.name} />
        {/snippet}
    </Form.Control>
</Form.Field>
