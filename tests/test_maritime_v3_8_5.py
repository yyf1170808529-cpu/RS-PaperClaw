import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rs-paper-pipeline/scripts'))
from services.domain_exclusion import exclusion
class DomainTests(unittest.TestCase):
 def test_medical(self):
  for title in ["Laryngopharyngeal Cancer T-Staging", "Fetal Brain MRI-Ultrasound Learning", "PPG photoplethysmography clinical alignment", "Chest X-Ray alignment", "Transcriptomes and Electrophysiology", "Alzheimer Prediction", "EEG Brain-to-Image Retrieval"]:
   self.assertIsNotNone(exclusion({'title':title}),title)
 def test_nonmedical(self):
  for title in ["CT: Contrastive Tracking", "Ship segmentation with Transformer", "Cross-modal alignment for radar AIS", "General visual representations", "Autonomous driving multimodal fusion"]:
   self.assertIsNone(exclusion({'title':title}),title)
