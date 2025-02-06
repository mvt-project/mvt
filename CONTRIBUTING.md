# Contributing to Mobile Verification Toolkit (MVT)

We greatly appreciate contributions to MVT!

Your involvement, whether through identifying issues, improving functionality, or enhancing documentation, is very much appreciated. To ensure smooth collaboration and a welcoming environment, we've outlined some key guidelines for contributing below.

## Getting started

Contributing to an open-source project like MVT might seem overwhelming at first, but we're here to support you!

 Whether you're a technologist, a frontline human rights defender, a field researcher, or someone new to consensual spyware forensics, there are many ways to make meaningful contributions.

 Here's how you can get started:

1. **Explore the codebase:**
    - Browse the repository to get familar with MVT. Many MVT modules are simple in functionality and easy to understand.
    - Look for `TODO:` or `FIXME:` comments in the code for areas that need attention.

2. **Check Github issues:**
    - Look for issues tagged with ["help wanted"](https://github.com/mvt-project/mvt/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) or ["good first issue"](https://github.com/mvt-project/mvt/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) to find tasks that are beginner-friendly or where input from the community would be helpful.

3. **Ask for guidance:**

    - If you're unsure where to start, feel free to open a [discussion](https://github.com/mvt-project/mvt/discussions) or comment on an issue.

## How to contribute:

1. **Report issues:**

 - Found a bug? Please check existing issues to see if it's already reported. If not, open a new issue. Mobile operating systems and databases are constantly evolving, an new errors may appear spontaniously in new app versions.

 **Please provide as much information as possible about the prodblem including: any error messages, steps to reproduce the problem, and any logs or screenshots that can help.**


2. **Suggest features:**
    - If you have an idea for new functionality, create a feature request issue and describe your proposal.

3. **Submit code:**
    - Fork the repository and create a new branch for your changes.
    - Ensure your changes align with the code style guidelines (see below).
    - Open a pull request (PR) with a clear description of your changes and link it to any relevant issues.

4. **Documentation contributions:**
    - Improving documentation is just as valuable as contributing code! If you notice gaps or inaccuracies in the documentation, feel free to submit changes or suggest updates.

## Code style
Please follow these code style guidelines for consistency and readability:

- **Indentation**: use 4 spaces per tab.
- **Quotes**: Use double quotes (`"`) by default. Use single quotes (`'`) for nested strings instead of escaping (`\"`), or when using f-formatting.
- **Maximum line length**:
    - Aim for lines no longer than 80 characters.
    - Exceptions are allowed for long log lines or strings, which may extend up to 100 characters.
    - Wrap lines that exceed 100 characters.

Follow [PEP 8 guidelines](https://peps.python.org/pep-0008/) for indentation and overall Python code style. All MVT code is automatically linted with [Ruff](https://github.com/astral-sh/ruff) before merging.

Please check your code before opening a pull request by running `make ruff`


## Community and support

We aim to create a supportive and collaborative environment for all contributors. If you run into any challenges, feel free to reach out through the discussions or issues section of the repository.

Your contributions, big or small, help improve MVT and are always appreciated.