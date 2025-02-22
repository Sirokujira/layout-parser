# Copyright 2021 The Layout Parser team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Union
from PIL import Image
import numpy as np
import warnings

from .catalog import MODEL_CATALOG, PathManager, LABEL_MAP_CATALOG
from ..base_layoutmodel import BaseLayoutModel
#from ...elements import Rectangle, TextBlock, Layout
from ...elements import Rectangle, TextBlock, Quadrilateral, Layout
from ...file_utils import is_torch_cuda_available, is_detectron2_available

if is_detectron2_available():
    import detectron2.engine
    import detectron2.config


#__all__ = ["Detectron2LayoutModel"]
__all__ = ["Detectron2LayoutModel", "Detectron2CustomLayoutModel"]


class Detectron2LayoutModel(BaseLayoutModel):
    """Create a Detectron2-based Layout Detection Model

    Args:
        config_path (:obj:`str`):
            The path to the configuration file.
        model_path (:obj:`str`, None):
            The path to the saved weights of the model.
            If set, overwrite the weights in the configuration file.
            Defaults to `None`.
        label_map (:obj:`dict`, optional):
            The map from the model prediction (ids) to real
            word labels (strings). If the config is from one of the supported
            datasets, Layout Parser will automatically initialize the label_map.
            Defaults to `None`.
        device(:obj:`str`, optional):
            Whether to use cuda or cpu devices. If not set, LayoutParser will
            automatically determine the device to initialize the models on.
        extra_config (:obj:`list`, optional):
            Extra configuration passed to the Detectron2 model
            configuration. The argument will be used in the `merge_from_list
            <https://detectron2.readthedocs.io/modules/config.html
            #detectron2.config.CfgNode.merge_from_list>`_ function.
            Defaults to `[]`.

    Examples::
        >>> import layoutparser as lp
        >>> model = lp.Detectron2LayoutModel('lp://HJDataset/faster_rcnn_R_50_FPN_3x/config')
        >>> model.detect(image)

    """

    DEPENDENCIES = ["detectron2"]
    DETECTOR_NAME = "detectron2"
    MODEL_CATALOG = MODEL_CATALOG

    def __init__(
        self,
        config_path,
        model_path=None,
        label_map=None,
        extra_config=None,
        enforce_cpu=None,
        device=None,
    ):

        if enforce_cpu is not None:
            warnings.warn(
                "Setting enforce_cpu is deprecated. Please set `device` instead.",
                DeprecationWarning,
            )

        if extra_config is None:
            extra_config = []

        config_path, model_path = self.config_parser(
            config_path, model_path, allow_empty_path=True
        )
        config_path = PathManager.get_local_path(config_path)

        if label_map is None:
            if config_path.startswith("lp://"):
                dataset_name = config_path.lstrip("lp://").split("/")[1]
                label_map = LABEL_MAP_CATALOG[dataset_name]
            else:
                label_map = {}

        cfg = detectron2.config.get_cfg()
        cfg.merge_from_file(config_path)
        cfg.merge_from_list(extra_config)

        if model_path is not None:
            model_path = PathManager.get_local_path(model_path)
            # Because it will be forwarded to the detectron2 paths
            cfg.MODEL.WEIGHTS = model_path

        if is_torch_cuda_available():
            if device is None:
                device = "cuda"
        else:
            device = "cpu"
        cfg.MODEL.DEVICE = device

        self.cfg = cfg

        self.label_map = label_map
        self._create_model()

    def _create_model(self):
        self.model = detectron2.engine.DefaultPredictor(self.cfg)

    def gather_output(self, outputs):

        instance_pred = outputs["instances"].to("cpu")

        layout = Layout()
        scores = instance_pred.scores.tolist()
        boxes = instance_pred.pred_boxes.tensor.tolist()
        labels = instance_pred.pred_classes.tolist()

        for score, box, label in zip(scores, boxes, labels):
            x_1, y_1, x_2, y_2 = box


            label = self.label_map.get(label, label)

            cur_block = TextBlock(
                Rectangle(x_1, y_1, x_2, y_2), type=label, score=score
            )
            layout.append(cur_block)

        return layout

    def detect(self, image):
        """Detect the layout of a given image.

        Args:
            image (:obj:`np.ndarray` or `PIL.Image`): The input image to detect.

        Returns:
            :obj:`~layoutparser.Layout`: The detected layout of the input image
        """

        image = self.image_loader(image)
        outputs = self.model(image)
        layout = self.gather_output(outputs)
        return layout

    def image_loader(self, image: Union["np.ndarray", "Image.Image"]):
        # Convert PIL Image Input
        if isinstance(image, Image.Image):
            if image.mode != "RGB":
                image = image.convert("RGB")
            image = np.array(image)

        return image


