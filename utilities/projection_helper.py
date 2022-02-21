class ProjectionManager():
    @staticmethod
    def get_matrix(xPt, yPt, video_name: str, matrices):
        if video_name == "LOADING DOCK F3 Rampa 13 - 14":
            if ((-8 / 3 * xPt + 1600) > yPt) and ((-25 / 39 * xPt + 1120) > yPt):
                matrix = matrices[0]
            elif ((-8 / 3 * xPt + 1600) < yPt) and ((-25 / 39 * xPt + 1120) > yPt):
                matrix = matrices[1]
            elif ((-8 / 3 * xPt + 1600) < yPt) and ((-25 / 39 * xPt + 1120) < yPt):
                matrix = matrices[2]
            return matrix
        elif video_name == "LOADING DOCK F3 Rampa 11-12":
            if ((-8 * xPt + 4800) > yPt) and ((-35 / 29 * xPt + 1645) > yPt):
                matrix = matrices[0]
            elif ((-8 * xPt + 4800) < yPt) and ((-35 / 29 * xPt + 1645) > yPt):
                matrix = matrices[1]
            elif ((-8 * xPt + 4800) < yPt) and ((-35 / 29 * xPt + 1645) < yPt):
                matrix = matrices[2]
            return matrix
        elif video_name == "LOADING DOCK F3 Rampa 9-10":
            if ((2 * xPt - 100) < yPt) and ((-80 / 9 * xPt + 6667) > yPt):
                matrix = matrices[0]
            elif ((2 * xPt - 100) > yPt) and ((-80 / 9 * xPt + 6667) > yPt):
                matrix = matrices[1]
            elif ((2 * xPt - 100) > yPt) and ((-80 / 9 * xPt + 6667) < yPt):
                matrix = matrices[2]
            return matrix
