
# placeNode_web.py
# For the placeNode calculation this handles:
#   - validation of received input
#   - mapping between mapID and layout to data file locations
#   - http response and code

import os, json, types, requests, traceback, csv, logging
from argparse import Namespace
import validate_web as validate
import util_web
from util_web import SuccessResp, ErrorResp, getMapMetaData, createBookmark
import placeNode
import compute_sparse_matrix
import utils
import pandas as pd
import StringIO
import numpy as np

import job

def check_duplicate_row_error(error):
    """
    Checks to see if there is a duplicate row error and sends a more meaningful
    error message.
    @param e_message: The message from the caught exception
    @return: None or Raises an ValueError with a pertinant message
    """
    e_message = error.message
    # These messages are created in comupte_sparse_matrix.common_rows function.
    if e_message == "Duplicate rows in first matrix.":
        raise ValueError("Duplicate rows in new nodes input causing failure.")
    if e_message == "Duplicate rows in second matrix.":
        raise ValueError("Duplicate rows in feature matrix causing failure,"
                         "this map will be unable to complete node placement."
                         "Build a new map without duplicate row names.")

    raise error

def validateParms(data):
    '''
    Validate the query.
    @param data: data received in the http post request
    @return: nothing
    '''
    # Basic checks on required parameters
    validate.map(data, True)
    validate.layout(data, True)
    if 'nodes' not in data:
        raise ErrorResp('nodes parameter missing or malformed')
    if not isinstance(data['nodes'], dict):
        raise ErrorResp('nodes parameter should be a dictionary')
    if len(data['nodes'].keys()) < 1:
        raise ErrorResp('there are no nodes in the nodes dictionary')
    
    # Basic checks on optional parameters
    validate.email(data)
    validate.viewServer(data)
    if 'neighborCount' in data and \
        (not isinstance(data['neighborCount'], int) or \
        data['neighborCount'] < 1):
        raise ErrorResp('neighborCount parameter should be a positive integer')

def postCalc(result, ctx):
    '''
    Create bookmarks and send email from a calculation result.
    @param result: results from the calculation
    @param ctx: global context
    @return: ('success', result)
    '''
    dataIn = ctx.dataIn

    #logging.debug('calcComplete: result: ' + str(result))
    
    if 'error' in result:
        raise ErrorResp(result['error'], 500)

    # Be sure we have a view server
    if not 'viewServer' in dataIn:
        dataIn['viewServer'] = ctx.app.viewServer

    # Format the result as client state in preparation to create a bookmark
    state = {
        'page': 'mapPage',
        'project': dataIn['map'] + '/',
        'layoutIndex': ctx.layoutIndex,
        'shortlist': [],
        'overlayNodes': {},
        'dynamic_attrs': {},
    }
    mailMsg = ''
    active_layer = None

    # Populate state for each node
    needFirstLayer = True
    for node in result['nodes']:
        nData = result['nodes'][node]
        state['overlayNodes'][node] = { 'x': nData['x'], 'y': nData['y'] }
        
        # Build the neighbor places layer
        attr = node + ': ' + dataIn['layout'] + ': neighbors'
        if needFirstLayer:
            needFirstLayer = False
            active_layer = attr
        state['shortlist'].append(attr)
        state['dynamic_attrs'][attr] = {
            'dynamic': True,
            'dataType': 'binary',
            'data': {},
        }
        
        # Build the neighbor values layer
        attrV = node + ': ' + dataIn['layout'] + ': neighbor values'
        state['shortlist'].append(attrV)
        state['dynamic_attrs'][attrV] = {
            'dynamic': True,
            'dataType': 'continuous',
            'data': {},
        }
        
        # Add the values to the new layers
        for neighbor in nData['neighbors']:
            state['dynamic_attrs'][attr]['data'][neighbor] = 1;
            state['dynamic_attrs'][attrV]['data'][neighbor] = \
                nData['neighbors'][neighbor];

        # Set the number of values in the state for each attribute
        state['dynamic_attrs'][attr]['n'] = \
            len(state['dynamic_attrs'][attr]['data']);
        state['dynamic_attrs'][attrV]['n'] = \
            len(state['dynamic_attrs'][attrV]['data']);

        # If individual Urls were requested, create a bookmark for this node
        if 'individualUrls' in dataIn and dataIn['individualUrls']:
        
            # Set the active_layer to color the map.
            state['active_layers'] = [attr]
            
            # Create the bookmark.
            bData = createBookmark(state, dataIn['viewServer'], ctx)
            result['nodes'][node]['url'] = bData['bookmark']
            mailMsg += ' \n' + node + ': ' + bData['bookmark']

            # Clear the node data to get ready for the next node
            state['overlayNodes'] = {}
            state['dynamic_attrs'] = {}
            state['shortlist'] = [];
        
    # If individual urls were not requested, create one bookmark containing all
    # nodes and return that url for each node
    if not 'individualUrls' in dataIn or not dataIn['individualUrls']:
        
        # Set the active layer to color the map.
        state['active_layers'] = [active_layer]

        # Create the bookmark.
        bData = createBookmark(state, dataIn['viewServer'], ctx)
        for node in result['nodes']:
            result['nodes'][node]['url'] = bData['bookmark']
            mailMsg += ', ' + node
        
        mailMsg += '\n' + bData['bookmark']

    # Notify any email addresses provided.
    if 'email' in dataIn:
        util_web.sendResultsEmail(dataIn['email'],
        'New nodes have been placed.\n\n' + mailMsg[2:], ctx)

    return 'Success', result

