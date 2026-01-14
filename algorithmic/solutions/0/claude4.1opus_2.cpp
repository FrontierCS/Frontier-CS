#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y;
};

vector<Point> normalize(vector<Point> cells) {
    if (cells.empty()) return cells;
    int minX = INT_MAX, minY = INT_MAX;
    for (auto& p : cells) {
        minX = min(minX, p.x);
        minY = min(minY, p.y);
    }
    for (auto& p : cells) {
        p.x -= minX;
        p.y -= minY;
    }
    return cells;
}

vector<Point> rotate90(vector<Point> cells) {
    vector<Point> result;
    for (auto& p : cells) {
        result.push_back({-p.y, p.x});
    }
    return normalize(result);
}

vector<Point> reflectY(vector<Point> cells) {
    vector<Point> result;
    for (auto& p : cells) {
        result.push_back({-p.x, p.y});
    }
    return normalize(result);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    
    vector<vector<Point>> polyominoes(n);
    int totalCells = 0;
    
    for (int i = 0; i < n; i++) {
        int k;
        cin >> k;
        totalCells += k;
        
        for (int j = 0; j < k; j++) {
            int x, y;
            cin >> x >> y;
            polyominoes[i].push_back({x, y});
        }
        polyominoes[i] = normalize(polyominoes[i]);
    }
    
    int W = (int)ceil(sqrt(totalCells * 1.5));
    int H = (int)ceil(sqrt(totalCells * 1.5));
    
    vector<vector<bool>> grid(H, vector<bool>(W, false));
    vector<array<int, 4>> placements(n);
    
    for (int i = 0; i < n; i++) {
        bool placed = false;
        
        for (int f = 0; f <= 1 && !placed; f++) {
            vector<Point> shape = polyominoes[i];
            if (f == 1) shape = reflectY(shape);
            
            for (int r = 0; r < 4 && !placed; r++) {
                if (r > 0) shape = rotate90(shape);
                
                for (int y = 0; y < H && !placed; y++) {
                    for (int x = 0; x < W && !placed; x++) {
                        bool canPlace = true;
                        
                        for (auto& cell : shape) {
                            int px = x + cell.x;
                            int py = y + cell.y;
                            
                            if (px >= W || py >= H) {
                                canPlace = false;
                                break;
                            }
                            
                            if (grid[py][px]) {
                                canPlace = false;
                                break;
                            }
                        }
                        
                        if (canPlace) {
                            for (auto& cell : shape) {
                                grid[y + cell.y][x + cell.x] = true;
                            }
                            placements[i] = {x, y, r, f};
                            placed = true;
                        }
                    }
                }
            }
        }
        
        if (!placed) {
            if (W <= H) {
                W++;
                for (auto& row : grid) row.resize(W, false);
            } else {
                H++;
                grid.resize(H, vector<bool>(W, false));
            }
            i--;
        }
    }
    
    cout << W << " " << H << "\n";
    for (int i = 0; i < n; i++) {
        cout << placements[i][0] << " " << placements[i][1] << " " << placements[i][2] << " " << placements[i][3] << "\n";
    }
    
    return 0;
}