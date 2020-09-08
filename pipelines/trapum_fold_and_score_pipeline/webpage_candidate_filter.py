import numpy as np
import pandas as pd
import glob
import xml.etree.ElementTree as ET
import os
import optparse
import re
import subprocess
import itertools
import logging
import sys
import pika_wrapper
from trapum_pipeline_wrapper import TrapumPipelineWrapper


log = logging.getLogger('manual_presto_fold')
FORMAT = "[%(levelname)s - %(asctime)s - %(filename)s:%(lineno)s] %(message)s"
logging.basicConfig(format=FORMAT)



log.setLevel('INFO')

#parser.add_option('--p_tol',type=float,help='period tolerance',dest="p_tol",default=5e-4)
#parser.add_option('--dm_tol',type=float,help='dm tolerance',dest="dm_tol",default=5e-3)

def make_tarfile(output_path,input_path,name):
    with tarfile.open(output_path+'/'+name, "w:gz") as tar:
        tar.add(input_path, arcname= name)


def candidate_filter_pipeline(data):
    output_dps = []
    dp_list=[]

    '''
    required from pipeline: Filetype, filename, beam id , pointing id, directory
    '''
    processing_args = data['processing_args']
    output_dir = data['base_output_dir']
    #Make output dir
    try:
        subprocess.check_call("mkdir -p %s"%(output_dir),shell=True)
    except:
        log.info("Already made subdirectory")
        pass
    processing_id = data['processing_id']

   # Get an xml list per pointing
    for pointing in data["data"]["pointings"]:
       xml_list=[]
       #beam_id_list=[]  
       for beam in pointing["beams"]:
           for dp in  (beam["data_products"]):
               xml_list.append(dp["filename"])

           
    # Get an xml list
    #xml_list = data['xml_list'] # !! Get an xml list 
   
       # Make temporary folder to keep any temporary outputs
       tmp_dir = '/beeond/PROCESSING/TEMP/%d'%processing_id
       try:
           subprocess.check_call("mkdir -p %s"%(tmp_dir),shell=True)
       except:
           log.info("Already made subdirectory")
           pass
    
  
       # Run the candidate filtering code
       try:
          subprocess.check_call("candidate_filter.py -i %s -o %s/%d -c /home/psr/candidate_filter/candidate_filter/default_config.json --rfi /home/psr/candidate_filter/candidate_filter/known_rfi.txt"%(xml_list,output_dir,processing_id))
       except Exception as error:
          log.error(error)


       # insert beam ID in good cands to fold csv file for later reference
       df = pd.read_csv('%s/%d_good_cands_to_fold.csv')
       all_xml_files = df['file'].values
    
       for i in range(len(all_xml_files)):
           ind = xml_list.index(all_xml_files[i])
           beam_id_values.append(beam_id_list[ind])

       df['beam_id'] = beam_id_values
       df.to_csv('%s/%d_good_cands_to_fold_with_beam.csv'%(output_path,proceessing_id))
    
          
       # Tar up the csv files
       tar_name = os.path.basename(output_path)+"_csv_files.tar.gz"
       make_tarfile(output_path,output_path,tar_name)    


       # Add tar file to dataproduct
       dp = dict(
                 type="candidate_tar_file",
                 filename=tar_name,
                 directory=output_path,
                 beam_id=beam["id"],
                 pointing_id=pointing["id"],
                 metainfo=json.dumps("tar_file:filtered_csvs")
                 ) 

       output_dps.append(dp)
    
    return output_dps

if __name__=="__main__":
    
    parser = optparse.OptionParser()
    pika_wrapper.add_pika_process_opts(parser)
    TrapumPipelineWrapper.add_options(parser)
    opts,args = parser.parse_args()

    processor = pika_wrapper.pika_process_from_opts(opts)
    pipeline_wrapper = TrapumPipelineWrapper(opts,candidate_filter_pipeline)
    processor.process(pipeline_wrapper.on_receive)


