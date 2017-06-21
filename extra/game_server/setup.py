try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name="ctf-game-server",
      author="Alexandru Budesteanu",
      author_email="alex.budesteanu@gmail.com",
      version="1.0.0",
      packages=["ctf_game_server"],
      install_requires=[
          'Flask>=0.10.1',
          'Flask-SQLAlchemy',
          'docker'
      ]
)