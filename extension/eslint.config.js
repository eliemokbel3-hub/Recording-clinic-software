import tseslint from "typescript-eslint";

export default tseslint.config(
  ...tseslint.configs.recommendedTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    files: ["**/*.ts"],
    rules: {
      // Mirror of the desktop-side logging ban (plan Critical Constraints):
      // no template-literal interpolation of protocol payloads into logs.
      "no-restricted-syntax": [
        "error",
        {
          selector:
            "CallExpression[callee.object.name='console'] TemplateLiteral Identifier[name=/^(message|payload|envelope)$/]",
          message:
            "Do not interpolate protocol messages/payloads into logs (plan Critical Constraints); log whitelisted metadata only.",
        },
      ],
    },
  },
);
