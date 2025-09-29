import { superValidate } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';
import { fail } from '@sveltejs/kit';
import type { Actions } from './$types';
import { signupSchema } from '$lib/schemas';
import { SIGNUP_URL } from '$lib/constants/api';
export const load = async () => {
  const form = await superValidate(zod(signupSchema));
  return { form };
};

export const actions = {
  default: async ({ request, fetch }) => {
    const form = await superValidate(request, zod(signupSchema));

    if (!form.valid) {
      return fail(400, {
        form,
      });
    }

    try {
      const formData = new FormData();
      for (const key in form.data) {
        if (Object.prototype.hasOwnProperty.call(form.data, key)) {
          formData.append(key, form.data[key]);
        }
      }
      const data = await fetch(SIGNUP_URL, {
        method: 'POST',
        body: formData
      })
      console.log(form.data);
      if (!data.ok) {
        let errorMessage = 'Signup failed. Please try again.';
        try {
          const errorData = await data.json();
          console.error('Error response from server:', errorData);
          if (errorData && typeof errorData.message === 'string') {
            errorMessage = errorData.message;
          }
        } catch (jsonError) {
          console.error('Failed to parse error response:', jsonError);
        }

        return fail(data.status, {
          form,
          message: errorMessage
        });
      }

      return {
        form,
        success: true,
        message: 'Welcome to Gravia! ' + form.data.name,
        redirectTo: '/auth/signup/success'
      };
    }
    catch (error) {
      console.error('Network or server error:', error);
      return fail(500, {
        form,
        message: 'An unexpected error occurred. Please try again later.'
      });
    }
  },
} satisfies Actions;