def outputToDict(neighboorhood, xys, urls):
    '''
    This function takes the output from the newplacement call
      into the expected format
    @param neighboorhood: pandas df
    @param xys: pandas df
    @param urls: an array of URLs
    @return: dictionary to be turned into a JSON str
    '''
    #return dictionary to populate with results
    retDict = {"nodes":{}}

    #seperating the columns of the neighborhood df
    # for processing
    newNodes  = neighboorhood[neighboorhood.columns[0]]
    neighbors = neighboorhood[neighboorhood.columns[1]]
    scores    = neighboorhood[neighboorhood.columns[2]]
    #grab column names for indexing
    xcol = xys.columns[0]
    ycol = xys.columns[1]

    for i,node in enumerate(set(newNodes)):
        maskArr = np.array(newNodes == node)
        retDict['nodes'][node] = {}
        retDict['nodes'][node]['neighbors'] = dict(zip(neighbors.iloc[maskArr],
                                                       scores.iloc[maskArr]))
        #add urls to the return struct
        #retDict['nodes'][node]['url'] = urls[i]
        retDict['nodes'][node]['x'] = xys.loc[node,xcol]
        retDict['nodes'][node]['y'] = xys.loc[node,ycol]

    return retDict

def putDataIntoPythonStructs(featurePath, xyPath, nodesDict):
    '''
    takes in the filenames and nodes dictionary needed for placement calc
    @param featurePath:
    @param xyPath:
    @param tabSepArray:
    @return:
    '''
    return (compute_sparse_matrix.numpyToPandas(
            *compute_sparse_matrix.read_tabular(featurePath)
                                                ),
            utils.readXYs(xyPath),
            nodesToPandas(nodesDict)
          )

def nodesToPandas(pydict):
    '''
    Input the json['nodes'] structure and outputs pandas df.
    Uses same processing pipeline as compute sparse matrix for input.
    @param pydict: the dataIn['nodes'] structure,
                   currently a dict of dicts {columns -> {rows -> values}}
    @return: a pandas dataframe
    '''
    df = pd.DataFrame(pydict, dtype=float)
    utils.duplicate_columns_check(df)
    df = compute_sparse_matrix.processInputData(df,
                                                numeric_flag=True,
                                                replaceNA=False
                                                )

    return df

def getBackgroundData(data, ctx):
    '''
    Find the clustering data file for this map and layout.
    @param data: background data of the existing map
    @param ctx: global context
    @return: cluster data file path and the pre-bin xy coordinates
    '''
    try:
        layouts = getMapMetaData(data['map'], ctx)['layouts']
        clusterData = layouts[data['layout']]['clusterData']
        clusterDataFile = os.path.join(ctx.app.dataRoot, clusterData)
    except:
        raise Exception(
            'Clustering data not found for layout: ' + data['layout'])

    # Find the index of the layout
    ctx.layoutIndex = \
        util_web.getLayoutIndex(data['layout'], data['map'], ctx)

    # Find the xyPosition file
    xyPositionFile = os.path.join(
        ctx.mapDir, 'assignments' + str(ctx.layoutIndex) + '.tab')

    return clusterDataFile, xyPositionFile

def preCalc(dataIn, ctx):    
    '''
    The entry point from the www URL routing.
    @param dataIn: data from the HTTP post request
    @param ctx: global context
    @return: result of calcComplete()
    '''
    validateParameters(dataIn)

    # Add the job to the job queue.
    if 'email' in dataIn:
        email = dataIn['email']
    else:
        email = None
    job.add(email, 'placeNode', dataIn, ctx)

def calcMain(dataIn, ctx):
    
    ctx.mapDir = os.path.join(ctx.app.viewDir, dataIn['map'])

    # Find the helper data needed to place nodes
    clusterDataFile, xyPositionFile = getBackgroundData(dataIn, ctx)

    # Set any optional parms, letting the calc script set defaults.
    if 'neighborCount' in dataIn:
        top = dataIn['neighborCount']
    else:
        top = 6 # TODO: this default should be set in the calc module.

    # Make expected python data structs
    referenceDF, xyDF, newNodesDF = \
     putDataIntoPythonStructs(clusterDataFile,
                              xyPositionFile,
                              dataIn['nodes'])

    # Call the calc script.
    try:
        neighboorhood, xys, urls = placeNode.placeNew(newNodesDF,referenceDF,
                                                  xyDF, top, dataIn['map'],
                                                  num_jobs=1)

    except ValueError as error:
        check_duplicate_row_error(error)

    #format into python struct
    result = outputToDict(neighboorhood, xys, urls)

    ctx.dataIn = dataIn
    
    return postCalc(result, ctx)
