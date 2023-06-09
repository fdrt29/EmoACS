from logging import Logger
from typing import Type
import cv2
import os
import shutil
import numpy as np

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Flatten
from tensorflow.keras.layers import Conv2D
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.layers import MaxPooling2D
from tensorflow.keras.preprocessing.image import ImageDataGenerator



import logger


class Camera(object):
    emotDict = {0: "Angry", 1: "Disgusted", 2: "Fearful",
                3: "Happy", 4: "Neutral", 5: "Sad", 6: "Surprised"}

    haar = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    faceCascade = cv2.CascadeClassifier(haar)
    recognizer = cv2.face.LBPHFaceRecognizer_create(
        grid_x=8, grid_y=8
        ) # TODO empirical. from guid: radius=2, neighbors=16, grid_x=8, grid_y=8

    datasetSize = 30
    imgSize = (150, 150)

    confidence = (30, 90)#(65, 100) # TODO empirical. old (30, 90)

    lastFrame = None

    def __init__(self, index=0, drawSquareFace=True, datasetsDir='datasets') -> None:
        """
        Args:
            - index (int, optional): camera index within system. Defaults to 0.
            - drawSquareFace (bool, optional): to draw square on face. Defaults to True.
        """
        self.datasetsDir = datasetsDir
        self.idx = index
        self.videsoStream = cv2.VideoCapture(self.idx, cv2.CAP_DSHOW)
        self.model = Sequential(name=f'model{index}')
        self.drawSquareFace = drawSquareFace
        if not os.path.isdir(self.datasetsDir):
            os.mkdir(self.datasetsDir)

        ret = self.loadmodel()
        if ret:
            logger.saveError(f'Camera {self.idx}: {ret}')
            return

        ret = self.loadImages()
        if ret:
            logger.saveInfo(f'Camera {self.idx}: dataset is empty')
            return

        ret = self.trainRecognizer()
        if ret:
            logger.saveInfo(f'Camera {self.idx}: ret')
        logger.saveInfo(f'Camera {self.idx}: READY')

    def __del__(self):
        self.videsoStream.release()

    def loadmodel(self) -> Exception:
        """
        Adds layers to & Loads weights for\n
        Emotion recognition model

        Returns:
            - Exception: if error occurs
        """
        try:
            self.model.add(Conv2D(32, kernel_size=(3, 3),
                           activation='relu', input_shape=(48, 48, 1)))
            self.model.add(Conv2D(64, kernel_size=(3, 3), activation='relu'))
            self.model.add(MaxPooling2D(pool_size=(2, 2)))
            self.model.add(Dropout(0.25))
            self.model.add(Conv2D(128, kernel_size=(3, 3), activation='relu'))
            self.model.add(MaxPooling2D(pool_size=(2, 2)))
            self.model.add(Conv2D(128, kernel_size=(3, 3), activation='relu'))
            self.model.add(MaxPooling2D(pool_size=(2, 2)))
            self.model.add(Dropout(0.25))
            self.model.add(Flatten())
            self.model.add(Dense(1024, activation='relu'))
            self.model.add(Dropout(0.5))
            self.model.add(Dense(7, activation='softmax'))

            self.model.load_weights('model.h5')
            logger.saveInfo(f'Camera {self.idx}: emotion model loaded')
        except Exception as e:
            return e

    def loadImages(self) -> int:
        """
        Loads data to be recognized:
            - images - datasets images
            - labels - user's id
            - names  - {label : user's name}

        Returns:
            - int: 1 if error occurs
        """
        self.images, self.labels, self.names, id = [], [], {}, 0
        for (subdirs, dirs, files) in os.walk(self.datasetsDir):
            for subdir in dirs:
                self.names[id] = subdir
                subjectpath = os.path.join(self.datasetsDir, subdir)
                for filename in os.listdir(subjectpath):
                    path = subjectpath + '/' + filename
                    self.images.append(cv2.imread(path, 0))
                    self.labels.append(id)
                id += 1
        if not self.images or not self.labels or not self.names:
            return 1

    def trainRecognizer(self) -> Exception:
        """
        Trains face recognizer

        Returns:
            - Exception: if error occurs
        """
        try:
            (images, labels) = [np.array(i)
                                for i in [self.images, self.labels]]
            self.recognizer.train(images, labels)
        except Exception as e:
            return e

    def getNames(self) -> list[str]:
        return self.names

    def readFrame(self):
        """
        Returns:
            - int: 0 if error
            - image: frame image
        """
        return self.videsoStream.read()

    def saveFace(self, Name) -> str:
        """
        Saves 30 jpeg face to datasets

        Args:
            Name (str): User's name

        Returns:
            str: description of error
        """
        path = os.path.join(self.datasetsDir, Name)
        if not os.path.isdir(path):
            os.mkdir(path)

        c = 0
        while c < self.datasetSize:
            ret, frame = self.readFrame()
            if not ret:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.faceCascade.detectMultiScale(gray, 1.3, 4)

            if len(faces) == 0:
                shutil.rmtree(path)
                ret = 'no face detected'
                logger.saveError(f'Camera {self.idx}: {ret}')
                return ret

            if len(faces) > 1:
                shutil.rmtree(path)
                ret = 'multiple faces detected'
                logger.saveError(f'Camera {self.idx}: ret')
                return ret

            for (x, y, w, h) in faces:
                face = gray[y:y + h, x:x + w]
                faceResized = cv2.resize(face, self.imgSize)
                cv2.imwrite(f'{path}/{c}.jpeg', faceResized)
            key = cv2.waitKey(10)
            c += 1
        logger.saveInfo(f'Camera {self.idx}: "{Name}" saved')

        ret = self.loadImages()
        if ret:
            logger.saveInfo(f'Camera {self.idx}: dataset is empty')
            return 'load images'

        ret = self.trainRecognizer()
        if ret:
            logger.saveInfo(f'Camera {self.idx}: ret')
            return 'recognizer training'

        return None

    def toggleDrawSquare(self):
        self.drawSquareFace = not self.drawSquareFace

    def detectFaces(self, frame):
        """
        Detects faces and [optioanlly] puts frame around and emotion above detected face 

        Args:
            - frame (image): image frame

        Returns:
            - frame: same frame (with square and emotion) 
            - grayFaces: array of detected faces grayed
        """
        UI_COLOR = (0, 150, 0)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.faceCascade.detectMultiScale(gray, 1.3, 4)
        grayFaces = []
        for (x, y, w, h) in faces:
            face = gray[y:y + h, x:x + w]
            grayFaces.append(face)
            if not self.drawSquareFace:
                continue

            cv2.rectangle(frame, (x, y), (x + w, y + h), UI_COLOR, 1)
            croppedImg = np.expand_dims(
                np.expand_dims(cv2.resize(face, (48, 48)), -1),
                0
            )
            emotPredictions = self.model.predict(croppedImg, verbose = 0) # TODO параметра verbose = 0 не было
            emotMaxIndex = int(np.argmax(emotPredictions))
            cv2.putText(
                frame, self.emotDict[emotMaxIndex], (x+20, y-60),
                cv2.FONT_HERSHEY_SIMPLEX, 1, UI_COLOR, 2, cv2.LINE_AA
            )
        return frame, grayFaces

    def recognizeFace(self, faces, frame):
        """
        Recognizes face from frame via datasets

        Args:
            - faces (array): array of grayed faces

        Returns:
            - ret (int): 1 if access denied
            - name (str): recognized user's name if access granted
            - txt (str): text of return value
        """
        if not self.images or not self.labels:
            ret = 'datasets empty'
            return 1, None, ret

        if len(faces) == 0:
            ret = 'no face detected'
            return 1, None, ret

        if len(faces) > 1:
            ret = 'multiple faces detected'
            return 1, None, ret

        for face in faces:
            faceResized = cv2.resize(face, self.imgSize)
            id, conf = self.recognizer.predict(faceResized)

            #print(f'prob: {conf}')
            cv2.putText(frame, f"{self.names[id]}: {conf}", (10, 400),
			cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)


            if conf > self.confidence[0] and conf <= self.confidence[1]:
                userName = self.names[id]
                return 0, userName, userName
            else:
                ret = 'access denied'
                return 1, None, ret
