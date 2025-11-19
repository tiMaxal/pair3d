## Changesets:
 - Whenever making a change that should bump the version - Run:
`npm run changeset`
  - read the committed changeset files and updates the versions accordingly
`npx changeset version`

### tl;dr
## **auto-git-ver.private.howto**
 [ perplexity-ai 20250713tdwm]

To set up **Changesets** for **_auto versioning_** triggered by changeset file commits, using Windows and GitHub Desktop, follow these explicit steps:

### 1. **_Prerequisites_**
- Node.js installed on your system.
-Your project is a git repository (already on GitHub, managed in GitHub Desktop).
-GitHub Desktop is installed and configured.

### 2. **_Install_** Changesets
- Open a terminal (e.g., Command Prompt, PowerShell, or VS Code terminal)
 _at your project root_ and run:
`bash`
npm install --save-dev @changesets/cli

### 3. **_Initialize_** Changesets
- Still in the terminal, run:
`bash`
npx changeset init
  - This creates a `.changeset folder` and a config file (e.g., .changeset/config.json).

### 4. _Add Scripts_ to package.json
- Add these scripts to your package.json for convenience:
`json`
```
"scripts": {
  "changeset": "changeset",
  "version-packages": "changeset version"
}
```
 - "changeset": 
    - creates a new changeset file.
        - Runs the Changesets CLI to create a new changeset file.
        - This launches an interactive prompt asking which package(s) are affected, what type of version bump you want (patch, minor, major), and a summary of the change.
 - "version-packages": 
    - applies version bumps and updates changelogs based on committed changeset files.
      - Applies all committed changeset files - bumps the version(s) in `package.json`, updates changelogs, and prepares the repo for release.

### 5. **_Create_** a Changeset File
- Whenever making a change that should bump the version - Run:
`bash`
npm run changeset
  - Answer the prompts to specify the type of bump (major/minor/patch) and a summary.
- This generates a Markdown file in .changeset/.

### 6. **_Commit_** the Changeset File
- Open GitHub Desktop.
- You will see the new changeset file in the "Changes" tab.
- Add any other changes you want to commit.
- Write a commit message and commit the changeset file along with your code.

### 7. **_Push_** to GitHub
- In GitHub Desktop, click Push origin to send your commit (including the changeset file) to GitHub.

### 8. Set Up **_GitHub Actions_** for Automation
- Create a workflow file at .github/workflows/release.yml in your repo (can be done in VS Code):
`text`

```
name: Version Packages

on:
  push:
    branches:
      - main  # or your default branch

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - run: npm ci
      - run: npx changeset version
      - run: git config user.name "github-actions[bot]"
      - run: git config user.email "github-actions[bot]@users.noreply.github.com"
      - run: git add .
      - run: git commit -m "Version Packages" || echo "No changes to commit"
      - run: git push
```
  - This workflow will automatically bump versions
     and update changelogs when you push a commit
      with a changeset file, to your default branch.

### 9. (Optional) Publishing
- If you want to publish to npm, add a step for npx changeset publish and set up your NPM_TOKEN as a secret.


## How It Works
  - Edit or create a changeset file (in VS Code or any editor).
  - Commit and push using GitHub Desktop.
  - GitHub Actions workflow detects the new changeset file, applies the version bump, 
      updates changelogs, and (optionally) publishes.


- # Summary:
  - Changesets files are human-editable and must be committed to the repo.
  - GitHub Desktop handles the commit and push.
  - GitHub Actions automates the versioning and changelog update when changeset files are pushed.
  - No need to run versioning commands locally — the automation happens on GitHub after pushing the changeset file.



#  to do Manually 

How to create version tags in GitHub Desktop:
- Commit all changes first.
- Click “Repository” → “Open in Terminal” (or use Git Bash or PowerShell).
- Run ..

`bash:`
git tag v1.3.0
git push origin v1.3.0

[Or on Windows]
`powershell`
git tag v1.3.0; git push origin v1.3.0

- 🚀 Result: This pushes a new v1.3.0 tag to GitHub
- Any GitHub Actions workflow watching tags: ['v*'] is triggered
- You can use the tag as a downloadable release
- 🔄 You can also delete a tag with:
git tag -d v1.3.0 (local) and git push origin --delete v1.3.0 (remote)



- **build** exe: [Set-Location -LiteralPath E:\images_stereo_bak\stereo_software\pair3d[ai]\pair3d]
C:\Users\timax\AppData\Roaming\Python\Python313\Scripts\pyinstaller --onefile --windowed --hidden-import=PIL --hidden-import=imagehash --version-file=version.txt pair3d.v1-3.py --name pair3d



# **🔐 1. Generate a GPG Key (if you don’t already have one)**
 On local machine (Linux/macOS/Windows WSL/PowerShell with GPG):

`bash`
gpg --full-generate-key

 Choose:
- RSA + RSA
- Key size: 4096
- Validity: 0 (never expires) or 1y
- Name and email (can match GitHub)
- Passphrase: choose a strong one

📄 2. Export Your GPG Private Key
 Run `bash`:
gpg --armor --export-secret-keys "Your Name or Email"

- Copy the entire output — it looks like:
-----BEGIN PGP PRIVATE KEY BLOCK-----
...
-----END PGP PRIVATE KEY BLOCK-----

 🛠 3. Add Secrets to GitHub
- Go to your repository on GitHub
- Click ⚙️ Settings (top bar)
- Scroll down to Secrets and variables → Actions
- Click New repository secret
- Add two secrets:
 GPG_PRIVATE_KEY
Paste the entire armored private key block from step 2
 GPG_PASSPHRASE
Enter the passphrase you used when creating the key

 🔐 Example GitHub Actions Use
 After adding those secrets, you can import the key and sign like this:
- yaml
      - name: Import GPG key
        run: |
          echo "${{ secrets.GPG_PRIVATE_KEY }}" | gpg --batch --import
          echo "allow-loopback-pinentry" >> ~/.gnupg/gpg.conf
          echo "use-agent" >> ~/.gnupg/gpg.conf
          echo RELOADAGENT | gpg-connect-agent
        shell: bash

      - name: Sign checksums
        run: |
          gpg --batch --yes --pinentry-mode loopback --passphrase "${{ secrets.GPG_PASSPHRASE }}" \
            --output artifacts/checksums.sha256.asc \
            --armor --detach-sign artifacts/checksums.sha256
- You can include this block in your release job after generating the checksum file.


