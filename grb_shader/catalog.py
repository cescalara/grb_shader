from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Type, Union

import astropy.units as u
import ipyvolume as ipv
import pythreejs
import ipywidgets as widgets
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord

from grb_shader.utils.package_data import get_path_of_data_file


@dataclass
class Galaxy(object):
    name: str
    distance: float
    center: SkyCoord
    radius: float
    ratio: float
    angle: float = 0

    def __post_init__(self):

        # Some useful ellipse properties

        self.a = self.radius / 60  # deg

        self.b = self.a * self.ratio  # deg

        self.area = np.pi * np.deg2rad(self.a) * np.deg2rad(self.b)  # rad

    def contains_point(self, ra: float, dec: float) -> bool:
        """
        does this galaxy contain this point?

        Assumes galaxy is an ellipse with object's properties.

        :param ra:
        :param dec:
        """

        cos_angle = np.cos(np.pi - np.deg2rad(self.angle))
        sin_angle = np.sin(np.pi - np.deg2rad(self.angle))

        # Get xy dist from point to center
        x = ra - self.center.ra.deg
        y = dec - self.center.dec.deg

        # Transform to along major/minor axes
        x_t = x * cos_angle - y * sin_angle
        y_t = x * sin_angle + y * cos_angle

        # Get normalised distance of point to center
        r_norm = x_t ** 2 / (self.a / 2) ** 2 + y_t ** 2 / (self.b / 2) ** 2

        if r_norm <= 1:

            return True

        else:

            return False


@dataclass
class LocalVolume(object):
    galaxies: Dict[str, Galaxy]

    @classmethod
    def from_lv_catalog(cls) -> "LocalVolume":
        """
        Construct a LocalVolume from the LV catalog
        """
        output = {}

        table = pd.read_csv(
            get_path_of_data_file("lv_catalog.txt"),
            delim_whitespace=True,
            header=None,
            na_values=-99.99,
            names=["name", "skycoord", "radius", "ratio", "distance"],
        )

        for rrow in table.iterrows():

            row = rrow[1]

            sk = parse_skycoord(row["skycoord"], row["distance"])

            galaxy = Galaxy(
                name=row["name"],
                distance=row["distance"],
                center=sk,
                radius=row["radius"],
                ratio=row["ratio"],
            )

            output[row["name"]] = galaxy

        return cls(output)

    def sample_angles(self, seed=None):
        """
        Sample random orientations for galaxies.
        """

        if seed:
            np.random.seed(seed)

        for name, galaxy in self.galaxies.items():

            galaxy.angle = np.random.uniform(0, 360)

    def intercepts_galaxy(
        self, ra: float, dec: float
    ) -> Tuple[bool, Union[Galaxy, None]]:
        """
        Test if the sky point intecepts a galaxy in the local volume
        and if so return that galaxy
        """

        for name, galaxy in self.galaxies.items():

            if galaxy.contains_point(ra, dec):
                return True, galaxy

        else:

            return False, None

    def percentage_sky_cover(self):

        total_area = 0

        for name, galaxy in self.galaxies.items():

            if not np.isnan(galaxy.area):

                total_area += galaxy.area

        fraction_sky_cover = total_area / (4 * np.pi)

        return fraction_sky_cover * 100

    def __dir__(self):
        # Get the names of the attributes of the class
        l = list(self.__class__.__dict__.keys())

        # Get all the children
        l.extend([x.name for k, x in self.galaxies.items()])

        return l

    def __getattr__(self, name):
        if name in self.galaxies:
            return self.galaxies[name]
        else:
            return super().__getattr__(name)

    def display(self):

        fig = ipv.figure()

        ipv.pylab.style.box_off()
        ipv.pylab.style.axes_off()
        ipv.pylab.style.set_style_dark()
        # ipv.pylab.style.background_color(background_color)

        xs = []
        ys = []
        zs = []

        for k, v in self.galaxies.items():

            xyz = v.center.cartesian.xyz.to("Mpc").value

            xs.append(xyz[0])
            ys.append(xyz[1])
            zs.append(xyz[2])

        ipv.scatter(
            np.array(xs),
            np.array(ys),
            np.array(zs),
            marker="sphere",
            size=0.5,
            color="white",
        )

        fig.camera.up = [1, 0, 0]
        control = pythreejs.OrbitControls(controlling=fig.camera)
        fig.controls = control
        control.autoRotate = True
        fig.render_continuous = True
        control.autoRotate = True
        toggle_rotate = widgets.ToggleButton(description="Rotate")
        widgets.jslink((control, "autoRotate"), (toggle_rotate, "value"))
        r_value = toggle_rotate

        ipv.show()

        return r_value


def parse_skycoord(x: str, distance: float) -> SkyCoord:
    """
    parse the archaic sailor version of
    coordinate into an astropy SkyCoord
    """

    sign = "+" if ("+" in x) else "-"

    ra, dec = x.split(sign)

    ra_string = f"{ra[:2]}h{ra[2:4]}min{ra[4:]}s"
    dec_str = f"{sign}{dec[:2]}.{dec[2:]}"

    sk = SkyCoord(
        f"{ra_string} {dec_str}",
        distance=distance * u.Mpc,
        frame="icrs",
        unit=(u.hourangle, u.deg),
    )

    return sk


__all__ = ["Galaxy", "LocalVolume"]
