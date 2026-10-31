from datetime import datetime, timezone


def on_config(config, **kwargs):
    year = datetime.now(timezone.utc).year
    config["copyright"] = (
        f"Copyright &copy; 2021-{year} MVT Project Developers"
    )
    return config
