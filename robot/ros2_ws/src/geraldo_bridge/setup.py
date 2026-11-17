from setuptools import find_packages, setup

package_name = "geraldo_bridge"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(include=[package_name, package_name + ".*"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml", "requirements.txt"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Samuel",
    maintainer_email="geraldo@example.com",
    description="Ponte ROS 2 do aplicativo local do G.E.R.A.L.D.O.",
    license="MIT",
    # fastapi e uvicorn vêm do venv do app (requirements.txt), não do Python do sistema: rode com `python -m geraldo_bridge.main`
    entry_points={"console_scripts": ["bridge = geraldo_bridge.main:main"]},
)
