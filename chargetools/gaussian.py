import os

import numpy as np
import periodictable


class GaussianInput:
    def __init__(self, link0, routes,
                 atom_symbols, atom_coords,
                 charge=0, multiplicity=1,
                 title="Title Card Required", extras=None):
        self.link0 = link0
        self.routes = routes

        self.charge = charge
        self.multiplicity = multiplicity
        self.atom_symbols = atom_symbols
        self.atom_coords = atom_coords
        self.title = title
        self.extras = extras or []

    @classmethod
    def read(cls, fname):
        with open(fname, 'r') as f:
            sections = f.read().split("\n\n")

        # Link 0 and Routes
        link0, routes = {}, {}
        routes_started = False
        for line in sections[0].split("\n"):
            if line[0] == '%':
                segments = line[1:].split("=")
                if segments[0] not in link0:
                    link0[segments[0]] = '='.join(segments[1:])

            if line[0] == '#' or routes_started:
                routes_started = True

                if line[0] == '#':
                    line = line[1:]

                route_str = line.split()
                for s in route_str:
                    segments = s.split("=")
                    if len(segments) > 1:
                        routes[segments[0]] = "=".join(segments[1:])
                    else:
                        routes[segments[0]] = None

        title = sections[1]
        charge, multiplicity = map(int, re.match(r"(\d+)\s+(\d+)", sections[2]).groups())

        symbols, coords = [], []
        for line in sections[2].split('\n')[1:]:
            symbol, *coord = line.split()
            symbols.append(symbol)
            coords.append(np.array(coord, dtype=np.float))
        symbols, coords = np.array(symbols), np.array(coords)

        extras = [section for section in sections[3:] if section != '']
        return cls(link0, routes, symbols, coords, charge, multiplicity, title, extras)

    @classmethod
    def read_log(cls, logfname, link0, routes, opt_step=-1, **kwargs):
        import cclib

        parser = cclib.parser.Gaussian(logfname)
        data = parser.parse()

        symbols = []
        for atom_no in data.atomnos:
            symbols.append(periodictable.elements[atom_no].symbol)

        coords = data.atomcoords[opt_step]
        charge = data.charge
        multiplicity = data.mult
        return cls(link0, routes, symbols, coords, charge, multiplicity, **kwargs)

    def save(self, fname, verbose=True, skip_if_exists=False):
        if skip_if_exists:
            if os.path.exists(fname):
                return

        lines = []

        for header, value in self.link0.items():
            if value is None:
                lines.append('%{}'.format(header))
            else:
                lines.append('%{}={}'.format(header, value))

        route_str = "# "
        for keyword, value in self.routes.items():
            if value is None:
                route_str += keyword + " "
            else:
                route_str += "{}={} ".format(keyword, value)
        lines.append(route_str)
        lines.append('')

        lines.append(self.title + "\n")

        lines.append('{} {}'.format(self.charge, self.multiplicity))
        for atom_symbol, atom_coord in zip(self.atom_symbols, self.atom_coords):
            lines.append(
                ' {}                  {:11.8f}    {:11.8f}    {:11.8f}'.format(atom_symbol, *list(atom_coord))
            )
        lines.append('')

        for extra in self.extras:
            lines.append(extra)
            lines.append('')

        lines.append('')

        if "." not in fname:
            fname += ".com"

        with open(fname, 'wb') as f:
            f.write('\n'.join(lines).encode())

        if verbose:
            print("Successfully saved Gaussian input file {}".format(os.path.basename(fname)))

    @staticmethod
    def update_kw(base, *args):
        d = base.copy()
        for arg in args:
            if isinstance(arg, dict):
                d.update(arg)
            elif isinstance(arg, list):
                for elm in arg:
                    d[elm] = None
            elif isinstance(arg, str):
                d[arg] = None
        return d
