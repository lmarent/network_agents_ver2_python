import GraphExecution
import foundation.agent_properties
from ProviderAgentException import ProviderException
import MySQLdb
import logging
from InformationExtracter import InformationExtracter

logger = logging.getLogger('information_extracter_test')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('information_extracter_test.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

def test_information_extracter(execution_count, graphics):
       
    inf_extract = InformationExtracter(execution_count, graphics)
    inf_extract.animate()



if __name__ == '__main__':

    try:
        # Open database connection
        db = MySQLdb.connect(foundation.agent_properties.addr_database,foundation.agent_properties.user_database,
                             foundation.agent_properties.user_password,foundation.agent_properties.database_name )

        # prepare a cursor object using cursor() method
        cursor = db.cursor()

        graphics = {}
        cursor3 = db.cursor()
        cursor4 = db.cursor()
        logger.info('Ready to load Graphics')
        GraphExecution.load_graphics(cursor3, cursor4, graphics)
        for graphic in graphics:
            print graphics[graphic], '\n'
        logger.info('Graphics loaded')
        execution_count = 1697
        test_information_extracter(execution_count, graphics)

    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()