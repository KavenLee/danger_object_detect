class Rectangle():
    def __init__(self,left,top,right,bottom):
        self.left=left
        self.right=right
        self.top=top
        self.bottom=bottom
    
    # 입력받은 Rectangle과 겹쳐지는 부분이 있는지 Check
    def IsCross(self, other):
        if self.left > other.right or self.top > other.bottom or self.right < other.left or self.bottom < other.top:
            return False
        else:
            return True

    # Point 객체가 Rectangle안에 들어왔는지 Check
    def PtInRect(self, pt):
        return pt.x >= self.left and pt.x <= self.right and pt.y >= self.top and pt.y <= self.bottom

    # 입력받은 Rectangle 과 겹치는 영역구하기
    def GetIntersectionRect(self, other):
        left = max(self.left,other.left)
        top  = max(self.top,other.top)
        right = min(self.right,other.right)
        bottom = min(self.bottom,other.bottom)
        return Rectangle(left, top, right, bottom)

    # Rectangle의 가로길이
    def GetWidth(self):
        return self.right - self.left

    # Rectangle의 세로길이
    def GetHeight(self):
        return self.bottom - self.top;
    
    # Rectangle의 넓이
    def GetArea(self):
        return self.GetWidth() * self.GetHeight()

class Point():
    def __init__(self, x, y):
        self.x = x
        self.y = y

# 두 개의 Rectangle 객체인 파라미터들이 겹쳐지는 지 Check
def IsOverlapRect(A,B):
    return A.IsCross(B)

# 입력받은 두 Rectangle의 겹쳐지는 비율
def GetIntersectionRatio(roi,other):
    if (roi.IsCross(other) and roi.GetArea() > 0): # 겹쳐지는 지와 영역이 0이 아닌지 확인
        intersection = roi.GetIntersectionRect(other)
        interArea = intersection.GetArea()
        return interArea / roi.GetArea() * 100

    return 0