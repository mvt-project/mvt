# ADB Analysis Removed

The ability to analyze Android devices directly over the [Android Debug Bridge (adb)](https://developer.android.com/studio/command-line/adb) has been removed from MVT.

Use [AndroidQF](https://github.com/mvt-project/androidqf) to collect forensic artifacts from an Android device, then analyze the collected output with:

```bash
mvt-android check-androidqf /path/to/androidqf-output
```

For a standalone Android bug report, use:

```bash
mvt-android check-bugreport /path/to/bugreport.zip
```

## Reasons for Removal

1. **Inconsistent Data Collection Across Devices**
   Android devices vary significantly in system architecture, security policy, and diagnostic log availability. This made it difficult to collect reliable forensic data across devices.

2. **Incomplete Forensic Data Acquisition**
   Direct ADB analysis did not retrieve a complete forensic snapshot. Critical artifacts such as full bug reports could be missing.

3. **Duplicated Analysis Paths**
   Similar artifacts were parsed through separate ADB, AndroidQF, and bugreport modules, which made behavior harder to keep consistent.

4. **Workflow Consistency**
   MVT now focuses on analyzing acquired artifacts rather than interacting with live devices directly.
