"""Data-dependent TensorRT output allocator with a per-output CUDA byte cap.
Only imported in an explicitly CUDA-enabled native process.
"""
def make_allocator(trt,torch,device,max_bytes):
    class Allocator(trt.IOutputAllocator):
        def __init__(self):
            trt.IOutputAllocator.__init__(self);self.storage=None;self.offset=0;self.size=0;self.shape=None;self.error=None
        def reallocate_output(self,tensor_name,memory,size,alignment):
            if alignment<=0:
                self.error="invalid TensorRT memory alignment";return 0
            if size<0 or size>max_bytes:
                self.error='output allocation exceeds configured byte budget';return 0
            try:
                if self.storage is None or self.storage.numel()<size+alignment:
                    self.storage=torch.empty(size+alignment,device=device,dtype=torch.uint8)
                self.offset=(-self.storage.data_ptr())%alignment;self.size=size
                return self.storage.data_ptr()+self.offset
            except Exception as exc:self.error=str(exc);return 0
        def reallocate_output_async(self,tensor_name,memory,size,alignment,stream):
            return self.reallocate_output(tensor_name,memory,size,alignment)
        def notify_shape(self,tensor_name,shape):
            self.shape=tuple(shape)
            if any(x<0 for x in self.shape):self.error='unresolved TensorRT output shape'
        def value(self,dtype):
            if self.error or self.storage is None or self.shape is None:raise ValueError(self.error or 'TensorRT omitted output shape/allocation')
            element_bytes=torch.empty((),dtype=dtype).element_size()
            import math
            elements=math.prod(self.shape)
            if elements*element_bytes>self.size:raise ValueError('TensorRT output shape exceeds allocated bytes')
            return self.storage[self.offset:self.offset+elements*element_bytes].view(dtype).reshape(self.shape)
    return Allocator()
