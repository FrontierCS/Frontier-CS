#include <iostream>
using namespace std;

int main() {
    int n = 20, m = 20;
    char grid[21][21];
    
    // Initialize all to '0'
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= m; j++) {
            grid[i][j] = '0';
        }
    }
    
    // Set odd rows to '1'
    for (int i = 1; i <= n; i += 2) {
        for (int j = 1; j <= m; j++) {
            grid[i][j] = '1';
        }
    }
    
    // Set connectors in even rows
    grid[2][20] = '1';
    grid[4][1] = '1';
    grid[6][20] = '1';
    grid[8][1] = '1';
    grid[10][20] = '1';
    grid[12][1] = '1';
    grid[14][20] = '1';
    grid[16][1] = '1';
    grid[18][20] = '1';
    
    // Output
    cout << n << " " << m << endl;
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= m; j++) {
            cout << grid[i][j];
        }
        cout << endl;
    }
    
    return 0;
}