import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { fail, redirect } from '@sveltejs/kit';
import type { Actions } from './$types';
import { preferencesSchema } from '$lib/schemas';
import { toast } from "svelte-sonner";
import { SETTINGS_UPDATE_CATEGORY_URL } from '$lib/constants/api';

export const load = async () => {
  const form = await superValidate(zod(preferencesSchema));
  return { form };
};

export const actions = {
  default: async ({ request , fetch}) => {
    const form = await superValidate(request, zod(preferencesSchema));

    if (!form.valid) {
      return fail(400, {
        form,
      });
    }

    console.log('Form data:', form.data);
    fetch(SETTINGS_UPDATE_CATEGORY_URL, {
      method: 'PUT',
      body: JSON.stringify({ category: "personalization", settings: form.data }),
      headers: {
        'Content-Type': 'application/json',
      },
    })
      .then((response) => {
        if (response.ok) {
          console.log('Preferences saved successfully');
          toast.success('Preferences saved successfully');
          redirect(303, '/');
        } else {
          toast.error('Failed to save preferences');
          return fail(500, {
            form,
            error: 'Failed to save preferences',
          });
        }
      })
      .catch((error) => {
        toast.error('An error occurred while saving preferences');
        console.error('Fetch error:', error);
        return fail(500, {
          form,
          error: 'An error occurred while saving preferences',
        });
      });
  },
} satisfies Actions;
