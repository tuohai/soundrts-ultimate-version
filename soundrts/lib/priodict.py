# Priority dictionary using binary heaps
# David Eppstein, UC Irvine, 8 Mar 2002

# 优化：预先导入heapq模块，避免每次方法调用时的import开销
try:
    import heapq
    _HEAPQ_AVAILABLE = True
except ImportError:
    _HEAPQ_AVAILABLE = False


class priorityDictionary(dict):
    def __init__(self):
        """Initialize priorityDictionary by creating binary heap
of pairs (value,key).  Note that changing or removing a dict entry will
not remove the old pair from the heap until it is found by smallest() or
until the heap is rebuilt."""
        self.__heap = []
        dict.__init__(self)

    def smallest(self):
        """Find smallest item after removing deleted items from heap."""
        if len(self) == 0:
            raise IndexError("smallest of empty priorityDictionary")
        heap = self.__heap
        
        # 优化：预先检查堆顶元素是否仍然有效
        while heap and (heap[0][1] not in self or self[heap[0][1]] != heap[0][0]):
            # 使用Python内置的heappop来维护堆性质，比手动实现更快
            if _HEAPQ_AVAILABLE:
                heapq.heappop(heap)
            else:
                # 备选方案：手动实现但优化了
                if not heap:
                    break
                lastItem = heap.pop()
                if not heap:
                    break
                    
                insertionPoint = 0
                heap_len = len(heap)
                
                # 循环展开优化，减少条件检查
                while True:
                    smallChild = 2 * insertionPoint + 1
                    if smallChild >= heap_len:
                        heap[insertionPoint] = lastItem
                        break
                    
                    if (smallChild + 1 < heap_len and 
                        heap[smallChild] > heap[smallChild + 1]):
                        smallChild += 1
                    
                    if lastItem <= heap[smallChild]:
                        heap[insertionPoint] = lastItem
                        break
                        
                    heap[insertionPoint] = heap[smallChild]
                    insertionPoint = smallChild
        
        return heap[0][1] if heap else None

    def __iter__(self):
        """Create destructive sorted iterator of priorityDictionary."""

        def iterfn():
            while len(self) > 0:
                x = self.smallest()
                yield x
                del self[x]

        return iterfn()

    def __setitem__(self, key, val):
        """Change value stored in dictionary and add corresponding
pair to heap.  Rebuilds the heap if the number of deleted items grows
too large, to avoid memory leakage."""
        dict.__setitem__(self, key, val)
        heap = self.__heap
        
        # 优化：使用更激进的重建策略，但使用heapify而非sort
        if len(heap) > 3 * len(self):  # 改为3倍而非2倍，减少重建频率
            if _HEAPQ_AVAILABLE:
                # 使用heapify替代sort，O(n) vs O(n log n)
                self.__heap = [(v, k) for k, v in self.items()]
                heapq.heapify(self.__heap)
            else:
                # 备选方案：仍使用sort但优化了列表生成
                items = list(self.items())
                self.__heap = [(v, k) for k, v in items]
                self.__heap.sort()
        else:
            # 优化：如果有heapq，直接使用heappush，否则手动上浮
            if _HEAPQ_AVAILABLE:
                heapq.heappush(heap, (val, key))
            else:
                newPair = (val, key)
                insertionPoint = len(heap)
                heap.append(newPair)  # 先添加到末尾，然后修正
                
                # 优化的上浮过程
                while insertionPoint > 0:
                    parentIndex = (insertionPoint - 1) // 2
                    if newPair >= heap[parentIndex]:
                        break
                    heap[insertionPoint] = heap[parentIndex]
                    insertionPoint = parentIndex
                
                heap[insertionPoint] = newPair

    def setdefault(self, key, val):
        """Reimplement setdefault to call our customized __setitem__."""
        if key not in self:
            self[key] = val
        return self[key]
