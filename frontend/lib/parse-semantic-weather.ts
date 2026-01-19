/**
 * Semantic parser for weather LLM responses.
 * Detects structural patterns and wraps them in data-semantic attributes
 * for CSS-based typography styling.
 */

// Strip markdown bold/italic since CSS will handle styling
function stripMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '$1') // **bold**
    .replace(/\*(.+?)\*/g, '$1')     // *italic*
    .replace(/__(.+?)__/g, '$1')     // __bold__
    .replace(/_(.+?)_/g, '$1');      // _italic_
}

export function parseSemanticWeather(text: string): string {
  const lines = text.split('\n');
  const result: string[] = [];
  let foundVerdict = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Skip empty lines
    if (!line) {
      result.push('');
      continue;
    }

    // Skip bullet points for verdict detection
    const isBullet = /^[-*•]\s/.test(line);

    // Verdict: first non-bullet line with recommendation words (not a question)
    if (
      !foundVerdict &&
      !isBullet &&
      !line.endsWith('?') &&
      /\b(would|wouldn't|should|shouldn't|don't|recommend|avoid|yes,|no,)\b/i.test(line)
    ) {
      foundVerdict = true;
      result.push(`<p data-semantic="verdict">${stripMarkdown(line)}</p>`);
      continue;
    }

    // Data row variations:
    // 1. "Label: value → interpretation"
    // 2. "**Label:** value (interpretation)"
    // 3. "- **Label:** value (interpretation)" (bullet with bold)
    const dataPatterns = [
      // Standard: Label: value → interpretation
      /^(\*\*)?([A-Za-z][A-Za-z0-9\s\.]+?)(\*\*)?:\s*(.+?)\s*(→|->|–)\s*(.+)$/,
      // Bullet with bold label: - **Label:** value (interpretation)
      /^[-*•]\s*\*\*([A-Za-z][A-Za-z0-9\s\.]+?):\*\*\s*(.+?)(\s*\((.+)\))?$/,
    ];

    // Try standard pattern first
    const standardMatch = line.match(dataPatterns[0]);
    if (standardMatch) {
      const [, , label, , value, , interpretation] = standardMatch;
      result.push(
        `<div data-semantic="data-row">` +
          `<span data-semantic="label">${stripMarkdown(label.trim())}:</span> ` +
          `<span data-semantic="value">${stripMarkdown(value.trim())}</span> ` +
          `<span data-semantic="arrow">→</span> ` +
          `<span data-semantic="interpretation">${stripMarkdown(interpretation.trim())}</span>` +
          `</div>`
      );
      continue;
    }

    // Try bullet+bold pattern
    const bulletMatch = line.match(dataPatterns[1]);
    if (bulletMatch) {
      const [, label, valueAndRest, , interpretation] = bulletMatch;
      // Extract value (everything before parenthetical, or all if no parens)
      const value = interpretation ? valueAndRest.trim() : valueAndRest.trim();
      result.push(
        `<div data-semantic="data-row">` +
          `<span data-semantic="label">${stripMarkdown(label.trim())}:</span> ` +
          `<span data-semantic="value">${stripMarkdown(value)}</span>` +
          (interpretation
            ? ` <span data-semantic="interpretation">${stripMarkdown(interpretation.trim())}</span>`
            : '') +
          `</div>`
      );
      continue;
    }

    // Conditional: starts with "If you"
    if (/^If you\b/i.test(line)) {
      result.push(`<p data-semantic="conditional">${stripMarkdown(line)}</p>`);
      continue;
    }

    // Invitation: contains engagement phrases (but not conditionals)
    if (
      !/^If /i.test(line) &&
      /\b(tell me|let me know|would you like)\b/i.test(line)
    ) {
      result.push(`<p data-semantic="invitation">${stripMarkdown(line)}</p>`);
      continue;
    }

    // Default: pass through unchanged
    result.push(line);
  }

  return result.join('\n');
}
