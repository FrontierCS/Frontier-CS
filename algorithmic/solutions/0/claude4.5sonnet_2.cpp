#include <bits/stdc++.h>
using namespace std;

struct Cell {
    int x, y;
};

vector<Cell> normalize(vector<Cell> cells) {
    if (cells.empty()) return cells;
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

vector<Cell> transform(vector<Cell> cells, int reflect, int rotate, int tx, int ty) {
    cells = normalize(cells);
    
    if (reflect) {
        for (auto& c : cells) {
            c.x = -c.x;
        }
        cells = normalize(cells);
    }
    
    for (int r = 0; r < rotate; r++) {
        for (auto& c : cells) {
            int nx = c.y;
            int ny = -c.x;
            c.x = nx;
            c.y = ny;
        }
        cells = normalize(cells);
    }
    
    for (auto& c : cells) {
        c.x += tx;
        c.y += ty;
    }
    
    return cells;
}

bool canPlace(const vector<Cell>& cells, int W, int H, const set<pair<int,int>>& occupied) {
    for (const auto& c : cells) {
        if (c.x < 0 || c.x >= W || c.y < 0 || c.y >= H) return false;
        if (occupied.count({c.x, c.y})) return false;
    }
    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    
    vector<vector<Cell>> pieces(n);
    int totalCells = 0;
    
    for (int i = 0; i < n; i++) {
        int k;
        cin >> k;
        totalCells += k;
        pieces[i].resize(k);
        for (int j = 0; j < k; j++) {
            cin >> pieces[i][j].x >> pieces[i][j].y;
        }
        pieces[i] = normalize(pieces[i]);
    }
    
    int sqrtArea = max(1, (int)ceil(sqrt((double)totalCells)));
    
    for (int W = sqrtArea; W <= totalCells; W++) {
        int H = (totalCells + W - 1) / W;
        
        set<pair<int,int>> occupied;
        vector<tuple<int,int,int,int>> placements(n);
        bool allPlaced = true;
        
        for (int i = 0; i < n; i++) {
            bool placed = false;
            
            for (int y = 0; y < H && !placed; y++) {
                for (int x = 0; x < W && !placed; x++) {
                    for (int f = 0; f < 2 && !placed; f++) {
                        for (int r = 0; r < 4 && !placed; r++) {
                            vector<Cell> transformed = transform(pieces[i], f, r, x, y);
                            if (canPlace(transformed, W, H, occupied)) {
                                for (const auto& c : transformed) {
                                    occupied.insert({c.x, c.y});
                                }
                                placements[i] = {x, y, r, f};
                                placed = true;
                            }
                        }
                    }
                }
            }
            
            if (!placed) {
                allPlaced = false;
                break;
            }
        }
        
        if (allPlaced) {
            cout << W << " " << H << "\n";
            for (int i = 0; i < n; i++) {
                auto [x, y, r, f] = placements[i];
                cout << x << " " << y << " " << r << " " << f << "\n";
            }
            return 0;
        }
        
        if (W * H > totalCells * 2) break;
    }
    
    return 0;
}