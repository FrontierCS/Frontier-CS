#include <bits/stdc++.h>
using namespace std;

struct Cell {
    int x, y;
};

struct Placement {
    int x, y, r, f;
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

vector<Cell> transform(vector<Cell> cells, int r, int f) {
    if (f) {
        for (auto& c : cells) c.x = -c.x;
        cells = normalize(cells);
    }
    for (int i = 0; i < r; i++) {
        for (auto& c : cells) {
            int tmp = c.x;
            c.x = c.y;
            c.y = -tmp;
        }
        cells = normalize(cells);
    }
    return cells;
}

bool canPlace(const set<pair<int,int>>& occupied, const vector<Cell>& cells, int x, int y, int W, int H) {
    for (const auto& c : cells) {
        int nx = x + c.x;
        int ny = y + c.y;
        if (nx < 0 || nx >= W || ny < 0 || ny >= H || occupied.count({nx, ny})) 
            return false;
    }
    return true;
}

void place(set<pair<int,int>>& occupied, const vector<Cell>& cells, int x, int y) {
    for (const auto& c : cells) {
        occupied.insert({x + c.x, y + c.y});
    }
}

bool solve(const vector<vector<Cell>>& pieces, int W, int H, vector<Placement>& placements) {
    set<pair<int,int>> occupied;
    placements.resize(pieces.size());
    
    for (int i = 0; i < pieces.size(); i++) {
        bool placed = false;
        
        for (int f = 0; f <= 1 && !placed; f++) {
            for (int r = 0; r < 4 && !placed; r++) {
                vector<Cell> transformed = transform(pieces[i], r, f);
                
                for (int y = 0; y < H && !placed; y++) {
                    for (int x = 0; x < W && !placed; x++) {
                        if (canPlace(occupied, transformed, x, y, W, H)) {
                            place(occupied, transformed, x, y);
                            placements[i] = {x, y, r, f};
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
    
    vector<vector<Cell>> pieces(n);
    int totalCells = 0;
    
    for (int i = 0; i < n; i++) {
        int k;
        cin >> k;
        pieces[i].resize(k);
        totalCells += k;
        
        for (int j = 0; j < k; j++) {
            cin >> pieces[i][j].x >> pieces[i][j].y;
        }
        
        pieces[i] = normalize(pieces[i]);
    }
    
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        return pieces[a].size() > pieces[b].size();
    });
    
    vector<vector<Cell>> sorted_pieces(n);
    for (int i = 0; i < n; i++) {
        sorted_pieces[i] = pieces[order[i]];
    }
    
    int bestW = totalCells, bestH = 1, bestArea = totalCells;
    vector<Placement> bestPlacements(n);
    
    int sqrtArea = (int)ceil(sqrt((double)totalCells));
    
    for (int H = sqrtArea; H <= min(totalCells, sqrtArea + 50); H++) {
        int minW = (totalCells + H - 1) / H;
        
        for (int W = minW; W <= minW + 20; W++) {
            int area = W * H;
            
            if (area > bestArea) break;
            
            vector<Placement> placements;
            if (solve(sorted_pieces, W, H, placements)) {
                if (area < bestArea || (area == bestArea && H < bestH) ||
                    (area == bestArea && H == bestH && W < bestW)) {
                    bestArea = area;
                    bestW = W;
                    bestH = H;
                    bestPlacements = placements;
                }
                break;
            }
        }
    }
    
    vector<Placement> result(n);
    for (int i = 0; i < n; i++) {
        result[order[i]] = bestPlacements[i];
    }
    
    cout << bestW << " " << bestH << "\n";
    for (const auto& p : result) {
        cout << p.x << " " << p.y << " " << p.r << " " << p.f << "\n";
    }
    
    return 0;
}