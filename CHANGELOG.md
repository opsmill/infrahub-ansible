# Opsmill.Infrahub Release Notes

This is the changelog for the `opsmill.infrahub` Ansible collection.
All notable changes to this project will be documented in this file.

Issue tracking is located in [GitHub](https://github.com/opsmill/infrahub-ansible/issues).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This project uses [*towncrier*](https://towncrier.readthedocs.io/) and the changes for the upcoming release can be found in <https://github.com/opsmill/infrahub-ansible/tree/stable/changelog/>.

> **Entries for 1.8.0, 1.8.2 and 1.8.3 were never recorded.** This file was
> maintained by hand and fell out of use: the last automated update was in
> January 2025, and those three releases shipped without an entry. They are
> left blank rather than reconstructed from git history, because a
> reconstruction nobody verified is worse than an honest gap. Everything from
> the next release onward is assembled by towncrier from per-change fragments.

<!-- towncrier release notes start -->

## 1.8.1

### New Modules

- `object_file_fetch` — Fetch file content from a CoreFileObject node in Infrahub by UUID or HFID, with optional local save via `dest`.

### Minor Changes

- `node` — Add `file_path` parameter to create or update CoreFileObject schema nodes with an attached file. SHA-1 idempotency prevents re-upload when the file is unchanged.
- `node` — Add `fetch_file` parameter to download and return file content (base64 `binary` + decoded `text`) from a CoreFileObject node in the same task.

## 1.7.0

### New Modules

- `artifact_generate` — Trigger artifact regeneration in Infrahub for a specified target node.

## 1.3.1

## 1.3.0

## 1.2.3

## 1.2.2

## 1.2.1

## 1.2.0

## 1.1.0

## 1.0.8

## 1.0.7

## 1.0.6

## 1.0.5

## 1.0.4

## 1.0.3

## 1.0.2

## 1.0.1

## 1.0.0
