#include <bits/stdc++.h>
using namespace std;

struct Polyomino {
    vector<pair<int, int>> cells;
    int id, size;
    
    void normalize() {
        if (cells.empty()) return;
        int minX = INT_MAX, minY = INT_MAX;
        for (auto& p : cells) {
            minX = min(minX, p.first);
            minY = min(minY, p.second);
        }
        for (auto& p : cells) {
            p.first -= minX;
            p.second -= minY;
        }
    }
    
    Polyomino rotate90() const {
        Polyomino result;
        for (auto& p : cells) {
            result.cells.push_back({-p.second, p.first});
        }
        result.normalize();
        return result;
    }
    
    Polyomino reflectY() const {
        Polyomino result;
        for (auto& p : cells) {
            result.cells.push_back({-p.first, p.second});
        }
        result.normalize();
        return result;
    }
    
    Polyomino transform(int f, int r) const {
        Polyomino result = *this;
        if (f == 1) {
            result = result.reflectY();
        }
        for (int i = 0; i < r; i++) {
            result = result.rotate90();
        }
        result.normalize();
        return result;
    }
    
    pair<int,int> getDimensions() const {
        int maxX = 0, maxY = 0;
        for (auto& p : cells) {
            maxX = max(maxX, p.first);
            maxY = max(maxY, p.second);
        }
        return {maxX + 1, maxY + 1};
    }
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    
    vector<Polyomino> polyominoes(n);
    
    for (int i = 0; i < n; i++) {
        int k;
        cin >> k;
        polyominoes[i].cells.resize(k);
        polyominoes[i].id = i;
        polyominoes[i].size = k;
        for (int j = 0; j < k; j++) {
            cin >> polyominoes[i].cells[j].first >> polyominoes[i].cells[j].second;
        }
        polyominoes[i].normalize();
    }
    
    const int MAX_SIZE = 1000;
    vector<vector<int>> grid(MAX_SIZE, vector<int>(MAX_SIZE, -1));
    
    struct Placement {
        int x, y, r, f;
    };
    
    vector<Placement> placements(n);
    int currentW = 0, currentH = 0;
    
    for (int i = 0; i < n; i++) {
        int bestArea = INT_MAX;
        Placement bestPlacement;
        int bestW = currentW, bestH = currentH;
        bool found = false;
        
        for (int f = 0; f <= 1; f++) {
            for (int r = 0; r < 4; r++) {
                Polyomino transformed = polyominoes[i].transform(f, r);
                auto [pieceW, pieceH] = transformed.getDimensions();
                
                int searchW = min(MAX_SIZE - pieceW, currentW + pieceW);
                int searchH = min(MAX_SIZE - pieceH, currentH + pieceH);
                
                for (int y = 0; y <= searchH; y++) {
                    for (int x = 0; x <= searchW; x++) {
                        bool canPlace = true;
                        
                        for (auto& cell : transformed.cells) {
                            int nx = x + cell.first;
                            int ny = y + cell.second;
                            
                            if (nx >= MAX_SIZE || ny >= MAX_SIZE || grid[ny][nx] != -1) {
                                canPlace = false;
                                break;
                            }
                        }
                        
                        if (canPlace) {
                            int newW = max(currentW, x + pieceW);
                            int newH = max(currentH, y + pieceH);
                            int area = newW * newH;
                            
                            if (area < bestArea || 
                                (area == bestArea && newH < bestH) ||
                                (area == bestArea && newH == bestH && newW < bestW)) {
                                bestArea = area;
                                bestPlacement = {x, y, r, f};
                                bestW = newW;
                                bestH = newH;
                                found = true;
                            }
                        }
                        
                        if (found && bestArea <= currentW * currentH) break;
                    }
                    if (found && bestArea <= currentW * currentH) break;
                }
                if (found && bestArea <= currentW * currentH) break;
            }
            if (found && bestArea <= currentW * currentH) break;
        }
        
        placements[i] = bestPlacement;
        Polyomino transformed = polyominoes[i].transform(bestPlacement.f, bestPlacement.r);
        for (auto& cell : transformed.cells) {
            int nx = bestPlacement.x + cell.first;
            int ny = bestPlacement.y + cell.second;
            grid[ny][nx] = i;
        }
        currentW = bestW;
        currentH = bestH;
    }
    
    cout << currentW << " " << currentH << "\n";
    for (int i = 0; i < n; i++) {
        cout << placements[i].x << " " << placements[i].y << " " 
             << placements[i].r << " " << placements[i].f << "\n";
    }
    
    return 0;
}