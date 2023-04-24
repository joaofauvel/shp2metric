# Import the typer, pathlib and rich libraries
import typer
from pathlib import Path
from rich.progress import track

# Create a typer app
app = typer.Typer()

# Define a command that takes the input and output directory names as arguments
@app.command()
def run(input_dir: str, output_dir: str = 'output', match: str = "*.shp", zip: bool = True):
    # Import the geopandas library
    import geopandas as gpd

    # Create Path objects for the input and output directories
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    # Find all shapefiles in the input directory
    shapefiles = input_dir.glob(match)

    # Loop through the shapefiles with a progress bar
    for file in track(shapefiles, description="Processing shapefiles..."):
        # Read the input shapefile
        gdf = gpd.read_file(file)

        # Assign a new column that is the difference of column "Applied" and "Target"
        gdf["Difference"] = gdf["Applied"] - gdf["Target"]

        # Apply 2*x to column "distance"
        gdf["distance"] = gdf["distance"] * 2

        # Save the output shapefile with the same name in the output directory
        output_file = output_dir / file.name
        gdf.to_file(output_file)

    # Print a success message
    typer.echo(f"Processed {input_dir} and saved to {output_dir}")


import typer
from pathlib import Path
from rich.progress import track
import zipfile
import geopandas as gpd

app = typer.Typer()

@app.command()
def run(
    input: str = typer.Argument(..., help="The input directory, shapefile or zip file"),
    output: str = typer.Argument("output", help="The output directory"),
    zip: bool = typer.Option(True, help="Whether to zip the output files or not"),
    match: str = typer.Option('*.shp', help="Match string to use if the input is a directory. Any file matching the criteria will be globbed."),
):
    # Create Path objects for the input and output directories
    input_path = Path(input)
    output_dir = Path(output)

    # Check if the input is a directory, a shapefile or a zip file
    if input_path.is_dir():
        # Find all shapefiles in the input directory
        shapefiles = input_path.glob("*.shp")
    elif input_path.suffix == ".shp":
        # Use the input shapefile as a single-item list
        shapefiles = [input_path]
    elif input_path.suffix == ".zip":
        # Open the zip file and find all shapefiles inside it
        with zipfile.ZipFile(input_path, "r") as zf:
            shapefiles = [Path(file) for file in zf.namelist() if file.endswith(".shp")]
    else:
        # Raise an error if the input is not valid
        raise typer.BadParameter("Input must be a directory, a shapefile or a zip file")

    # Loop through the shapefiles with a progress bar
    for file in track(shapefiles, description="Processing shapefiles..."):
        # Read the input shapefile
        gdf = gpd.read_file(file)

        # Assign a new column that is the difference of column "Applied" and "Target"
        gdf["Difference"] = gdf["Applied"] - gdf["Target"]

        # Apply 2*x to column "distance"
        gdf["distance"] = gdf["distance"] * 2

        # Save the output shapefile with the same name in the output directory
        output_file = output_dir / file.name
        gdf.to_file(output_file)

        # If zip option is True, zip the output file and delete the original one
        if zip:
            # Create a zip file name with the same stem as the output file
            zip_file = output_dir / (file.stem + ".zip")

            # Create a zip file object in write mode
            with zipfile.ZipFile(zip_file, "w") as zf:
                # Write the output file and its associated files to the zip file
                for ext in [".shp", ".dbf", ".prj", ".shx"]:
                    zf.write(output_file.with_suffix(ext))

                # Delete the original output file and its associated files
                for ext in [".shp", ".dbf", ".prj", ".shx"]:
                    output_file.with_suffix(ext).unlink()

    # Print a success message
    typer.echo(f"Processed {input_path} and saved to {output_dir}")

