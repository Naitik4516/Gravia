import * as z from "zod";

export const signupSchema = z.object({
  name: z
    .string()
    .min(2, 'Full name must be at least 2 characters')
    .max(50, 'Full name must be at most 50 characters')
    .regex(/^[a-zA-Z\s'-]+$/, 'Full name can only contain letters, spaces, apostrophes, and hyphens'),
  email: z
    .string()
    .email('Please enter a valid email address')
    .max(100, 'Email must be at most 100 characters'),
});

export const preferencesSchema = z.object({
  preferred_name: z.string().optional(),
  response_tone: z.string().optional(),
  response_length: z.string().optional(),
  humour_level: z.string().optional(),
  preferred_language: z.string().optional(),
  custom_instructions: z.string().optional(),
});

export const profileSchema = z.object({
  name: z.string().min(2).max(100),
  email: z.string().email(),
  dob: z.string().optional(),
  gender: z.enum(["Male", "Female", "Other"]).optional(),
  location: z.string().max(100).optional(),
  bio: z.string().max(500).optional(),
});