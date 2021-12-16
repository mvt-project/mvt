import sys
import os
from stix2.v21 import (Indicator, Malware, Relationship, Bundle, DomainName)


if __name__ == "__main__":
    if os.path.isfile("test.stix2"):
        os.remove("test.stix2")

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
        res.append(Relationship(i, 'indicates', malware))

    for p in processes:
        i = Indicator(indicator_types=["malicious-activity"], pattern="[process:name='{}']".format(p), pattern_type="stix")
        res.append(i)
        res.append(Relationship(i, 'indicates', malware))

    for f in filenames:
        i = Indicator(indicator_types=["malicious-activity"], pattern="[file:name='{}']".format(f), pattern_type="stix")
        res.append(i)
        res.append(Relationship(i, 'indicates', malware))

    for e in emails:
        i = Indicator(indicator_types=["malicious-activity"], pattern="[email-addr:value='{}']".format(e), pattern_type="stix")
        res.append(i)
        res.append(Relationship(i, 'indicates', malware))

    bundle = Bundle(objects=res)
    with open("test.stix2", "w+") as f:
        f.write(bundle.serialize(pretty=True))
    print("test.stix2 file created")
