import cv2
import numpy as np


def setLabel(img, pts, label):
    (x, y, w, h) = cv2.boundingRect(pts)
    pt1 = (x, y)
    pt2 = (x + w, y + h)
    cv2.rectangle(img, pt1, pt2, (0, 255, 0), 2)
    cv2.putText(img, label, (pt1[0], pt1[1] - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255))


for idx in range(0, 2400):
    for folder in range(0, 4):
        img = cv2.imread(r"D:/source-D/respos-D/Pinokio.HumanDT/test/anchor/" +
                         str(folder) + "/" + str(idx) + ".jpeg")
        height, width, _ = img.shape
        img = img[int(height * 1 / 3):, :]
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cv2.imwrite(r"D:/source-D/respos-D/Pinokio.HumanDT/test/gray/" +
                    str(folder) + "/" + str(idx) + ".jpeg", img_gray)

        ret, imthres = cv2.threshold(img_gray, 100, 255, cv2.THRESH_BINARY)
        cv2.imwrite(r"D:/source-D/respos-D/Pinokio.HumanDT/test/binary/" +
                    str(folder) + "/" + str(idx) + ".jpeg", imthres)
        contours, _ = cv2.findContours(imthres, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for contour in contours:
            approx = cv2.approxPolyDP(contour, cv2.arcLength(contour, True) * 0.02, True)
            vtc = len(approx)
            if vtc > 3:
                setLabel(img, contour, str(vtc))
        cv2.imwrite(r"D:/source-D/respos-D/Pinokio.HumanDT/test/draw/" +
                    str(folder) + "/" + str(idx) + ".jpeg", img)
