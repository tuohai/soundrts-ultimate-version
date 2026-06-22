def must_be_said(nb):
    # 对于小数部分
    if isinstance(nb, float) and nb != int(nb):
        # 如果是小数，则总是显示
        return True
    
    # 将nb转为整数处理
    nb = int(nb)
    if nb <= 10:
        return True
    elif nb <= 100:
        return nb % 10 == 0
    else:
        return nb % 100 == 0
