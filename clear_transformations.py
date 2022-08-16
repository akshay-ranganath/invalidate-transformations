import cloudinary.api
import argparse
import logging

#### GLOBAL LOGGING CONFIG ###
log_level = logging.INFO # other values logging.DEBUG logging.ERROR
### GLOBAL LOGGING CONFIG ENDS ###

"""
    CustomFormatter is a helper function to generate colored output. 
    Modify the color codes, if you want to change the schema.

"""
class CustomFormatter(logging.Formatter):

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    green = "\x1b[1;32m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)

        return formatter.format(record)

# create console handler with a higher log level
logger = logging.getLogger("transformation_cleaner")
logger.setLevel(log_level)
ch = logging.StreamHandler()
ch.setLevel(log_level)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)


"""
    checkArgument is a method to test the name of the input for overlay image
    It returns an exception if a null value is found.

    Raises:
        ValueError: when an empty string is presented as the overlay image        

    Returns:
        None    
"""
class checkArgument(argparse.Action):    
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super().__init__(option_strings, dest, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        if values.strip()==None or values.strip()=='':
            raise ValueError("Null values allowed")
        #print('%r %r %r' % (namespace, values, option_string))
        setattr(namespace, self.dest, values)
        

def get_transformations(overlay, results=[], next_cursor=None):
    """
    get_transformations is a wrapper for the 'GET Transformations' API Method (https://cloudinary.com/documentation/admin_api#get_transformations)

    This function is also recursive. Using the `next_cursor` as a pagination variable, it loops through all transformations.
    Each call will return a max of 500 transformations. If the name contains the overlay image and if it is actually used, 
    it is retained for next round of analysis. 
    
    We say a transformation is "used" if it has at least one derived image using the transformation.

    Args:
        overlay (_type_): _description_
        results (list, optional): _description_. Defaults to [].
        next_cursor (_type_, optional): _description_. Defaults to None.

    Returns:
        results: A list of transformations that contains the overlay image name
    """
    
    try:        
        resp = cloudinary.api.transformations(
            max_results=500,
            next_cursor = next_cursor
        )
        for transformation in resp['transformations']:
            #logger.debug(f"{transformation['name']}, {transformation['used']}")
            try:
                if transformation['used']==True and transformation['name'].find(f'{overlay}')>-1:            
                    results.append(transformation['name'])                
            except TypeError as e:
                logger.error(transformation['name'], e)            
                return None
        
        if('next_cursor' in resp and resp['next_cursor']!=None):
            get_transformations(overlay, results, resp['next_cursor'])
    except cloudinary.exceptions.RateLimited as e:
        logger.error('API rate limit has been reached. Try after 1 hour or reach out to Cloudinary Support')
        results = []
    except Exception as e:
        logger.error(e)
        results = []
    return results


def get_resources(transformation, resources, next_cursor=None):    
    """
    get_resources is a wrapper for the API 'GET transformation details` (https://cloudinary.com/documentation/admin_api#get_transformation_details)
    This method returns a list of public ids and the associated transformation string.

    This is also a recursive method and uses next_cursor to loop through list of all images that use same transformation string.

    Args:
        transformation (_type_): _description_
        resources (_type_): _description_
        next_cursor (_type_, optional): _description_. Defaults to None.

    Returns:
        _results_: Dictionary of resources containg { transformation -> [public ids] } mapping
    """

    resp = cloudinary.api.transformation(
        transformation,
        max_results=500,
        next_cursor = next_cursor        
    )

    for derived in resp['derived']:
        public_id = derived['public_id']
        if transformation in resources:
            resources[transformation].append(public_id)
        else:
            resources[transformation] = [public_id]
    
    if('next_cursor' in resp and resp['next_cursor']!=None):
        get_resources(transformation, resources, resp['next_cursor'])
    
    return resources


def get_impacted_resources(transformations):
    """
    get_impacted_resources is a helper function to identify resources that use a specific transformation string.
    This method calls 'get_resources' to make the actual API call for every transformation and get back the set of images.


    Args:
        transformations (_list_): A list of transformation strings containing the overlay image

    Returns:
        _type_: Dictionary of resources containg { transformation -> [public ids] } mapping
    """
    resources = {}

    for transformation in transformations:
        resources = get_resources(transformation, resources)
    return resources


def delete_resource(public_ids, transformations):
    """
    delete_resource is a wrapper for the DELETE resources method (https://cloudinary.com/documentation/admin_api#delete_resources)
    This method takes a list of public ids associated with a transformation string and submits it for invalidation.
    Note that the original image is never deleted. Only the specific derivative and the the cached version of this derivative is removed.

    The API is restricted to to invalidate only 100 public ids in a request. 

    Args:
        public_ids (_list_): _list of publicids for deletion, limited to a max of 100_
        transformations (_list_): _a single transformation string containing the overlay image_
    """
    
    resp = cloudinary.api.delete_resources(
        public_ids=public_ids,
        resource_type='image',
        type='upload',
        keep_original=True,
        invalidate=True,
        transformations=transformations
    )
    logger.debug(resp)


def delete_old_transformations(transformations):
    """
    delete_old_transformations is the method that chunks 100 public ids associated with a transformation string
    and submits for invalidation through the 'delete_resource' method.

    Args:
        transformations (_dict_): Dictionary of resources containg { transformation -> [public ids] } mapping

    Returns:
        _int_: Total assets invalidated
    """
    total_invaidated = 0    
    max_resources = 100
    for transformation in transformations:        
        total_resources = len(transformations[transformation])
        if total_resources > max_resources:
            for index in range(0,total_resources,max_resources):
                if total_resources > index+max_resources:
                    print(transformations[transformation][index:index+max_resources])
                    delete_resource(transformations[transformation][index:index+max_resources], transformation)                    
                else:
                    print(transformations[transformation][index:total_resources])
                    delete_resource(transformations[transformation][index:total_resources], transformation)
            total_invaidated += total_resources            
        else:
            delete_resource(transformations[transformation], transformation)
            total_invaidated += len(transformations[transformation])
    return total_invaidated


if __name__=="__main__":

    ## Step 1: Accept input and check if any overlay image has been specified.
    parser = argparse.ArgumentParser(description='Clear transformations using a specific overlay.')
    parser.add_argument('--overlay', help='overlay image name', required=True, action=checkArgument)        
    args = parser.parse_args()    
    
    ## Step 2: Identify the transformations that contain the overlay image
    overlay = 'l_' + args.overlay
    logger.info(f'Looking for transformations string: {overlay}')

    transformations = get_transformations(overlay)

    ## Step 3: If transformations are found, identify the resources / public ids associated with the transformation
    if len(transformations) > 0:
        logger.info(f'Found {len(transformations)} transformations using the image "{args.overlay}"')            
        
        resources = get_impacted_resources(transformations)            
        logger.info(f'Fetched impacted resources. Now trying to delete them...')
        logger.debug(resources)         
        
        ## Step 4: Finally, invalidate the resources associated with the transformation
        total_invaidated = delete_old_transformations(resources)  
        logger.info(f'Deleted overlay transformations associated with {total_invaidated} resources.') 

    else:
        logger.info(f'No transformation found using overlay image "{args.overlay}.')