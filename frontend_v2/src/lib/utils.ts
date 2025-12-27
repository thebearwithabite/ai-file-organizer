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

  // 1. Google Drive Truncation: Keep only what's after "My Drive/"
  const driveMarker = "My Drive/"
  const driveIndex = path.indexOf(driveMarker)
  if (driveIndex !== -1) {
    return path.substring(driveIndex + driveMarker.length)
  }

  // 2. Incoming Local Truncation: Keep "Downloads/" or "Desktop/" and relative path
  const downloadsMarker = "Downloads/"
  const downloadsIndex = path.indexOf(downloadsMarker)
  if (downloadsIndex !== -1) {
    return "Downloads/" + path.substring(downloadsIndex + downloadsMarker.length)
  }

  const desktopMarker = "Desktop/"
  const desktopIndex = path.indexOf(desktopMarker)
  if (desktopIndex !== -1) {
    return "Desktop/" + path.substring(desktopIndex + desktopMarker.length)
  }

  // 3. Fallback to root truncation if provided
  if (root && path.startsWith(root)) {
    let truncated = path.replace(root, '')
    if (truncated.startsWith('/')) truncated = truncated.substring(1)
    return truncated || '/'
  }

  // 4. General Mac Home Truncation
  if (path.startsWith('/Users/')) {
    const parts = path.split('/')
    if (parts.length > 4) {
      return '.../' + parts.slice(-2).join('/')
    }
  }

  return path
}

