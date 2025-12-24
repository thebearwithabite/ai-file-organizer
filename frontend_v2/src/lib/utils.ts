import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Utility function to merge Tailwind classes
 * Used throughout the app for conditional styling
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Truncates a directory root from a file path for cleaner UI display.
 * @param path The full file path
 * @param root The root path to truncate
 * @returns The truncated path or the original path if root is not found
 */
export function formatPath(path: string | undefined, root: string | undefined): string {
  if (!path) return ''
  if (!root) return path

  if (path.startsWith(root)) {
    // Return path relative to root, ensuring it starts with / or just the relative part
    const truncated = path.replace(root, '')
    return truncated.startsWith('/') ? truncated : `/${truncated}`
  }
  return path
}
