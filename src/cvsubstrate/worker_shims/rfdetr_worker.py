from runtime_common import main
from modern_detector_worker import run

def execute(request):
    request['service']='rfdetr'
    return run(request)
if __name__=='__main__':main(execute)
