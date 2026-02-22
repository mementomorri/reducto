
#Bad Code
def doSomething(srh39fdfkdl):
    for i in range(9):
        for j in range(9):
            x1i90jjdk = srh39fdfkdl[i][j]
            for k in range(9):
                if k != j and srh39fdfkdl[i][k] == x1i90jjdk:
                    return False
                if k != i and srh39fdfkdl[k][j] == x1i90jjdk:
                    return False
            boxStartRow = i - i % 3
            boxStartCol = j - j % 3
            for k in range(3):
                for l in range(3):
                    if k != i and l != j and srh39fdfkdl[boxStartRow + k][boxStartCol + l] == x1i90jjdk:
                        return False
    return True

#Good Code
def is_valid_sudoku(sudoku_grid):
    for row in range(9):
        for col in range(9):
            current_value = sudoku_grid[row][col]
            
            # Check for duplicate values in the same row
            for i in range(9):
                if i != col and sudoku_grid[row][i] == current_value:
                    return False
            
            # Check for duplicate values in the same column
            for j in range(9):
                if j != row and sudoku_grid[j][col] == current_value:
                    return False
            
            # Check for duplicate values in the same 3x3 box
            box_start_row = 3 * (row // 3)
            box_start_col = 3 * (col // 3)
            for i in range(3):
                for j in range(3):
                    current_row = box_start_row + i
                    current_col = box_start_col + j
                    if current_row != row and current_col != col and sudoku_grid[current_row][current_col] == current_value:
                        return False
    
    return True
