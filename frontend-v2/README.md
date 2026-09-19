# Company AI — Clean Redesign V1

A clean rebuild of the public Company AI experience.

Engineering rules:
- No legacy frontend code is imported.
- No patching of the previous UI.
- Content, presentation and behavior are separated.
- Responsive behavior is designed from the first component.
- Language detection is centralized.
- Service taxonomy is data-driven.
- Layan integration is isolated behind a dedicated interface.
- Security-sensitive operations remain server-side.
- No feature is considered complete until static checks, integration checks and live verification pass.

Structure:
- index.html: application shell
- styles/: presentation
- data/: content and service taxonomy
- modules/: behavior
- assets/: redesign assets
