import typer
from pathlib import Path
from rich.progress import Progress, TaskID, MofNCompleteColumn
import zipfile
import geopandas as gpd
import shutil
import fiona
from itertools import islice
import pandas as pd

app = typer.Typer()

# Open the shapefile with fiona
def progress_read_shp(file, progress: Progress, chunk_size: int = 10000) -> tuple[gpd.GeoDataFrame, TaskID]:
    with fiona.open(file) as src:
        # Get the crs and schema of the shapefile
        crs = src.crs
        schema = src.schema

        # Create an empty geodataframe to store the final result
        gdf = gpd.GeoDataFrame()
        feat_count = len(src)
        read_task = progress.add_task("Reading shapefile", total=feat_count)
        for i in range(0, feat_count, chunk_size):
            # Convert the chunk into a list of features
            chunk = list(src[i:i+chunk_size])
            # Create a geodataframe from the features
            gdf_chunk = gpd.GeoDataFrame.from_features(chunk, crs=crs)
            # Concatenate the geodataframes
            gdf = pd.concat([gdf, gdf_chunk])
            progress.update(read_task, advance=len(chunk))
            # Delete the chunk and the geodataframe variables
            del chunk, gdf_chunk

        # Return a geodataframe from the features
        return gdf, read_task

@app.command()
def run(
    input: str = typer.Argument(..., help="The input directory, shapefile or zip file"),
    output: str = typer.Argument("output/", help="The output directory"),
    zip: bool = typer.Option(True, help="Whether to zip the output files or not"),
    match: str = typer.Option('**/*.shp', help="Match string to use if the input is a directory or a zip archive. Any file matching the criteria will be globbed"),
):
    # Create Path objects for the input and output directories
    input_path = Path(input)
    output_dir = Path(output)

    if not output_dir.exists():
        output_dir.mkdir()
    else:
        print(f'[WARNING] output dir "{output_dir}" already exists')

    progress = Progress(MofNCompleteColumn(), *Progress.get_default_columns())

    # Check if the input is a directory, a shapefile or a zip file
    if input_path.is_dir():
        # Find all shapefiles in the input directory recursively
        shapefiles = list(input_path.glob(match))
    elif input_path.suffix == ".shp":
        # Use the input shapefile as a single-item list
        shapefiles = [input_path]
    elif input_path.suffix == ".zip":
        # Create a temporary directory
        tmp_dir = Path(".tmp")
        # Extract all the contents of the zip file to the temporary directory
        with zipfile.ZipFile(input_path, "r") as zf:
            zf.extractall(tmp_dir)
        # Find all shapefiles in the temporary directory recursively
        shapefiles = list(tmp_dir.glob(match))
    else:
        # Raise an error if the input is not valid
        raise typer.BadParameter("Input must be a directory, a shapefile or a zip file")
    
    progress.start()

    # Add tasks for reading and processing shapefiles
    process_task = progress.add_task("Processing shapefile", total=len(shapefiles))

    # Loop through the shapefiles with a progress bar
    for file in shapefiles:
        # Read the input shapefile
        gdf, task = progress_read_shp(file, progress)

        gdf["TargtRxVar"] = ((gdf["AppliedRate"] - gdf["TargetRate"]) / gdf["TargetRate"]) * 100
        gdf["Speed"] = (gdf["DISTANCE"] * 0.0003048) * 3600
        gdf["FieldProd"] = (((gdf["DISTANCE"] * 0.3048) * (gdf["SWATHWIDTH"] * 0.3048)) / 10000) * 3600
        gdf["TargetRate"] = gdf["TargetRate"] * 2.47105381
        gdf["AppliedRate"] = gdf["AppliedRate"] * 2.47105381

        # Save the output shapefile with the same name in the output directory
        output_file = output_dir / file.name
        print(f'[INFO] writing output shapefile')
        gdf.to_file(output_file)

        # If zip option is True, zip the output file and delete the original one
        if zip:
            # Create a zip file name with the same stem as the output file
            zip_file = output_dir / (file.stem + ".zip")
            # Create a zip file object in write mode
            with zipfile.ZipFile(zip_file, "w") as zf:
                print(f'[INFO] zipping shapefile')
                # Write the output file and its associated files to the zip file
                for ext in [".shp", ".dbf", ".prj", ".shx", ".cpg"]:
                    zf.write(output_file.with_suffix(ext), arcname=output_file.name())
                print(f'[INFO] removing temporary files')
                # Delete the original output file and its associated files
                for ext in [".shp", ".dbf", ".prj", ".shx", ".cpg"]:
                    output_file.with_suffix(ext).unlink()
        progress.remove_task(task)
        progress.update(process_task, advance=1)
        del gdf

    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Stop displaying progress
    progress.stop()

    # Print a success message
    typer.echo(f"Processed {input_path} and saved to {output_dir}")
