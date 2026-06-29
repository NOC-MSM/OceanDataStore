# Contributing

### **Contributing to OceanDataStore**
---

Thank you for your interest in contributing to **OceanDataStore**!

We welcome contributions from the community to help us support the adoption of Analysis-Ready Cloud Optimised data.

### **Getting Started**
---

To get started with contributing to **OceanDataStore**, please follow the steps below:

#### 1. Create an account on [**GitHub**]([https://github.com/]) if you do not already have one.

#### 2. Raise an Issue in the OceanDataStore GitHub repository [**here**](https://github.com/NOC-MSM/OceanDataStore/issues).

#### 3. Creating your own fork of the OceanDataStore code: 

- Go to the OceanDataStore repository [**here**](https://github.com/NOC-MSM/OceanDataStore) and select `Fork` near the top of the page.
    
- This will create a copy of OceanDataStore under your account on GitHub.

#### 4. Clone your forked repository to your local machine:

```bash
git clone https://github.com/your-user-name/OceanDataStore.git

cd OceanDataStore

git remote add upstream https://github.com/NOC-MSM/OceanDataStore.git
```

- This creates the directory ``OceanDataStore`` and connects your repository to the upstream (main) OceanDataStore repository.

#### 5. Creating a Python development environment:

OceanDataStore uses [**Pixi**](https://pixi.sh/latest/) to manage Python development environments.

To get started, you'll need to follow these steps:

- Install Pixi following the instructions [**here**](https://pixi.sh/latest/installation/).

- ``cd`` to your forked `OceanDataStore` directory.

All done! You're now ready to get started contributing to OceanDataStore.

A poweful feature of **Pixi** is its ability to manage multiple environments and define routine development tasks via the `pixi.toml` file.

Using the `pixi task list` command, we can see see the following tasks are available:

```
Tasks that can run on this machine:
-----------------------------------
docs, test

Task  Description
docs  Run the MkDocs built-in development server to build docs locally.
test  Run OceanDataStore unit tests using pytest.
```

To see all available environments and tasks, use the `pixi info` command.

Next, we can enter the development environment `dev` using:

```bash
pixi shell -e dev
```

This is similar to "activating" an environment in Conda. To exit this shell type ``exit`` or press ``Ctrl-D``.

Note, we can also use this Pixi development environment within Jupyter Notebooks when editing or creating new OceanDataStore recipes.

#### 6. Create a new branch for your contribution:

Before making any changes to OceanDataStore, create a new branch to ensure your `main` branch contains only production-ready code using:

```bash
git checkout -b my-new-feature
```
To add your feature branch to your GitHub fork of OceanDataStore, push this new branch to your GitHub repository using:

```bash
git push origin my-new-feature
```

#### 7. Add your new recipe or improvements to the codebase:

- Follow the [NumPy docstring conventions](https://numpydoc.readthedocs.io/en/latest/format.html) when adding or modifying docstrings.

- Follow the [PEP 8](https://peps.python.org/pep-0008/) style guide when writing code.

#### 8. Test your changes thoroughly to ensure they work as expected:

Add new unit tests using [**pytest**](https://docs.pytest.org/en/stable/) as required and then run the `test` task to execute the OceanDataStore test suite using **Pixi** as follows:

```bash
pixi run test
```

#### 9. Commit all your changes with clear and descriptive commit messages.

#### 10 . Document your changes in the User Guide and How To.. sections of the documentation where applicable.

#### 11. Push your finalised changes to your forked repository.

#### 12. Submit a Pull Request to the main branch of OceanDataStore.

### **Code Guidelines**
---

When contributing code to **OceanDataStore**, please adhere to the following guidelines:

- Follow the coding style and conventions used in the existing codebase.
- Write clear and concise code with appropriate comments.
- Ensure your code is well-tested using pytest and does not introduce any regressions.
- Make sure your changes are scalable using dask.
- Document any new features or changes in the appropriate sections of the documentation.


### **Bug Reports and Feature Requests**
---

If you find any bugs or have ideas for new features, please open an [issue](https://github.com/NOC-MSM/OceanDataStore/issues) on the **OceanDataStore** GitHub repository.

Provide as much detail as possible, including steps to reproduce the issue or a clear description of the desired feature.


### **Community Guidelines**
---

When participating in the **OceanDataStore** community, please be respectful and considerate towards others. Follow the code of conduct and engage in constructive discussions.

We appreciate your contributions and look forward to working together to improve **OceanDataStore**!
