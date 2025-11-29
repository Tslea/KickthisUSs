(function () {
  const validationRules = window.__APP_VALIDATION_RULES || {};

  function getRules(section, field) {
    return (validationRules[section] && validationRules[section][field]) || null;
  }

  function formatMessage(label, type, value) {
    switch (type) {
      case 'required':
        return `${label} è obbligatorio.`;
      case 'min':
        return `${label} deve contenere almeno ${value} caratteri.`;
      case 'max':
        return `${label} non può superare ${value} caratteri.`;
      case 'pattern':
        return `${label} contiene caratteri non ammessi.`;
      default:
        return `${label} non è valido.`;
    }
  }

  function validateField(section, input) {
    const fieldName = input.dataset.validateField;
    const rules = getRules(section, fieldName);
    if (!rules) return null;

    const label = rules.label || fieldName;
    const value = (input.value || '').trim();
    const errors = [];

    if (rules.required && !value) {
      errors.push(formatMessage(label, 'required'));
    }

    if (value && rules.min_length && value.length < rules.min_length) {
      errors.push(formatMessage(label, 'min', rules.min_length));
    }

    if (value && rules.max_length && value.length > rules.max_length) {
      errors.push(formatMessage(label, 'max', rules.max_length));
    }

    if (value && rules.pattern) {
      try {
        const regex = new RegExp(rules.pattern);
        if (!regex.test(value)) {
          errors.push(formatMessage(label, 'pattern'));
        }
      } catch (error) {
        console.warn('Invalid validation regex for', section, fieldName, error);
      }
    }

    if (errors.length) {
      input.setAttribute('aria-invalid', 'true');
      input.classList.add('ring-2', 'ring-red-500');
      return errors[0];
    }

    input.removeAttribute('aria-invalid');
    input.classList.remove('ring-2', 'ring-red-500');
    return null;
  }

  function attachFormValidation(form) {
    const section = form.dataset.validateSection;
    const fields = Array.from(form.querySelectorAll('[data-validate-field]'));
    if (!section || !fields.length) return;

    const summary = form.querySelector('[data-validation-summary]');
    const showSummary = (messages) => {
      if (!summary) return;
      if (!messages.length) {
        summary.classList.add('hidden');
        summary.textContent = '';
        return;
      }
      summary.textContent = messages.join(' ');
      summary.classList.remove('hidden');
    };

    fields.forEach((field) => {
      field.addEventListener('input', () => {
        validateField(section, field);
        showSummary([]);
      });
    });

    form.addEventListener('submit', (event) => {
      const errors = [];
      fields.forEach((field) => {
        const message = validateField(section, field);
        if (message) errors.push(message);
      });

      if (errors.length) {
        event.preventDefault();
        showSummary(errors);
        const firstInvalid = fields.find((field) =>
          field.hasAttribute('aria-invalid')
        );
        if (firstInvalid) firstInvalid.focus();
      } else {
        showSummary([]);
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    document
      .querySelectorAll('form[data-validate-section]')
      .forEach(attachFormValidation);
  });
})();

