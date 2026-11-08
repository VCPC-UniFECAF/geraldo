from setuptools import find_packages, setup

package_name = "geraldo_dispatcher"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools", "pyyaml"],
    zip_safe=True,
    maintainer="Samuel",
    maintainer_email="geraldo@example.com",
    description="Dispatcher do G.E.R.A.L.D.O.",
    license="MIT",
    entry_points={"console_scripts": ["dispatcher = geraldo_dispatcher.node:main"]},
)
