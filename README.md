# 🔍 GitLab Fork Analyzer

An automated tool for analyzing GitLab repository forks based on development activity and license compatibility. The system helps identify actively maintained forks and highlights potential license compatibility risks.

---

## 📖 Overview

Open-source software development relies heavily on repository forking to enable experimentation, customization, and independent evolution of projects. However, GitLab provides limited insight into how forks develop over time. Many repositories accumulate numerous forks, yet only a small portion remain actively maintained.

Contributing to inactive or abandoned forks can lead to wasted effort and reduced collaboration potential. Additionally, differences in open-source licenses between the original repository and its forks may introduce legal and compatibility risks.

This project addresses these challenges by combining fork activity analysis and license compatibility assessment into a single integrated framework.

---

## 🎯 Research Question

> Can GitLab forks be automatically analyzed using repository metadata and activity metrics to reliably identify actively maintained forks and assess license compatibility?

---

## 🚀 Features

- Accepts a public GitLab repository URL as input
- Retrieves fork metadata using the GitLab REST API
- Evaluates development activity metrics:
  - Commit frequency
  - Last commit date
  - Recent activity
  - Contributor patterns
- Ranks forks based on development activity
- Detects license information
- Assesses license compatibility
- Highlights potential license conflicts

---

## 🛠️ How It Works

1. User provides a public GitLab repository URL
2. The system retrieves all forks via the GitLab REST API
3. Metadata and activity metrics are collected
4. License information is extracted
5. Forks are ranked according to maintenance activity
6. License compatibility issues are flagged

---

## 🏗️ System Workflow

User Input (Repository URL)
->
GitLab REST API
->
Fork Metadata Retrieval
->
Activity Analysis
->
License Detection
->
Compatibility Assessment
->
Fork Ranking & Results


## 📊 Evaluation Criteria

Forks are analyzed and ranked based on:

- Recency of commits
- Frequency of updates
- Number of contributors
- Maintenance consistency
- License compatibility with the original repository

---

## 👥 Target Users

- Open-source contributors
- Software developers
- Research students
- Organizations evaluating open-source reuse
- Legal and compliance teams
