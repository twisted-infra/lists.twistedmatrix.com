from setuptools import setup

if __name__ == "__main__":
    setup(
        setup_requires=["incremental"],
        use_incremental=True,
        install_requires=[
            "klein",
            "twisted[tls]",
            "txacme",
            "sqlalchemy",
        ],
        license="MIT",
        name="TxLists",
        packages=["txlists",
                  "twisted.plugins"],
        package_dir={"": "src"},
        maintainer='Twisted Matrix Labs',
        maintainer_email='labs@twistedmatrix.com',
    )
