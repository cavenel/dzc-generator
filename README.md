# dzc-generator
A tool to generate deep zoom collections

## Building

[Libvips](http://www.vips.ecs.soton.ac.uk/index.php?title=Libvips) is required in order for this to build.

Building is achieved by running **make**.

## Generating the collection

```bash
./build_collection input_directory output_directory collection_name
```

This will build a [deep zoom collection](https://msdn.microsoft.com/en-us/library/cc645077%28v=vs.95%29.aspx#Collections) by saving all of the images in input_directory as deep zoom images in output_directory and a zoomable collection of thumbnails with the collection_name.

## Running in Python

```bash
python build_collection.py input_directory output_directory collection_name
```

The python version needs [pyvips](https://libvips.github.io/pyvips/) installed.
You can then run the following command to generate a collection:

