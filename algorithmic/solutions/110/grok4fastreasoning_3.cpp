#include <bits/stdc++.h>
using namespace std;

int main() {
    char grid[8][14];
    memset(grid, '0', sizeof(grid));

    // Row 0
    grid[0][0] = '1'; grid[0][1] = '0'; grid[0][2] = '2'; grid[0][3] = '0';
    grid[0][4] = '3'; grid[0][5] = '3'; grid[0][6] = '4'; grid[0][7] = '4';
    grid[0][8] = '5'; grid[0][9] = '3'; grid[0][10] = '6'; grid[0][11] = '4';
    grid[0][12] = '7'; grid[0][13] = '3';

    // Row 1
    grid[1][0] = '0'; grid[1][1] = '1'; grid[1][2] = '0'; grid[1][3] = '2';
    grid[1][4] = '0'; grid[1][5] = '1'; grid[1][6] = '0'; grid[1][7] = '2';
    grid[1][8] = '0'; grid[1][9] = '1'; grid[1][10] = '0'; grid[1][11] = '2';
    grid[1][12] = '0'; grid[1][13] = '1';

    // Row 2
    grid[2][10] = '8'; grid[2][11] = '3'; grid[2][12] = '9'; grid[2][13] = '0';

    // Row 3
    grid[3][11] = '4';

    // Row 5
    grid[5][0] = '5'; grid[5][1] = '5'; grid[5][2] = '6';
    grid[5][12] = '8'; grid[5][13] = '9';

    // Row 6
    grid[6][0] = '7'; grid[6][1] = '8'; grid[6][2] = '9';
    grid[6][6] = '6'; grid[6][7] = '6';
    grid[6][12] = '8'; grid[6][13] = '9';

    // Row 7
    grid[7][5] = '7'; grid[7][6] = '8'; grid[7][7] = '9';
    grid[7][12] = '7'; grid[7][13] = '7';

    for (int i = 0; i < 8; ++i) {
        for (int j = 0; j < 14; ++j) {
            cout << grid[i][j];
        }
        cout << endl;
    }
    return 0;
}