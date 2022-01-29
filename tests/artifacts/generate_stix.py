# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os

from stix2.v21 import Bundle, Indicator, Malware, Relationship


def generate_test_stix_file(file_path):
    if os.path.isfile(file_path):
        os.remove(file_path)

    domains = ["example.org"]
    processes = ["Launch"]
    emails = ["foobar@example.org"]
    filenames = ["/var/foobar/txt"]

    res = []
    malware = Malware(name="TestMalware", is_family=False, description="")
    res.append(malware)
    for d in domains:
        i = Indicator(indicator_types=["malicious-activity"], pattern="[domain-name:value='{}']".format(d), pattern_type="stix")
        res.append(i)
        res.append(Relationship(i, "indicates", malware))

    for p in processes:
        i = Indicator(indicator_types=["malicious-activity"], pattern="[process:name='{}']".format(p), pattern_type="stix")
        res.append(i)
        res.append(Relationship(i, "indicates", malware))

    for f in filenames:
        i = Indicator(indicator_types=["malicious-activity"], pattern="[file:name='{}']".format(f), pattern_type="stix")
        res.append(i)
        res.append(Relationship(i, "indicates", malware))

    for e in emails:
        i = Indicator(indicator_types=["malicious-activity"], pattern="[email-addr:value='{}']".format(e), pattern_type="stix")
        res.append(i)
        res.append(Relationship(i, "indicates", malware))

    bundle = Bundle(objects=res)
    with open(file_path, "w+", encoding="utf-8") as f:
        f.write(bundle.serialize(pretty=True))


if __name__ == "__main__":
    generate_test_stix_file("test.stix2")
    print("test.stix2 file created")
