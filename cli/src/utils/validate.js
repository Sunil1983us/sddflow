// Input validation for project/feature names.

const INVALID_CHARS = ['"'];

export function validateName(value, label) {
  for (const ch of INVALID_CHARS) {
    if (value.includes(ch)) {
      return `${label} cannot contain ${ch === '"' ? 'double-quote' : ch} characters — ` +
             `they break YAML string serialization. Please use a different name.`;
    }
  }
  if (value.trim().length === 0) {
    return `${label} cannot be empty.`;
  }
  return true; // inquirer convention: true = valid
}

export function assertValidName(value, label) {
  const result = validateName(value, label);
  if (result !== true) throw new Error(result);
}
