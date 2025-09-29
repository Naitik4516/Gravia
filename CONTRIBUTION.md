# **🤝 Contributing to Gravia**

We're thrilled you're considering contributing to Gravia, the advanced desktop virtual assistant\! Gravia is an ambitious project, and we rely on the community to help us make it smarter, more stable, and more feature-rich.

These guidelines should help you navigate the process of contributing, from reporting a bug to submitting a major feature.

## **🧭 Code of Conduct**

By participating in this project, you are expected to uphold our [Code of Conduct](https://github.com/Naitik4516/Gravia/CODE_OF_CONDUCT.md) (a separate file to be created) or, by default, the Contributor Covenant. Please ensure all interactions are respectful and inclusive.

## **🐞 Reporting Bugs & Suggesting Features**

The best place to start is often in the project's **Issue Tracker**.

### **Reporting a Bug**

If you find an issue, please open a new issue and include the following:

1. **A Clear Title:** A concise description of the bug (e.g., "ASR fails to initialize on macOS").  
2. **Steps to Reproduce:** Detailed, numbered steps that consistently replicate the issue.  
3. **Expected Behavior:** What you thought should happen.  
4. **Actual Behavior:** What actually happened.  
5. **Environment Details:** Your OS, Node/Bun version, Python version, and any relevant API errors from the console.

### **Suggesting a Feature**

We welcome new ideas\! Open a feature request issue and clearly outline:

1. **The Problem:** What user need or pain point does this feature address?  
2. **The Proposed Solution:** A brief description of how the feature would work and integrate with Gravia.  
3. **Use Cases:** Examples of how a user would interact with the new feature.

## **🛠️ Your First Code Contribution**

If you're ready to dive into the code, follow this general workflow.

### **1\. Prerequisites and Setup**

Ensure you have your developer environment set up by following the "For Developers" instructions in the **README.md**. You will need the **Backend (Python/FastAPI)** and **Frontend (Tauri/Bun)** environments running locally.

### **2\. Fork and Branch**

1. **Fork** the main gravia repository to your personal GitHub account.  
2. **Clone** your fork to your local machine.  
3. Create a new branch for your contribution. Use a descriptive name based on the type of change:  
   * **Feature:** feat/your-feature-name  
   * **Bug Fix:** fix/issue-number-brief-description  
   * **Documentation:** docs/description

### **3\. Making Changes**

* **Stick to the Style:** Please adhere to the existing code styles (e.g., use **Tailwind CSS** in the frontend, standard Python conventions in the backend).  
* **Write Tests:** For bug fixes, please include a test that fails without your fix and passes with it. For new features, include tests that cover the new functionality.  
* **Keep Changes Focused:** Try to keep your pull request small and focused on a single change, bug, or feature. Larger changes should be split into multiple PRs.

### **4\. Submitting a Pull Request (PR)**

When your changes are ready, push your branch and open a Pull Request against the **main** branch of the original gravia repository.

**In your PR description, please include:**

* **A Detailed Summary** of the changes.  
* **Links to any relevant issues** being addressed (e.g., Fixes \#123).  
* **Screenshots or GIFs** (if the change affects the UI/UX).

### **5\. Review Process**

Maintainers will review your code. This is a collaborative process\! Please be patient, responsive to feedback, and willing to make requested changes. Once the review is complete and all checks pass, your contribution will be merged.

## **✍️ Documentation Contributions**

Documentation is vital\! If you find confusing, missing, or outdated documentation (in the README.md, comments, or future docs), please submit a PR with your suggested improvements. These are often the fastest contributions to review and merge.

Thank you for helping us build Gravia\! We look forward to seeing your contributions.