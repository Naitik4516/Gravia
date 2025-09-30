<script lang="ts">
  import Input from "../components/Input.svelte";
  import AuthCard from "../components/AuthCard.svelte";
  import { toast } from "svelte-sonner";
  import { goto } from "$app/navigation";
  import { SIGNUP_URL } from "$lib/constants/api";

  let name = $state('');
  let email = $state('');
  let submitting = $state(false);

  async function handleSubmit(event: Event) {
    event.preventDefault();
    if (submitting) return;

    submitting = true;
    try {
      const formData = new FormData();
      formData.append('name', name);
      formData.append('email', email);

      const res = await fetch(SIGNUP_URL, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        let errorMessage = 'Signup failed. Please try again.';
        const contentType = res.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          try {
            const errorData = await res.json();
            if (errorData && typeof errorData.message === 'string') {
              errorMessage = errorData.message;
            }
          } catch (jsonError) {
            console.error('Failed to parse error response:', jsonError);
          }
        }
        toast.error(errorMessage);
      } else {
        toast.success('Welcome to Gravia! ' + name);
        await goto('/auth/signup/success');
      }
    } catch (error) {
      console.error('Network or server error:', error);
      toast.error('An unexpected error occurred. Please try again later.');
    } finally {
      submitting = false;
    }
  }
</script>


<AuthCard
  title="Account Details"
  subtitle="This helps me create a personalized experience for you."
  primaryButton="Create Account"
  onsubmit={handleSubmit}
  {submitting}
>
  <Input
    type="text"
    name="name"
    placeholder="Name"
    iconname="User"
    bind:value={name}
  />
  <Input
    type="email"
    name="email"
    placeholder="Email"
    iconname="Mail"
    bind:value={email}
  />
</AuthCard>
