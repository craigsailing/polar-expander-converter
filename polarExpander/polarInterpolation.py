import csv
import getopt
import math
import numpy
import sys

from matplotlib import pyplot as plt


class PolarPoint:
    x = 0             # X and Y of a velocity vector from a sin / cos transform
    y = 0
    twa = 0
    tws = 0
    velocity = 0
    inferred = False  # True if this is an inferred calculated from polar on each side else false

    def __init__(self, twa: int, tws: int, velocity: float, inferred: bool):
        self.twa = twa
        self.tws = tws
        self.velocity = velocity
        self.y = round(math.cos(math.radians(twa)) * velocity, 5)
        self.x = round(math.sin(math.radians(twa)) * velocity, 5)
        self.inferred = inferred


class Polars:
    name = "BoatType"
    twa_range = []
    tws_range = []
    polar_data = dict()  # [TWA][TWS][Value] Dict of TWA each one with a Dict of TWS at the prev TWA

    def get_polar(self, twa: int, tws: int):
        return self.polar_data[twa][tws].velocity


def convert_xy_to_velocity(x, y):
    return math.sqrt(x * x + y * y)


def expand_polar(polars: Polars):
    print('Expanding Polar across wind speed and angle')
    # expand on wind speed first to every knot of TWS
    for twa in polars.twa_range:
        # print("========== Adding data for each knot of wind speed for angle: ", twa)
        for index, value in enumerate(polars.tws_range):
            if index < len(polars.tws_range) - 1:
                wind_range = polars.tws_range[index + 1] - value
                v1 = polars.polar_data[twa][polars.tws_range[index + 1]].velocity
                v2 = polars.polar_data[twa][value].velocity
                speed_range = v1 - v2
                speed_change = speed_range / wind_range

                # Add linear polar points across the wind range
                for inc in range(1, wind_range):
                    tmp = PolarPoint(twa, value + inc,
                                     round(polars.polar_data[twa][value].velocity + speed_change * inc, 1),
                                     True)
                    # print(tmp.twa, tmp.tws, tmp.velocity)
                    polars.polar_data[twa][tmp.tws] = tmp

    # Expand on wind angle that is expanded for each knot of wind speed (smooth curve)
    for tws in range(polars.tws_range[0], polars.tws_range[-1] + 1):
        print("TWS ========= ", tws)
        tws_curve = []
        for index, value in enumerate(polars.twa_range):
            tws_curve.append(polars.polar_data[value][tws])
            # print("twa, tws, bs", value, tws, tws_curve[-1].velocity)

        # plot_curve(tws_curve, tws)
        expand_polar_along_curve(tws_curve, tws, polars.twa_range, "up")
        expand_polar_along_curve(tws_curve, tws, polars.twa_range, "down")
    print('Done Expanding')


def expand_polar_along_curve(polar_point_list, tws, tw_angles, mode="up"):
    x1 = []
    y1 = []

    # split the polar to up and downwind sections use different polys for up and downwind
    offset = 0
    for index, value in enumerate(tw_angles):
        if mode == "up" and value <= 100:
            x1.append(polar_point_list[index].x)
            y1.append(polar_point_list[index].y)
        if mode == "down" and value > 100:
            x1.append(polar_point_list[index].x)
            y1.append(polar_point_list[index].y)
            offset = len(tw_angles) - len(x1)

    xpf = numpy.array(x1)
    ypf = numpy.array(y1)
    z = numpy.polyfit(xpf, ypf, 3)  # Upwind is ok on Deg 3 but down wind is bad in the 90 -120 Deg range?
    poly_function = numpy.poly1d(z)

    print("x ", x1)
    print("y ", y1)

    output_list = [round(poly_function(point), 5) for point in x1]
    print('o ', output_list)

    new_x = []
    new_y = []
    for index, value in enumerate(x1):
        if index < len(x1) - 1:
            angle_inc_range = round(x1[index + 1] - value, 5)
            angle_deg_change = tw_angles[offset + index + 1] - tw_angles[offset + index]
            print('angle: ', angle_inc_range, angle_deg_change, tw_angles[offset + index])

            for i in range(1, angle_deg_change):
                new_x.append(value + ((angle_inc_range / angle_deg_change) * i))
                new_y.append(poly_function(new_x[-1]))
                print(90 - int(round(math.degrees(math.atan2(new_y[-1], new_x[-1])))))
                #      convert_xy_to_velocity(new_x, round(poly_function(new_x), 5)))

    # plt.title("Wind Speed: " + str(tws))
    # plot_scatter(x1, y1)
    # plot_scatter(x1, output_list)
    # plot_scatter(new_x, new_y, )
    # plt.show()


def print_deg(x, y):
    for index, value in enumerate(x):
        print(int(round(90 - math.degrees(math.atan2(y[index], value)))))


def plot_curve(polar_point_list, tws):
    plt.title("Polar for :" + str(tws))
    x = [point.x for point in polar_point_list]
    y = [point.y for point in polar_point_list]
    plt.scatter(x, y)
    plt.show()


