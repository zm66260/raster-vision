from abc import (abstractmethod)
import logging

from rastervision.evaluation import Evaluator
from rastervision.data import ActivateMixin
from rastervision.rv_config import RVConfig
from rastervision.utils.files import (download_if_needed)

log = logging.getLogger(__name__)


class ClassificationEvaluator(Evaluator):
    """Evaluates predictions for a set of scenes.
    """

    def __init__(self, class_map, output_uri):
        self.class_map = class_map
        self.output_uri = output_uri

    @abstractmethod
    def create_evaluation(self):
        pass

    def process(self, scenes, tmp_dir):
        evaluation = self.create_evaluation()
        for scene in scenes:
            log.info('Computing evaluation for scene {}...'.format(scene.id))
            label_source = scene.ground_truth_label_source
            label_store = scene.prediction_label_store
            with ActivateMixin.compose(label_source, label_store):
                ground_truth = label_source.get_labels()
                predictions = label_store.get_labels()

                if scene.aoi_polygons:
                    # Filter labels based on AOI.
                    ground_truth = ground_truth.filter_by_aoi(
                        scene.aoi_polygons)
                    predictions = predictions.filter_by_aoi(scene.aoi_polygons)
                scene_evaluation = self.create_evaluation()
                scene_evaluation.compute(ground_truth, predictions)
                evaluation.merge(scene_evaluation)

            if hasattr(label_source, 'source') and hasattr(
                    label_source.source, 'vector_source') and hasattr(
                        label_store, 'vector_output'):
                tmp_dir = RVConfig.get_tmp_dir().name
                gt_geojson = label_source.source.vector_source.uri
                gt_geojson_local = download_if_needed(gt_geojson, tmp_dir)
                for vo in label_store.vector_output:
                    pred_geojson = vo['uri']
                    mode = vo['mode']
                    class_id = vo['class_id']
                    pred_geojson_local = download_if_needed(
                        pred_geojson, tmp_dir)
                    scene_evaluation = self.create_evaluation()
                    scene_evaluation.compute_vector(
                        gt_geojson_local, pred_geojson_local, mode, class_id)
                    evaluation.merge(scene_evaluation)

        evaluation.save(self.output_uri)
