#include <bits/stdc++.h>
using namespace std;

struct Cell {
    int x, y;
};

vector<Cell> normalize(vector<Cell> cells) {
    if (cells.empty()) return cells;
    int minX = INT_MAX, minY = INT_MAX;
    for (auto& c : cells) {
        minX = min(minX, c.x);
        minY = min(minY, c.y);
    }
    for (auto& c : cells) {
        c.x -= minX;
        c.y -= minY;
    }
    return cells;
}

vector<Cell> transform(vector<Cell> cells, int R, int F, int tx, int ty) {
    if (F == 1) {
        for (auto& c : cells) {
            c.x = -c.x;
        }
    }
    
    for (int r = 0; r < R; r++) {
        for (auto& c : cells) {
            int nx = c.y;
            int ny = -c.x;
            c.x = nx;
            c.y = ny;
        }
    }
    
    cells = normalize(cells);
    
    for (auto& c : cells) {
        c.x += tx;
        c.y += ty;
    }
    
    return cells;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    
    vector<vector<Cell>> polyominoes(n);
    int totalCells = 0;
    
    for (int i = 0; i < n; i++) {
        int k;
        cin >> k;
        totalCells += k;
        polyominoes[i].resize(k);
        for (int j = 0; j < k; j++) {
            cin >> polyominoes[i][j].x >> polyominoes[i][j].y;
        }
    }
    
    int side = (int)sqrt(totalCells) + 5;
    int W = side;
    int H = side;
    
    while (W * H < totalCells) {
        if (W <= H) W++;
        else H++;
    }
    
    vector<vector<bool>> grid(H, vector<bool>(W, false));
    vector<tuple<int,int,int,int>> solution(n);
    
    for (int i = 0; i < n; i++) {
        bool placed = false;
        
        for (int F = 0; F <= 1 && !placed; F++) {
            for (int R = 0; R < 4 && !placed; R++) {
                for (int y = 0; y < H && !placed; y++) {
                    for (int x = 0; x < W && !placed; x++) {
                        auto transformed = transform(polyominoes[i], R, F, x, y);
                        
                        bool canPlace = true;
                        for (auto& c : transformed) {
                            if (c.x < 0 || c.x >= W || c.y < 0 || c.y >= H || grid[c.y][c.x]) {
                                canPlace = false;
                                break;
                            }
                        }
                        
                        if (canPlace) {
                            for (auto& c : transformed) {
                                grid[c.y][c.x] = true;
                            }
                            solution[i] = {x, y, R, F};
                            placed = true;
                        }
                    }
                }
            }
        }
        
        if (!placed) {
            if (W <= H) {
                W++;
                grid.assign(H, vector<bool>(W, false));
            } else {
                H++;
                grid.assign(H, vector<bool>(W, false));
            }
            i = -1;
            continue;
        }
    }
    
    cout << W << " " << H << "\n";
    for (auto& [x, y, r, f] : solution) {
        cout << x << " " << y << " " << r << " " << f << "\n";
    }
    
    return 0;
}