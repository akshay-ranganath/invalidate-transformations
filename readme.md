## Clear Transformations

`clear_transformations.py` is a simple helper script to clear Cloudinary's storage and CDN cache when an overlay image has been updated or deleted.

### Installation

Clone the repository.

```
git clone https://github.com/akshay-ranganath/invalidate-transformations.git
```

Change to the project directory.

```
cd invalidate-transformations
```

The script has been written for Python3. Install the libraries for the script. Alternatively create a virtual environment and then install the libraries.

```
pip install -r requirement.txt
```

Get your Cloudinary API credentials by logging into Cloudinary console. In the _Dashboard_ section. Copy the `API Environment Variable` and export it to your environment.

```
export CLOUDINARY_URL=cloudinary://<<api-key>:<<api-secret>>@cloud-name/<<CNAME info>>
```

## Executing the script

After installation and including the environment variable, execute the script as follows

```
python clear_transformations.py --overlay OVERLAY

--overlay OVERLAY  overlay image name
```

The script starts with a logging default level of _INFO_. If you'd like to change the level, please modify the variable at the top of the file.

```
log_level = logging.INFO # other values logging.DEBUG logging.ERROR
```

The script should execute and print out the messages as it progresses. It will report the number of transformations that uses the overlay image and the invalidate the associated derived image.