def save_expanded_polars(output_file: str, polars: Polars):
    with open(output_file, 'w', newline='') as f:
        polar_writer = csv.writer(f, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        # Header row TWA, 5, 6, 7, 8 ...
        header = list(range(polars.tws_range[0], polars.tws_range[-1] + 1))
        header.insert(0, 'twa/tws')
        polar_writer.writerow(header)

        # Write data rows TWA and Speed on the row
        for key in polars.polar_data.keys():
            tmp = [polar.velocity for polar in polars.polar_data[key].values()]
            tmp.insert(0, key)
            polar_writer.writerow(tmp)


def plot_scatter(x, y):
    plt.scatter(x, y)
    plt.show(block=False)


def load_polar(input_file: str, polars: Polars):
    print("Detecting Polar format")
    # Determine file type and load (need to load all polar types)
    with open(input_file, newline='') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            if "!Expedition polar" in row:
                load_expedition_format(input_file, polars)
                break
            elif "TWA" in row:
                load_general_table_format(input_file, polars)
                break
            elif "TWA/TWS" in row:
                load_general_table_format(input_file, polars)
                break
            else:
                print("unknown polar format!")
                raise Exception("Unknown Polar Type")


def load_general_table_format(input_file: str, polars: Polars):
    print("Loading Polar TWA/TWS csv or tab delimited table ...")
    polar_dict_twa = dict()
    with open(input_file, newline='') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            print(row)
            # polar_points = []
            if reader.line_num == 1:
                polars.tws_range = [int(i) for i in row[1:]]
            else:
                polar_dict_tws = dict()
                polars.twa_range.append(int(row[0]))
                for index, point in enumerate(row[1:]):
                    polar_dict_tws[polars.tws_range[index]] = PolarPoint(int(row[0]),
                                                                         polars.tws_range[index],
                                                                         float(point),
                                                                         False)
                polar_dict_twa[int(row[0])] = polar_dict_tws
    polars.polar_data = polar_dict_twa


def load_expedition_format(input_file: str, polars: Polars):
    #  Blue-water and Expedition follow this format of TWA TWS1 BSP1 TWST2 BSP2 on single row
    print("Loading Expedition format: " + input_file)

    with open(input_file, newline='') as f:
        line1 = f.readline().strip()
        if line1 != "!Expedition polar":
            print("File format not correct. Expedition expected line 1 to be: !Expedition polar")

        for line in f:
            print(line)
            line = line.strip()
            data = line.split('\t')

            tws = 0
            twa = 0
            for index, item in enumerate(data):
                if index == 0:
                    tws = int(round(float(item)))
                    polars.tws_range.append(tws)
                    continue

                if index % 2 == 0:
                    bsp = float(item)
                    polar_point = PolarPoint(twa, int(tws), bsp, False)
                    polars.polar_data[twa][tws] = polar_point

                else:
                    twa = int(round(float(item)))
                    if twa not in polars.twa_range:
                        polars.twa_range.append(twa)
                        polars.polar_data[twa] = dict()


def load_bandg(input_file: str, polars: Polars):
    print("Loading Expedition format:" + input_file)
    print("Not implemented")
    print(polars)


def load_maxsea(input_file: str, polars: Polars):
    print("Loading maxsea format: " + input_file)
    print("Not implemented !")
    print(polars)
    # Tab delimited with first cell TWA and TWS as Col


def save_polar_in_expedition_format(output_file: str, polars: Polars):
    print("Saving polar in Expedition Marine Nav format")
    with open(output_file, 'w', newline='') as f:
        f.write("!Expedition polar\n")
        for wind_speed in polars.tws_range:
            line = str(wind_speed) + "\t"
            for wind_angle in polars.twa_range:
                line = line + str(wind_angle) + "\t"
                line = line + str(polars.polar_data.get(wind_angle).get(wind_speed).velocity) + "\t"
            line = line + "\n"
            print(line)
            f.write(line)


def save_row_level_csv(output_file: str, polars: Polars):
    print("Saving polar in row level expansion for data analysis SQL, PowerBI or Tableau")
    with open(output_file, 'w', newline='') as f:
        f.write("TWS,TWA,BPS\n")
        for wind_speed in polars.tws_range:
            for wind_angle in polars.twa_range:
                try:
                    f.write(str(wind_speed) + "," + str(wind_angle) + "," +
                            str(polars.polar_data.get(wind_angle).get(wind_speed).velocity) + "\n")
                except Exception as e:
                    print('Missing value for index at: TWA, ' + str(wind_angle) + ", TWS " + str(wind_speed))
                    print(e)


def print_help():
    print('polarInterpolation.py -i <input file> -o <output file> '
          'default operation expands to 1 deg and 1 knot resolution')
    print('-c converts to expedition pol format from TWS/TWA table format with no expansion')
    print('-r will expand to row level csv with columns TWA, TWS, BSP useful for SQL join and data analysis')


def main(argv):
    input_file = ""
    output_file = ""
    convert_file = False
    expand_to_rows = False

    try:
        opts, args = getopt.getopt(argv, "i:o:crh", ["ifile=", "ofile=, --convert, --row_convert"])

        for opt, arg in opts:
            if opt == '-h':
                print_help()
                sys.exit(1)

            elif opt in ("-i", "--ifile"):
                input_file = arg
            elif opt in ("-o", "--ofile"):
                output_file = arg
            elif opt in ("-c", "--convert"):
                convert_file = True
            elif opt in ("-r", "--row_convert"):
                expand_to_rows = True
    except getopt.GetoptError:
        print_help()
        sys.exit(2)

    if not input_file or not output_file:
        print_help()
        sys.exit(2)

    print('Loading polars for %s', input_file)
    polars = Polars()
    load_polar(input_file, polars)

    if expand_to_rows:
        print("Expanding to row level for data analysis csv")
        print("File format is TWA TWS BSP column format csv")
        save_row_level_csv(output_file, polars)
        print('Find the output file: ' + output_file)
        sys.exit(0)

    if convert_file:
        print("Converting polar file format to Expedition from TWA/TWS table")
        save_polar_in_expedition_format(output_file, polars)
        print('Find the output file: ' + output_file)
        sys.exit(0)

    # Expand polars main function of this script.
    print("Expanding polars using linear and polynomial expansion across TWS and TWA")
    expand_polar(polars)
    save_expanded_polars(output_file, polars)
    print('Find the expanded output file: ' + output_file)


if __name__ == '__main__':
    main(sys.argv[1:])