class Detectron2CustomLayoutModel(BaseLayoutModel):
    """Create a Detectron2-based Layout Detection Model

    Args:
        config_path (:obj:`str`):
            The path to the configuration file.
        model_path (:obj:`str`, None):
            The path to the saved weights of the model.
            If set, overwrite the weights in the configuration file.
            Defaults to `None`.
        label_map (:obj:`dict`, optional):
            The map from the model prediction (ids) to real
            word labels (strings). If the config is from one of the supported
            datasets, Layout Parser will automatically initialize the label_map.
            Defaults to `None`.
        device(:obj:`str`, optional):
            Whether to use cuda or cpu devices. If not set, LayoutParser will
            automatically determine the device to initialize the models on.
        extra_config (:obj:`list`, optional):
            Extra configuration passed to the Detectron2 model
            configuration. The argument will be used in the `merge_from_list
            <https://detectron2.readthedocs.io/modules/config.html
            #detectron2.config.CfgNode.merge_from_list>`_ function.
            Defaults to `[]`.

    Examples::
        >>> import layoutparser as lp
        >>> model = lp.Detectron2LayoutModel('lp://HJDataset/faster_rcnn_R_50_FPN_3x/config')
        >>> model.detect(image)

    """

    DEPENDENCIES = ["detectron2"]
    DETECTOR_NAME = "detectron2"
    MODEL_CATALOG = MODEL_CATALOG

    def __init__(
        self,
        config_path,
        model_path=None,
        label_map=None,
        extra_config=None,
        enforce_cpu=None,
        device=None,
    ):

        if enforce_cpu is not None:
            warnings.warn(
                "Setting enforce_cpu is deprecated. Please set `device` instead.",
                DeprecationWarning,
            )

        if extra_config is None:
            extra_config = []

        config_path, model_path = self.config_parser(
            config_path, model_path, allow_empty_path=True
        )
        config_path = PathManager.get_local_path(config_path)

        if label_map is None:
            if config_path.startswith("lp://"):
                dataset_name = config_path.lstrip("lp://").split("/")[1]
                label_map = LABEL_MAP_CATALOG[dataset_name]
            else:
                label_map = {}

        cfg = detectron2.config.get_cfg()
        cfg.merge_from_file(config_path)
        cfg.merge_from_list(extra_config)

        if model_path is not None:
            model_path = PathManager.get_local_path(model_path)
            # Because it will be forwarded to the detectron2 paths
            cfg.MODEL.WEIGHTS = model_path

        if is_torch_cuda_available():
            if device is None:
                device = "cuda"
        else:
            device = "cpu"
        cfg.MODEL.DEVICE = device

        self.cfg = cfg

        self.label_map = label_map
        self._create_model()

    def _create_model(self):
        self.model = detectron2.engine.DefaultPredictor(self.cfg)

    def gather_output(self, outputs):

        instance_pred = outputs["instances"].to("cpu")

        layout = Layout()
        scores = instance_pred.scores.tolist()
        boxes = instance_pred.pred_boxes.tensor.tolist()
        masks = instance_pred.pred_masks.numpy()
        masks = masks.astype(np.uint8)
        masks[masks > 0] = 255
        labels = instance_pred.pred_classes.tolist()
        import cv2

        for score, box, label, mask in zip(scores, boxes, labels, masks):
            x_1, y_1, x_2, y_2 = box

            #print(mask)
            #mask = masks.cpu().numpy()
            #inv_bool_array = []
            #for l in mask:
            #    inv_b = []
            #    for b in l:
            #        if b == False:
            #            inv_b.append(True)
            #        else:
            #            inv_b.append(False)
            #    inv_bool_array.append(inv_b)
            #copy_img = img.copy()
            #copy_img[inv_bool_array] = [128,128,128]

            #contours, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            contours, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            #print(contours)
            #print(contours[0])
            #print(contours[0][0])
            #print(contours[0][:].T)
            #print(contours[0][:].T[0])
            #print(contours[0][:].T[0][0])
            #print(contours[0][:].T[1][0])
            contour_xlist = contours[0][:].T[0][0]
            contour_ylist = contours[0][:].T[1][0]
            #print(contours[0][:][0]) # xlist?
            #print(contours[0][:][1]) # ylist?
            #print(contours[0,:,0]) # xlist?(ng)
            #print(contours[0,:,1]) # ylist?(ng)
            #for cont in contours[0]:
            #    #print(cont)    # [[x y]]
            #    #print(cont[0])  # [x y]
            #    pass
            #img_contour = cv2.drawContours(img_origin, contours, -1, (0, 255, 0), 5)
            contour = contours[np.argmax([cv2.contourArea(x) for x in contours])]
            rotrect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rotrect)
            box = np.int0(box)
            print(box)

            label = self.label_map.get(label, label)
            cur_block = TextBlock(
                Rectangle(x_1, y_1, x_2, y_2), type=label, score=score
            )
            # 
            # [[p0_x, p0_y], [p1_x, p1_y], [p2_x, p2_y], [p3_x, p3_y]]
            cont_x_1 = min(contour_xlist)
            cont_x_2 = max(contour_xlist)
            cont_y_1 = min(contour_ylist)
            cont_y_2 = max(contour_ylist)
            p0_x = cont_x_1
            p0_y = cont_y_1
            p1_x = cont_x_1
            p1_y = cont_y_2
            p2_x = cont_x_2
            p2_y = cont_y_2
            p3_x = cont_x_2
            p3_y = cont_y_1
            polyline = [[p0_x, p0_y], [p1_x, p1_y], [p2_x, p2_y], [p3_x, p3_y]]
            cur2_block = Quadrilateral(points=polyline,height=None, width=None)
            #layout.append(cur_block)
            layout.append(cur2_block)

        return layout


    def detect(self, image):
        """Detect the layout of a given image.

        Args:
            image (:obj:`np.ndarray` or `PIL.Image`): The input image to detect.

        Returns:
            :obj:`~layoutparser.Layout`: The detected layout of the input image
        """

        image = self.image_loader(image)
        outputs = self.model(image)
        layout = self.gather_output(outputs)
        return layout


    def image_loader(self, image: Union["np.ndarray", "Image.Image"]):
        # Convert PIL Image Input
        if isinstance(image, Image.Image):
            if image.mode != "RGB":
                image = image.convert("RGB")
            image = np.array(image)

        return image

