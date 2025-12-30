#include <iostream>
#include <vector>
#include <cassert>

using namespace std;

const int MAX = 3000;
bool black[MAX+1][MAX+1] = {false};

int main() {
    int rx, ry;
    cin >> rx >> ry; // initial position
    
    // target corner neighbors
    int trap_cells[3][2] = {{1,2}, {2,1}, {2,2}};
    int trapped = 0; // number of trap cells blackened
    
    for (int turn = 1; turn <= MAX; ++turn) {
        // choose cell to mark
        int mx = -1, my = -1;
        
        if (rx == 1 && ry == 1) {
            // check if all trap cells are already black
            bool all_black = true;
            for (int i = 0; i < 3; ++i) {
                int tx = trap_cells[i][0], ty = trap_cells[i][1];
                if (!black[tx][ty]) {
                    all_black = false;
                    break;
                }
            }
            if (all_black) {
                // all neighbors black, mark (1,1) itself to force explosion
                mx = 1; my = 1;
            } else {
                // blacken the first not yet blackened trap cell
                for (int i = 0; i < 3; ++i) {
                    int tx = trap_cells[i][0], ty = trap_cells[i][1];
                    if (!black[tx][ty]) {
                        mx = tx; my = ty;
                        break;
                    }
                }
            }
        } else {
            // pushing strategy: if rx > ry, try to mark right; else mark above
            if (rx > ry) {
                // try (rx+1, ry)
                if (rx+1 <= MAX && !black[rx+1][ry]) {
                    mx = rx+1; my = ry;
                } else if (ry+1 <= MAX && !black[rx][ry+1]) {
                    mx = rx; my = ry+1;
                } else if (rx+2 <= MAX && !black[rx+2][ry]) {
                    mx = rx+2; my = ry;
                } else if (ry+2 <= MAX && !black[rx][ry+2]) {
                    mx = rx; my = ry+2;
                } else if (rx+1 <= MAX && ry+1 <= MAX && !black[rx+1][ry+1]) {
                    mx = rx+1; my = ry+1;
                } else {
                    // fallback: find any unmarked cell near (rx,ry)
                    for (int d = 1; d <= MAX; ++d) {
                        bool found = false;
                        for (int dx = -d; dx <= d; ++dx) {
                            for (int dy = -d; dy <= d; ++dy) {
                                if (dx == 0 && dy == 0) continue;
                                int nx = rx + dx, ny = ry + dy;
                                if (nx >= 1 && nx <= MAX && ny >= 1 && ny <= MAX && !black[nx][ny]) {
                                    mx = nx; my = ny;
                                    found = true;
                                    break;
                                }
                            }
                            if (found) break;
                        }
                        if (found) break;
                    }
                }
            } else {
                // rx <= ry, try to mark (rx, ry+1)
                if (ry+1 <= MAX && !black[rx][ry+1]) {
                    mx = rx; my = ry+1;
                } else if (rx+1 <= MAX && !black[rx+1][ry]) {
                    mx = rx+1; my = ry;
                } else if (ry+2 <= MAX && !black[rx][ry+2]) {
                    mx = rx; my = ry+2;
                } else if (rx+2 <= MAX && !black[rx+2][ry]) {
                    mx = rx+2; my = ry;
                } else if (rx+1 <= MAX && ry+1 <= MAX && !black[rx+1][ry+1]) {
                    mx = rx+1; my = ry+1;
                } else {
                    // fallback
                    for (int d = 1; d <= MAX; ++d) {
                        bool found = false;
                        for (int dx = -d; dx <= d; ++dx) {
                            for (int dy = -d; dy <= d; ++dy) {
                                if (dx == 0 && dy == 0) continue;
                                int nx = rx + dx, ny = ry + dy;
                                if (nx >= 1 && nx <= MAX && ny >= 1 && ny <= MAX && !black[nx][ny]) {
                                    mx = nx; my = ny;
                                    found = true;
                                    break;
                                }
                            }
                            if (found) break;
                        }
                        if (found) break;
                    }
                }
            }
        }
        
        // should always find something
        assert(mx != -1 && my != -1);
        
        // mark the cell
        cout << mx << " " << my << endl;
        cout.flush();
        black[mx][my] = true;
        
        // read robot's new position or explosion
        cin >> rx >> ry;
        if (rx == 0 && ry == 0) {
            // robot exploded
            break;
        }
    }
    
    return 0;
}