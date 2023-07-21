# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
from mvt.android.utils import warn_android_patch_level


INTERESTING_PROPERTIES = [
    "gsm.sim.operator.alpha",
    "gsm.sim.operator.iso-country",
    "persist.sys.timezone",
    "ro.boot.serialno",
    "ro.build.version.sdk",
    "ro.build.version.security_patch",
    "ro.product.cpu.abi",
    "ro.product.locale",
    "ro.product.vendor.manufacturer",
    "ro.product.vendor.model",
    "ro.product.vendor.name",
]


class GetPropDetectionMixin(object):
    """Mixin to have cosistent detection logic across various extraction modules."""

    def check_indicators(self) -> None:
        for entry in self.results:
            if entry["name"] in INTERESTING_PROPERTIES:
                self.log.info("%s: %s", entry["name"], entry["value"])

            if entry["name"] == "ro.build.version.security_patch":
                warn_android_patch_level(entry["value"], self.log)

        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_android_property_name(result.get("name", ""))
            print(result.get("name", ""), ioc)
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)


ANDROID_DANGEROUS_SETTINGS = [
    {
        "description": "disabled Google Play Services apps verification",
        "key": "verifier_verify_adb_installs",
        "safe_value": "1",
    },
    {
        "description": "disabled Google Play Protect",
        "key": "package_verifier_enable",
        "safe_value": "1",
    },
    {
        "description": "disabled Google Play Protect",
        "key": "package_verifier_user_consent",
        "safe_value": "1",
    },
    {
        "description": "disabled Google Play Protect",
        "key": "upload_apk_enable",
        "safe_value": "1",
    },
    {
        "description": "disabled confirmation of adb apps installation",
        "key": "adb_install_need_confirm",
        "safe_value": "1",
    },
    {
        "description": "disabled sharing of security reports",
        "key": "send_security_reports",
        "safe_value": "1",
    },
    {
        "description": "disabled sharing of crash logs with manufacturer",
        "key": "samsung_errorlog_agree",
        "safe_value": "1",
    },
    {
        "description": "disabled applications errors reports",
        "key": "send_action_app_error",
        "safe_value": "1",
    },
    {
        "description": "enabled installation of non Google Play apps",
        "key": "install_non_market_apps",
        "safe_value": "0",
    },
]


class SettingsDetectionMixin(object):
    def check_indicators(self) -> None:
        for namespace, settings in self.results.items():
            for key, value in settings.items():
                for danger in ANDROID_DANGEROUS_SETTINGS:
                    # Check if one of the dangerous settings is using an unsafe
                    # value (different than the one specified).
                    if danger["key"] == key and danger["safe_value"] != value:
                        self.log.warning(
                            'Found suspicious "%s" setting "%s = %s" (%s)',
                            namespace,
                            key,
                            value,
                            danger["description"],
                        )
                        break


class ProcessDetectionMixin(object):
    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            proc_name = result.get("proc_name", "")
            if not proc_name:
                continue

            # Skipping this process because of false positives.
            if result["proc_name"] == "gatekeeperd":
                continue

            ioc = self.indicators.check_app_id(proc_name)
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

            ioc = self.indicators.check_process(proc_name)
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
