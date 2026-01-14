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

vector<Cell> transform(vector<Cell> cells, int r, int f) {
    if (f == 1) {
        for (auto& c : cells) c.x = -c.x;
    }
    for (int i = 0; i < r; i++) {
        for (auto& c : cells) {
            int tmp = c.x;
            c.x = c.y;
            c.y = -tmp;
        }
    }
    return normalize(cells);
}

bool canPlace(vector<vector<bool>>& grid, int W, int H, const vector<Cell>& cells, int x, int y) {
    for (auto& c : cells) {
        int nx = x + c.x, ny = y + c.y;
        if (nx < 0 || nx >= W || ny < 0 || ny >= H || grid[ny][nx]) return false;
    }
    return true;
}

void place(vector<vector<bool>>& grid, const vector<Cell>& cells, int x, int y) {
    for (auto& c : cells) grid[y + c.y][x + c.x] = true;
}

bool tryPack(vector<vector<Cell>>& polys, int W, int H, vector<array<int,4>>& result) {
    vector<vector<bool>> grid(H, vector<bool>(W, false));
    result.resize(polys.size());
    
    for (int i = 0; i < polys.size(); i++) {
        bool placed = false;
        for (int f = 0; f <= 1 && !placed; f++) {
            for (int r = 0; r < 4 && !placed; r++) {
                vector<Cell> transformed = transform(polys[i], r, f);
                for (int y = 0; y < H && !placed; y++) {
                    for (int x = 0; x < W && !placed; x++) {
                        if (canPlace(grid, W, H, transformed, x, y)) {
                            place(grid, transformed, x, y);
                            result[i] = {x, y, r, f};
                            placed = true;
                        }
                    }
                }
            }
        }
        if (!placed) return false;
    }
    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    
    vector<vector<Cell>> polys(n);
    vector<int> indices(n);
    int totalCells = 0;
    
    for (int i = 0; i < n; i++) {
        int k;
        cin >> k;
        polys[i].resize(k);
        totalCells += k;
        for (int j = 0; j < k; j++) {
            cin >> polys[i][j].x >> polys[i][j].y;
        }
        polys[i] = normalize(polys[i]);
        indices[i] = i;
    }
    
    sort(indices.begin(), indices.end(), [&](int a, int b) {
        return polys[a].size() > polys[b].size();
    });
    
    vector<vector<Cell>> sortedPolys(n);
    for (int i = 0; i < n; i++) sortedPolys[i] = polys[indices[i]];
    
    int sqrtCells = (int)sqrt(totalCells);
    int bestW = 0, bestH = 0;
    long long bestArea = LLONG_MAX;
    vector<array<int,4>> bestResult;
    
    for (int h = max(1, sqrtCells - 5); h <= sqrtCells + 50; h++) {
        int minW = (totalCells + h - 1) / h;
        for (int w = minW; w <= minW + 20; w++) {
            long long area = (long long)w * h;
            if (area > bestArea) break;
            
            vector<array<int,4>> result;
            if (tryPack(sortedPolys, w, h, result)) {
                if (area < bestArea || (area == bestArea && h < bestH) ||
                    (area == bestArea && h == bestH && w < bestW)) {
                    bestArea = area;
                    bestW = w;
                    bestH = h;
                    bestResult = result;
                }
                break;
            }
        }
    }
    
    cout << bestW << " " << bestH << "\n";
    
    vector<array<int,4>> finalResult(n);
    for (int i = 0; i < n; i++) {
        finalResult[indices[i]] = bestResult[i];
    }
    
    for (int i = 0; i < n; i++) {
        cout << finalResult[i][0] << " " << finalResult[i][1] << " "
             << finalResult[i][2] << " " << finalResult[i][3] << "\n";
    }
    
    return 0;
}