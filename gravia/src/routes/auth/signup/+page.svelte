<script lang="ts">
  import Input from "../components/Input.svelte";
  import AuthCard from "../components/AuthCard.svelte";
  import { signupSchema } from "$lib/schemas";
  import {
    type SuperValidated,
    type Infer,
    superForm,
  } from "sveltekit-superforms";
  import { zodClient } from "sveltekit-superforms/adapters";
  import { toast } from "svelte-sonner";
  import { goto } from "$app/navigation";

  let {
    data,
  }: {
    data: {
      form: SuperValidated<Infer<typeof signupSchema>>;
      message?: string;
      redirectTo?: string;
      success?: boolean;
    };
  } = $props();

  const form = superForm(data.form, {
    validators: zodClient(signupSchema),
    onResult: async ({ result }) => {
      if (!result) return;

      const payload = (result.data ?? {}) as {
        message?: string;
        redirectTo?: string;
        success?: boolean;
      };

      if (result.status && result.status >= 200 && result.status < 300) {
        if (payload.message) {
          toast.success(payload.message);
        }
        if (payload.redirectTo) {
          await goto(payload.redirectTo);
        }
      } else if (result.status && result.status >= 400) {
        toast.error(payload.message ?? "Signup failed. Please try again.");
      }
    },
    onError: ({ result }) => {
      console.error("Signup form submission error:", result);
      toast.error("An unexpected error occurred. Please try again later.");
    },
  });

  const { form: formData, enhance, errors } = form;


</script>


<AuthCard
  title="Account Details"
  subtitle="This helps me create a personalized experience for you."
  primaryButton="Create Account"
  { enhance }
>
  <Input
    type="text"
    name="name"
    placeholder="Name"
    iconname="User"
    bind:value={$formData.name}
    {form}
    {errors}
  />
  <Input
    type="email"
    name="email"
    placeholder="Email"
    iconname="Mail"
    bind:value={$formData.email}
    {form}
    {errors}
  />
</AuthCard>
