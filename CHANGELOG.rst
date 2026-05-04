==============================
Opmisll.Infrahub Release Notes
==============================

.. contents:: Topics

v1.9.0
======

New Modules
-----------

- ``object_file_fetch`` - Fetch file content from a CoreFileObject node in Infrahub by UUID or HFID, with optional local save via ``dest``.

Minor Changes
-------------

- ``node`` - Add ``file_path`` parameter to create or update CoreFileObject schema nodes with an attached file. SHA-1 idempotency prevents re-upload when the file is unchanged.
- ``node`` - Add ``fetch_file`` parameter to download and return file content (base64 ``binary`` + decoded ``text``) from a CoreFileObject node in the same task.

v1.7.0
======

New Modules
-----------

- ``artifact_generate`` - Trigger artifact regeneration in Infrahub for a specified target node.

v1.3.1
======

v1.3.0
======

v1.2.3
======

v1.2.2
======

v1.2.1
======

v1.2.0
======

v1.1.0
======

v1.0.8
======

v1.0.7
======

v1.0.6
======

v1.0.5
======

v1.0.4
======

v1.0.3
======

v1.0.2
======

v1.0.1
======

v1.0.0
======

