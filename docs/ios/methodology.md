# iOS Forensic Methodology

Before jumping into acquiring and analyzing data from an iOS device, you should evaluate what is your precise plan of action. Because multiple options are available to you, you should define and familiarize with the most effective forensic methodology in each case.

#### Filesystem Dump

You will need to decide whether to attempt to jailbreak the device and obtain a full filesystem dump, or not.

While access the full filesystem allows to extract data that would otherwise be unavailable, it might not always be possible to jailbreak a certain iPhone model or version of iOS. In addition, depending on the type of jailbreak available, doing so might compromise some important records, pollute others, or potentially cause unintended malfunctioning of the device later in case it is used again.

If you are not expected to return the phone, you might want to consider to attempt a jailbreak after having exhausted all other options, including a backup.

#### iTunes Backup

An alternative option is to generate an iTunes backup (in most recent version of macOS, they are no longer launched from iTunes, but directly from Finder). While backups only provide a subset of the files stored on the device, in many cases it might be sufficient to at least detect some suspicious artifacts. Backups encrypted with a password will have some additional interesting records not available in unencrypted ones, such as Safari history, Safari state, etc.
