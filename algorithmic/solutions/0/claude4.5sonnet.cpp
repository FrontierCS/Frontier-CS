#include <bits/stdc++.h>
using namespace std;

struct Cell {
    int x, y;
};

struct Poly {
    vector<Cell> cells;
    int id;
};

Cell transform(Cell c, int R, int F, int X, int Y) {
    int x = c.x, y = c.y;
    if (F == 1) x = -x;
    for (int i = 0; i < R; i++) {
        int tmp = x;
        x = y;
        y = -tmp;
    }
    return {x + X, y + Y};
}

vector<Cell> getTransformed(const vector<Cell>& cells, int R, int F, int X, int Y) {
    vector<Cell> result;
    for (const auto& c : cells) {
        result.push_back(transform(c, R, F, X, Y));
    }
    return result;
}

vector<Cell> normalize(vector<Cell> cells) {
    int minX = INT_MAX, minY = INT_MAX;
    for (const auto& c : cells) {
        minX = min(minX, c.x);
        minY = min(minY, c.y);
    }
    for (auto& c : cells) {
        c.x -= minX;
        c.y -= minY;
    }
    return cells;
}

bool isValid(const vector<Cell>& cells, int W, int H, vector<vector<bool>>& grid) {
    for (const auto& c : cells) {
        if (c.x < 0 || c.x >= W || c.y < 0 || c.y >= H || grid[c.y][c.x]) 
            return false;
    }
    return true;
}

void place(const vector<Cell>& cells, vector<vector<bool>>& grid) {
    for (const auto& c : cells) {
        grid[c.y][c.x] = true;
    }
}

bool tryPack(vector<Poly>& polys, int W, int H, vector<tuple<int,int,int,int>>& placements) {
    vector<vector<bool>> grid(H, vector<bool>(W, false));
    
    for (const auto& poly : polys) {
        bool placed = false;
        
        for (int y = 0; y < H && !placed; y++) {
            for (int x = 0; x < W && !placed; x++) {
                for (int F = 0; F <= 1 && !placed; F++) {
                    for (int R = 0; R < 4 && !placed; R++) {
                        auto transformed = getTransformed(poly.cells, R, F, x, y);
                        if (isValid(transformed, W, H, grid)) {
                            place(transformed, grid);
                            placements[poly.id] = {x, y, R, F};
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
    cin.tie(NULL);
    
    int n;
    cin >> n;
    
    vector<Poly> polys(n);
    int totalCells = 0;
    
    for (int i = 0; i < n; i++) {
        int k;
        cin >> k;
        totalCells += k;
        polys[i].cells.resize(k);
        polys[i].id = i;
        for (int j = 0; j < k; j++) {
            cin >> polys[i].cells[j].x >> polys[i].cells[j].y;
        }
        polys[i].cells = normalize(polys[i].cells);
    }
    
    sort(polys.begin(), polys.end(), [](const Poly& a, const Poly& b) {
        return a.cells.size() > b.cells.size();
    });
    
    int bestW = 0, bestH = 0;
    long long bestArea = LLONG_MAX;
    vector<tuple<int,int,int,int>> bestPlacements(n);
    
    int sqrtArea = (int)ceil(sqrt(totalCells));
    
    for (int H = sqrtArea; H <= min(totalCells, sqrtArea + 50); H++) {
        int minW = (totalCells + H - 1) / H;
        
        for (int W = minW; W <= minW + 20; W++) {
            long long area = (long long)W * H;
            if (area >= bestArea) continue;
            
            vector<tuple<int,int,int,int>> placements(n);
            if (tryPack(polys, W, H, placements)) {
                if (area < bestArea || (area == bestArea && H < bestH)) {
                    bestArea = area;
                    bestW = W;
                    bestH = H;
                    bestPlacements = placements;
                }
            }
        }
    }
    
    cout << bestW << " " << bestH << "\n";
    for (const auto& p : bestPlacements) {
        cout << get<0>(p) << " " << get<1>(p) << " " << get<2>(p) << " " << get<3>(p) << "\n";
    }
    
    return 0;
}