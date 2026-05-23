
# TestSprite AI Testing Report(MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** EmoVest
- **Date:** 2026-05-16
- **Prepared by:** TestSprite AI Team

---

## 2️⃣ Requirement Validation Summary

#### Test TC001 Sign in and land on the dashboard
- **Test Code:** [TC001_Sign_in_and_land_on_the_dashboard.py](./TC001_Sign_in_and_land_on_the_dashboard.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c5404dba-5507-49ca-aa38-87c7f82e404c/0cb4e716-be16-4e90-8fb2-cdc4e75283fa
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC002 Register a new trading member and reach sign in
- **Test Code:** [TC002_Register_a_new_trading_member_and_reach_sign_in.py](./TC002_Register_a_new_trading_member_and_reach_sign_in.py)
- **Test Error:** TEST BLOCKED

The test could not be run — the SPA did not render after submitting the registration form, preventing verification that registration succeeded or that the user was redirected to sign in.

Observations:
- After clicking 'Registrarse' the page content is a bare <div id="root" /> with no success confirmation or login page content visible.
- Multiple waits and a scroll/search for 'Iniciar sesión' did not expose any registration success message or sign-in form.
- The URL remains /signup and the visible UI is blank, so the outcome of the submission cannot be confirmed.
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c5404dba-5507-49ca-aa38-87c7f82e404c/6aaf243d-0583-407b-8024-832dc2115024
- **Status:** BLOCKED
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC003 Register a new account and reach the dashboard
- **Test Code:** [TC003_Register_a_new_account_and_reach_the_dashboard.py](./TC003_Register_a_new_account_and_reach_the_dashboard.py)
- **Test Error:** TEST FAILURE

The new user registration did not complete and the account could not be used to sign in.

Observations:
- After submitting the signup form the app rendered an empty root div with no confirmation or dashboard.
- Attempting to sign in with the created credentials showed 'Credenciales incorrectas'.
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c5404dba-5507-49ca-aa38-87c7f82e404c/7e3f1de6-926b-4097-a0ae-cc3c9684dd0e
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC004 Recover access with a password reset and sign in
- **Test Code:** [TC004_Recover_access_with_a_password_reset_and_sign_in.py](./TC004_Recover_access_with_a_password_reset_and_sign_in.py)
- **Test Error:** TEST BLOCKED

The password reset flow could not be run — the backend is not configured to send recovery emails, so a real reset token cannot be obtained and the rest of the flow cannot be completed.

Observations:
- The page showed the error: "No se pudo enviar el correo de recuperación: ValueError - Falta configuración de correo electrónico en el backend"
- The reset email could not be sent, therefore no reset token is available
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c5404dba-5507-49ca-aa38-87c7f82e404c/2c79eba4-065d-42ce-a190-49c99ff8f164
- **Status:** BLOCKED
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC005 Log out from the user menu
- **Test Code:** [TC005_Log_out_from_the_user_menu.py](./TC005_Log_out_from_the_user_menu.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c5404dba-5507-49ca-aa38-87c7f82e404c/cd6fc8bd-b1c9-40cf-9d25-460d1c20308b
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC006 Keep the email remembered after signing out and closing the session
- **Test Code:** [TC006_Keep_the_email_remembered_after_signing_out_and_closing_the_session.py](./TC006_Keep_the_email_remembered_after_signing_out_and_closing_the_session.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c5404dba-5507-49ca-aa38-87c7f82e404c/39c6fd98-0cbc-4abf-8448-61aface585e1
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC007 Reset access with a new password
- **Test Code:** [TC007_Reset_access_with_a_new_password.py](./TC007_Reset_access_with_a_new_password.py)
- **Test Error:** TEST BLOCKED

The test could not be run — the UI provides no way to obtain a valid password reset token required to complete the flow.

Observations:
- The reset-password page displays the message 'El enlace de restablecimiento es inválido.'
- The current URL is http://localhost:5173/reset-password (no token query parameter)
- The page provides no UI control to generate or request a valid reset token
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c5404dba-5507-49ca-aa38-87c7f82e404c/18829e82-6ebd-4eb0-a236-64e3cc9b00f5
- **Status:** BLOCKED
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC008 Create a trading account and add a trading operation
- **Test Code:** [TC008_Create_a_trading_account_and_add_a_trading_operation.py](./TC008_Create_a_trading_account_and_add_a_trading_operation.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c5404dba-5507-49ca-aa38-87c7f82e404c/f2b53cc1-91ca-4fd6-a9ac-7bc09b70c6aa
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC009 Add a trading operation to a selected account
- **Test Code:** [TC009_Add_a_trading_operation_to_a_selected_account.py](./TC009_Add_a_trading_operation_to_a_selected_account.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c5404dba-5507-49ca-aa38-87c7f82e404c/1cf83bfb-50bb-41f6-b892-526d1df4678f
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC010 View dashboard performance for a selected account and period
- **Test Code:** [TC010_View_dashboard_performance_for_a_selected_account_and_period.py](./TC010_View_dashboard_performance_for_a_selected_account_and_period.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c5404dba-5507-49ca-aa38-87c7f82e404c/80224390-1b13-4be9-bb20-003dad7304b8
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC011 Reach authenticated sections from the main navigation after signing in
- **Test Code:** [TC011_Reach_authenticated_sections_from_the_main_navigation_after_signing_in.py](./TC011_Reach_authenticated_sections_from_the_main_navigation_after_signing_in.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c5404dba-5507-49ca-aa38-87c7f82e404c/c85acd62-1c9c-4e73-9684-e8b310f359da
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC012 Create a trading account from the profile page
- **Test Code:** [TC012_Create_a_trading_account_from_the_profile_page.py](./TC012_Create_a_trading_account_from_the_profile_page.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c5404dba-5507-49ca-aa38-87c7f82e404c/33662b80-f31a-434c-a4b8-94b2bd3f2811
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC013 Edit and delete a trading operation
- **Test Code:** [TC013_Edit_and_delete_a_trading_operation.py](./TC013_Edit_and_delete_a_trading_operation.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c5404dba-5507-49ca-aa38-87c7f82e404c/a606789a-6a96-42f8-8ee9-51a8cfdf34f5
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC014 Edit a trading account and adjust its funds
- **Test Code:** [TC014_Edit_a_trading_account_and_adjust_its_funds.py](./TC014_Edit_a_trading_account_and_adjust_its_funds.py)
- **Test Error:** TEST FAILURE

The profile page does not provide controls to edit trading accounts or update funds from the profile. The UI contains only personal information fields (showing 'Cargando...') and a single 'Editar Perfil (Próximamente)' placeholder button, so the required update flow cannot be performed from /perfil.

Observations:
- The profile page shows 'Editar Perfil (Próximamente)' and no account-management or fund-edit controls.
- Personal information fields display 'Cargando...' placeholders and no trading account entries or edit buttons are present.
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c5404dba-5507-49ca-aa38-87c7f82e404c/dac5f051-84e0-4b6a-8ac9-febee4c597fa
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC015 Request a password reset link
- **Test Code:** [TC015_Request_a_password_reset_link.py](./TC015_Request_a_password_reset_link.py)
- **Test Error:** TEST BLOCKED

The password recovery request could not be completed — the backend is not configured to send email, so the UI cannot show a successful reset confirmation.

Observations:
- The forgot-password page displayed the error: 'No se pudo enviar el correo de recuperación: ValueError - Falta configuración de correo electrónico en el backend'
- The email field contains 'Estadisticas1@gmail.com' and the 'Enviar enlace' action was submitted
- No success/confirmation message (e.g., 'Se ha enviado', 'Revisa tu correo', 'enlace enviado') is visible
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/c5404dba-5507-49ca-aa38-87c7f82e404c/eaf5840f-6a38-4625-abd7-1b18ae89abf1
- **Status:** BLOCKED
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---


## 3️⃣ Coverage & Matching Metrics

- **60.00** of tests passed

| Requirement        | Total Tests | ✅ Passed | ❌ Failed  |
|--------------------|-------------|-----------|------------|
| ...                | ...         | ...       | ...        |
---


## 4️⃣ Key Gaps / Risks
{AI_GNERATED_KET_GAPS_AND_RISKS}
---