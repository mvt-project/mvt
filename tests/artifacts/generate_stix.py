# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os

from stix2.v21 import Bundle, Indicator, Malware, Relationship


def generate_test_stix_file(file_path):
    if os.path.isfile(file_path):
        os.remove(file_path)

    domains = ["example.org"]
    ip_addresses = ["198.51.100.1"]
    processes = ["Launch"]
    emails = ["foobar@example.org"]
    filenames = ["/var/foobar/txt"]
    android_property = ["sys.foobar"]
    sha256 = ["570cd76bf49cf52e0cb347a68bdcf0590b2eaece134e1b1eba7e8d66261bdbe6"]
    sha1 = ["da0611a300a9ce9aa7a09d1212f203fca5856794"]
    urls = ["http://example.com/thisisbad"]

    res = []
    malware = Malware(name="TestMalware", is_family=False, description="")
    res.append(malware)
    for d in domains:
        i = Indicator(
            indicator_types=["malicious-activity"],
            pattern="[domain-name:value='{}']".format(d),
            pattern_type="stix",
        )
        res.append(i)
        res.append(Relationship(i, "indicates", malware))

    for a in ip_addresses:
        i = Indicator(
            indicator_types=["malicious-activity"],
            pattern="[ipv4-addr:value='{}']".format(a),
            pattern_type="stix",
        )
        res.append(i)
        res.append(Relationship(i, "indicates", malware))

    for p in processes:
        i = Indicator(
            indicator_types=["malicious-activity"],
            pattern="[process:name='{}']".format(p),
            pattern_type="stix",
        )
        res.append(i)
        res.append(Relationship(i, "indicates", malware))

    for f in filenames:
        i = Indicator(
            indicator_types=["malicious-activity"],
            pattern="[file:name='{}']".format(f),
            pattern_type="stix",
        )
        res.append(i)
        res.append(Relationship(i, "indicates", malware))

    for e in emails:
        i = Indicator(
            indicator_types=["malicious-activity"],
            pattern="[email-addr:value='{}']".format(e),
            pattern_type="stix",
        )
        res.append(i)
        res.append(Relationship(i, "indicates", malware))

    for p in android_property:
        i = Indicator(
            indicator_types=["malicious-activity"],
            pattern="[android-property:name='{}']".format(p),
            pattern_type="stix",
        )
        res.append(i)
        res.append(Relationship(i, "indicates", malware))

    for h in sha256:
        i = Indicator(
            indicator_types=["malicious-activity"],
            pattern="[file:hashes.sha256='{}']".format(h),
            pattern_type="stix",
        )
        res.append(i)
        res.append(Relationship(i, "indicates", malware))

    for h in sha1:
        i = Indicator(
            indicator_types=["malicious-activity"],
            pattern="[file:hashes.sha1='{}']".format(h),
            pattern_type="stix",
        )
        res.append(i)
        res.append(Relationship(i, "indicates", malware))

    for u in urls:
        i = Indicator(
            indicator_types=["malicious-activity"],
            pattern="[url:value='{}']".format(u),
            pattern_type="stix",
        )
        res.append(i)
        res.append(Relationship(i, "indicates", malware))

    bundle = Bundle(objects=res)
    with open(file_path, "w+", encoding="utf-8") as f:
        f.write(bundle.serialize(pretty=True))


if __name__ == "__main__":
    generate_test_stix_file("test.stix2")
    print("test.stix2 file created")
