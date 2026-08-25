# Installation and security notices

This guide explains the alerts that can appear when opening EmoVest downloaded from [GitHub Releases](https://github.com/ELROKA02/EmoVest/releases). Always download the application from that official page.

## macOS: opening EmoVest when Gatekeeper blocks it

EmoVest is currently distributed outside the Mac App Store, and the published build is not signed or notarized by Apple. As a result, macOS may block the application through Gatekeeper the first time you try to open it.

This alert does not, by itself, mean that EmoVest contains malware. It means macOS cannot verify a developer identity through Apple's signing program. EmoVest is open source, and you can inspect its code in this repository before running it.

### Recommended method

1. Download EmoVest from [GitHub Releases](https://github.com/ELROKA02/EmoVest/releases).
2. Open the downloaded file and move `EmoVest.app` to the **Applications** folder if the download requires it.
3. Try to open EmoVest normally.
4. If macOS blocks it, open **System Settings**.
5. Go to **Privacy & Security**.
6. Find the message saying that EmoVest was blocked.
7. Click **Open Anyway**.
8. Confirm the action if macOS asks for your password or Touch ID.
9. Open EmoVest again.

You will normally only need to do this the first time you open that copy of the application.

### Advanced solution: Terminal

Use this alternative only if the recommended method does not work. Before running the command, check that EmoVest is in the **Applications** folder and came from the official GitHub release.

In Terminal, run:

```bash
xattr -dr com.apple.quarantine /Applications/EmoVest.app
```

This command recursively removes the `com.apple.quarantine` attribute **only** from `/Applications/EmoVest.app`. macOS adds this attribute to many files downloaded from the internet so Gatekeeper can ask for confirmation before opening them. It does not disable Gatekeeper or change protection for other apps or for the system.

Then open EmoVest with:

```bash
open /Applications/EmoVest.app
```

We do not recommend globally disabling macOS security protections.

## Windows: SmartScreen or “unknown publisher” warning

On Windows, SmartScreen may show an alert such as “Windows protected your PC” or identify the publisher as unknown when you run an installer downloaded from GitHub. As with macOS, the alert is not itself a malware detection: Windows cannot associate the file with a verified identity when the installer does not include a recognized Authenticode signature or has not yet built SmartScreen reputation.

Windows signing (Authenticode) and macOS signing (Apple Developer ID and notarization) require certificates, identity verification, and platform-specific processes. EmoVest does not yet use those credentials for its current public distribution. That is why the system may appear to distrust the application even though the code is public and reviewable.

To reduce risk:

- Download EmoVest only from the official [GitHub Releases](https://github.com/ELROKA02/EmoVest/releases).
- Inspect the source code in this repository before running the application if you want to understand how it works.
- Do not globally disable macOS or Windows security protections to install EmoVest.

The current lack of signing/notarization explains these warnings; it is not, by itself, a conclusion about the safety of the code. If the system shows a different alert or you suspect the file did not come from the official release, do not run it and open an issue in the repository.
