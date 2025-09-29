import { superValidate } from "sveltekit-superforms";
import { zod } from "sveltekit-superforms/adapters";
import type { Actions, PageServerLoad } from "./$types";
import { fail } from "@sveltejs/kit";
import { USER_PROFILE_URL } from "$lib/constants/api";
import { profileSchema as formSchema } from "$lib/schemas";


export const load: PageServerLoad = async ({ parent }) => {
    console.log("🔍 Profile page load function called");
    // Get parent data which includes user profile
    const parentData = await parent();

    // Flatten additional_info from parent data for the form
    let initial: Record<string, unknown> = {
        name: "",
        email: "",
        location: "",
        bio: "",
        dob: "",
        gender: "",
    };

    if (parentData.user) {
        const data = parentData.user;
        const info = data?.additional_info ?? {};
        initial = {
            name: data?.name ?? "",
            email: data?.email ?? "",
            location: info?.location ?? "",
            bio: info?.bio ?? "",
            dob: info?.dob ?? "",
            gender: info?.gender ?? "",
        };
    }

    const form = await superValidate(initial, zod(formSchema));

    // Return both form and parent data
    return {
        ...parentData,
        form
    };
};

export const actions = {
    default: async ({ request, fetch }) => {
        const form = await superValidate(request, zod(formSchema));

        if (!form.valid) {
            console.log("Form validation errors:", form.errors);
            return fail(400, { form });
        }

        // Re-nest payload under additional_info for the API
        const { name, email, dob, gender, location, bio } = form.data;
        const payload = {
            name,
            email,
            additional_info: {
                location: location ?? "",
                bio: bio ?? "",
                dob: dob ?? "",
                gender: gender ?? "",
            },
        };

        const res = await fetch(USER_PROFILE_URL, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                ...payload,
                additional_info: {
                    ...payload.additional_info,
                },
            }),
        });

        if (!res.ok) {
            return fail(500, { form });
        }

        let updatedUser: unknown = undefined;
        try {
            updatedUser = await res.json();
        } catch {
        }

        // Return success with updated form data
        return {
            form,
            success: true,
            message: "Profile updated successfully"
        };
    },
} satisfies Actions;
