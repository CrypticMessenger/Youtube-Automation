import unittest
from unittest.mock import patch, MagicMock
import sys

# Assuming cli.py and other relevant modules are structured in a way they can be imported.
# If they are in the root directory and tests is a subdirectory,
# we might need to adjust sys.path or use relative imports if the project is packaged.
# For now, let's assume they can be imported directly or sys.path is handled.

# Add project root to sys.path to allow importing project modules
import os
# Calculate the path to the project root (assuming tests is a direct subdir of project root)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from cli import parse_arguments
# We need a way to trigger the part of the code that uses the niche prompt.
# This might involve calling a main function or a specific processor.
# For this test, we'll focus on argument parsing and the call to the Gemini interaction.
from processors.viral_analysis import ViralAnalysisStep # Assuming this can be imported
from manifest import ManifestEntry # Assuming this can be imported

class TestNicheFeature(unittest.TestCase):

    @patch('gemini_interaction.identify_viral_clips_gemini')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="transcript data")
    @patch('os.makedirs')
    def test_niche_prompt_provided(self, mock_makedirs, mock_open_file, mock_path_exists, mock_identify_viral_clips):
        # Arrange
        test_niche_prompt = "test niche"
        # Simulate command line arguments for the 'process' command
        sys.argv = [
            'main.py', 'process', 'http://youtube.com/video',
            '--viral-short-identifier', # This is needed to trigger viral analysis
            '--niche', test_niche_prompt,
            '--output', 'test_output', # Provide required arg
            '--transcript-dir', 'test_transcripts', # Provide required arg
            '--analysis-dir', 'test_analysis' # Provide required arg
        ]

        # Mock path checks for transcript
        mock_path_exists.return_value = True
        # Mock the return for the identify_viral_clips_gemini function
        mock_identify_viral_clips.return_value = "path/to/analysis_file.txt"

        args = parse_arguments()

        # We need to simulate the ViralAnalysisStep execution
        # This requires a ManifestEntry and other setup that ViralAnalysisStep expects.
        # Create a dummy manifest entry
        entry_data = {
            'url': 'http://youtube.com/video',
            'status_video_downloaded': True, # Assume previous steps are done
            'video_path': 'dummy/video.mp4',
            'status_transcript_generated': True,
            'transcript_path': 'dummy/transcript.txt', # Needs to exist for ViralAnalysisStep
            # other fields as necessary for ManifestEntry
        }
        entry = ManifestEntry(url='http://youtube.com/video', data=entry_data)


        # Ensure necessary args attributes are set for ViralAnalysisStep
        args.effective_analysis_dir = args.analysis_dir # Or however it's set in cli.py
        args.number_of_sections = None # Default or provide
        args.clip_identifier_model = "gemini-1.5-pro-latest" # Default or provide

        # Act
        # Simulate the orchestrator or main logic that would call ViralAnalysisStep
        # For simplicity, we instantiate and call process directly.
        # This part is tricky as it depends on how ViralAnalysisStep is normally called.
        # We are primarily interested in the niche argument passed to identify_viral_clips_gemini.

        # To directly test the call to identify_viral_clips_gemini,
        # we can instantiate ViralAnalysisStep and call its process method.
        # This requires self.args to be set on the instance, which is usually done by an orchestrator.
        # We'll create a ViralAnalysisStep instance and manually set its 'args' and 'entry'

        processor = ViralAnalysisStep(args=args, entry=entry, base_name="test_video")
        processor.process()

        # Assert
        self.assertEqual(args.niche, test_niche_prompt)
        # Check that identify_viral_clips_gemini was called with the niche prompt
        mock_identify_viral_clips.assert_called_once()
        call_args, call_kwargs = mock_identify_viral_clips.call_args
        self.assertEqual(call_kwargs.get('niche_prompt'), test_niche_prompt)


    @patch('gemini_interaction.identify_viral_clips_gemini')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="transcript data")
    @patch('os.makedirs')
    def test_niche_prompt_not_provided(self, mock_makedirs, mock_open_file, mock_path_exists, mock_identify_viral_clips):
        # Arrange
        # Simulate command line arguments without the --niche flag
        sys.argv = [
            'main.py', 'process', 'http://youtube.com/video',
            '--viral-short-identifier',
            '--output', 'test_output',
            '--transcript-dir', 'test_transcripts',
            '--analysis-dir', 'test_analysis'
        ]
        mock_path_exists.return_value = True
        mock_identify_viral_clips.return_value = "path/to/analysis_file.txt"

        args = parse_arguments()

        entry_data = {
            'url': 'http://youtube.com/video',
            'status_video_downloaded': True,
            'video_path': 'dummy/video.mp4',
            'status_transcript_generated': True,
            'transcript_path': 'dummy/transcript.txt',
        }
        entry = ManifestEntry(url='http://youtube.com/video', data=entry_data)

        args.effective_analysis_dir = args.analysis_dir
        args.number_of_sections = None
        args.clip_identifier_model = "gemini-1.5-pro-latest"

        # Act
        processor = ViralAnalysisStep(args=args, entry=entry, base_name="test_video")
        processor.process()

        # Assert
        self.assertIsNone(args.niche) # Default is None as per cli.py modification
        mock_identify_viral_clips.assert_called_once()
        call_args, call_kwargs = mock_identify_viral_clips.call_args
        self.assertIsNone(call_kwargs.get('niche_prompt'))

if __name__ == '__main__':
    unittest.main()
