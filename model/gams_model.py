from typing import Optional, Any
import os
import shutil
import sys
import tempfile
import gams.transfer as gt
import gams
from .utils import get_temp_dir


class GamsModel:
    """A generic GAMS model represented in Python

    Attributes:
        workspace: the gams workspace
        database: database used in the workspace
        checkpoint: the current model checkpoint
        options: gams option used when running the file
        files: files used to run the job
    """

    workspace: Optional[gams.GamsWorkspace] = None
    database: Optional[gams.GamsDatabase] = None
    checkpoint: Optional[gams.GamsCheckpoint] = None
    files: Optional[gams.GamsOptions] = None
    options: Optional[gams.GamsOptions] = None

    def __init__(
        self,
        working_directory: str | None = None,
        database: Optional[gams.GamsDatabase] = None,
        checkpoint: Optional[gams.GamsCheckpoint] = None,
        options: dict[str, Any] = {},
        files: Optional[list[str]] = None,
    ):
        """

        Args:
            working_directory: If no directory is provided working_directory is
                used to create the workspace
            database: a gams database, to add and gdx file, use the add_database
                method after the model has been instantiated
            checkpoint: gams checkpoint to start the model from (usually empty)
            options: a dictionary with your default gams options
            files: files used to run the gams model: If none the standard model
                file will be used
        """
        self.workspace = self.create_workspace(working_directory=working_directory)
        self.database = database
        self.checkpoint = checkpoint
        # add options to gams
        self.options = self.workspace.add_options()
        for k, v in options.items():
            setattr(self.options, k, v)
        # copy files into the workspace
        if files is None:
            files = [os.path.join(os.path.dirname(__file__), "model.gms")]
        all_files = [
            os.path.join(self.working_directory, os.path.basename(fn)) for fn in files
        ]
        for src in files:
            shutil.copy(src, self.working_directory)
        self.files = all_files

    @staticmethod
    def create_workspace(working_directory: Optional[str] = None) -> gams.GamsWorkspace:
        """Create workspace. If path is not provided it is created in a
        temporary folder

        Args:
            working_directory: directory used as working directory for the gams
                model
        """
        if working_directory is None:
            temp_dir = get_temp_dir()
            working_directory = tempfile.mkdtemp(dir=temp_dir)
        return gams.GamsWorkspace(working_directory=working_directory)

    @property
    def working_directory(self) -> str:
        """Working directory of the model"""
        return self.workspace.working_directory

    def add_database(
        self,
        container: Optional[gt.Container] = None,
        gdx_file_name: Optional[str] = None,
        database_name: Optional[str] = None,
        in_model_name: Optional[str] = None,
    ) -> gams.GamsDatabase:
        """Add database to model space. An existing gams.transfer.Container or
        and gdx file can be used to populate the database. If none of these
        is provided, an empty database is created.

        Args:
            container: a gams.transfer.Container containing the data
            gdx_file_name: name of the gdx file
            database_name: Identifier of GamsDatabase (determined automatically if omitted)
                that is name of the file on disk
            in_model_name: GAMS string constant that is used to access this database
                this is name of the file used in the gams code %in_model_name%

        Returns:
            gams.GamsDatabase instance referring to the Gams database
        """
        if container and gdx_file_name:
            raise ValueError(
                "Specify either path to gdx or provide container but not both"
            )
        if gdx_file_name:
            self.database = self.workspace.add_database_from_gdx(
                gdx_file_name, database_name=database_name, in_model_name=in_model_name
            )
        else:
            self.database = self.workspace.add_database(
                database_name=database_name, in_model_name=in_model_name
            )
            if container:
                container.write(self.database)
        return

    def run_file(
        self,
        file_name: Optional[str] = None,
        gams_source: Optional[str] = None,
        output: Optional[Any] = sys.stdout,
    ):
        """Run a gams file. Running the gams file will overwrite the current
            checkpoint of the model. Also, the database will be substituted by
            the output database

        Args:
            file_name: name of the file to run
            gams_source: a string holding the gams code
            output
        """
        if gams_source and file_name:
            raise ValueError("Specify either file_name or gams_source, not both")
        if not gams_source and not file_name:
            raise ValueError("Specify either file_name or gams_source.")

        if file_name:
            job = self.workspace.add_job_from_file(
                file_name=file_name, checkpoint=self.checkpoint
            )
        if gams_source:
            job = self.workspace.add_job_from_string(
                gams_source=gams_source, checkpoint=self.checkpoint
            )
        # create checkpoint if not already specified
        if self.checkpoint is None:
            self.checkpoint = self.workspace.add_checkpoint()
        # run job and update database reference
        job.run(
            gams_options=self.options,
            checkpoint=self.checkpoint,
            databases=self.database,
            output=output,
        )
        self.database = job.get_out_db()
        return

    def run_files(
        self,
        files: list[str],
        output: Any | None = sys.stdout,
    ):
        """Run multiple GAMS files

        Args:
            files: list of files to be run. Order in the list
                determines order in which the files are run
            output: destination of gams output stream
        """
        for fn in files:
            self.run_file(file_name=fn, output=output)

    def run(
        self,
        output: Any | None = sys.stdout,
    ) -> gt.Container:
        """Run all files to prepare the model for solving

        Args:
            output: destination of gams output stream
        """
        self.run_files(self.files, output=output)
        # check solution statistics

        return gt.Container(load_from=self.database)
