<p align="center">
     <img src="https://docs.mvt.re/en/latest/mvt.png" width="200" />
</p>

# Mobile Verification Toolkit

[![](https://img.shields.io/pypi/v/mvt)](https://pypi.org/project/mvt/)
[![Documentation Status](https://readthedocs.org/projects/mvt/badge/?version=latest)](https://docs.mvt.re/en/latest/?badge=latest)
[![CI](https://github.com/mvt-project/mvt/actions/workflows/python-package.yml/badge.svg)](https://github.com/mvt-project/mvt/actions/workflows/python-package.yml)
[![Downloads](https://pepy.tech/badge/mvt)](https://pepy.tech/project/mvt)

Mobile Verification Toolkit (MVT) is a collection of utilities to simplify and automate the process of gathering forensic traces helpful to identify a potential compromise of Android and iOS devices.

It has been developed and released by the [Amnesty International Security Lab](https://securitylab.amnesty.org) in July 2021 in the context of the [Pegasus Project](https://forbiddenstories.org/about-the-pegasus-project/) along with [a technical forensic methodology](https://www.amnesty.org/en/latest/research/2021/07/forensic-methodology-report-how-to-catch-nso-groups-pegasus/). It continues to be maintained by Amnesty International and other contributors.

> **Note**
> MVT is a forensic research tool intended for technologists and investigators. It requires understanding digital forensics and using command-line tools. This is not intended for end-user self-assessment. If you are concerned with the security of your device please seek reputable expert assistance.
>

### Indicators of Compromise

MVT supports using public [indicators of compromise (IOCs)](https://github.com/mvt-project/mvt-indicators) to scan mobile devices for potential traces of targeting or infection by known spyware campaigns. This includes IOCs published by [Amnesty International](https://github.com/AmnestyTech/investigations/) and other  research groups.

> **Warning**
> Public indicators of compromise are insufficient to determine that a device is "clean", and not targeted with a particular spyware tool. Reliance on public indicators alone can miss recent forensic traces and give a false sense of security.
>
> Reliable and comprehensive digital forensic support and triage requires access to non-public indicators, research and threat intelligence.
>
>Such support is available to civil society through [Amnesty International's Security Lab](https://securitylab.amnesty.org/get-help/?c=mvt_docs) or through our forensic partnership with [Access Now’s Digital Security Helpline](https://www.accessnow.org/help/).

More information about using indicators of compromise with MVT is available in the [documentation](https://docs.mvt.re/en/latest/iocs/).

## Installation

MVT can be installed from sources or from [PyPI](https://pypi.org/project/mvt/) (you will need some dependencies, check the [documentation](https://docs.mvt.re/en/latest/install/)):

```
pip3 install mvt
```

For alternative installation options and known issues, please refer to the [documentation](https://docs.mvt.re/en/latest/install/) as well as [GitHub Issues](https://github.com/mvt-project/mvt/issues).


## Usage

MVT provides two commands `mvt-ios` and `mvt-android`. [Check out the documentation to learn how to use them!](https://docs.mvt.re/)


## License

The purpose of MVT is to facilitate the ***consensual forensic analysis*** of devices of those who might be targets of sophisticated mobile spyware attacks, especially members of civil society and marginalized communities. We do not want MVT to enable privacy violations of non-consenting individuals.  In order to achieve this, MVT is released under its own license. [Read more here.](https://docs.mvt.re/en/latest/license/)
