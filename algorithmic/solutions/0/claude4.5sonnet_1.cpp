#include <bits/stdc++.h>
using namespace std;

vector<pair<int,int>> applyTransform(vector<pair<int,int>> cells, int rot, int flip) {
    if (flip) {
        for (auto& [x, y] : cells) {
            x = -x;
        }
    }
    
    for (int r = 0; r < rot; r++) {
        for (auto& [x, y] : cells) {
            int nx = y, ny = -x;
            x = nx; y = ny;
        }
    }
    
    int minX = INT_MAX, minY = INT_MAX;
    for (auto [x, y] : cells) {
        minX = min(minX, x);
        minY = min(minY, y);
    }
    for (auto& [x, y] : cells) {
        x -= minX;
        y -= minY;
    }
    
    return cells;
}

bool tryPack(vector<pair<vector<pair<int,int>>, int>>& pieces, int W, int H, 
             vector<array<int,4>>& result) {
    vector<vector<int>> grid(H, vector<int>(W, 0));
    
    for (auto& [cells, id] : pieces) {
        bool placed = false;
        
        for (int flip = 0; flip <= 1 && !placed; flip++) {
            for (int rot = 0; rot < 4 && !placed; rot++) {
                auto oriented = applyTransform(cells, rot, flip);
                
                for (int y = 0; y < H && !placed; y++) {
                    for (int x = 0; x < W && !placed; x++) {
                        bool valid = true;
                        
                        for (auto [cx, cy] : oriented) {
                            int nx = x + cx, ny = y + cy;
                            if (nx >= W || ny >= H || grid[ny][nx]) {
                                valid = false;
                                break;
                            }
                        }
                        
                        if (valid) {
                            for (auto [cx, cy] : oriented) {
                                grid[y + cy][x + cx] = 1;
                            }
                            result[id] = {x, y, rot, flip};
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
    
    vector<pair<vector<pair<int,int>>, int>> pieces(n);
    int totalArea = 0;
    
    for (int i = 0; i < n; i++) {
        int k;
        cin >> k;
        totalArea += k;
        pieces[i].second = i;
        pieces[i].first.resize(k);
        for (int j = 0; j < k; j++) {
            cin >> pieces[i].first[j].first >> pieces[i].first[j].second;
        }
        pieces[i].first = applyTransform(pieces[i].first, 0, 0);
    }
    
    sort(pieces.begin(), pieces.end(), [](auto& a, auto& b) {
        return a.first.size() > b.first.size();
    });
    
    int bestW = 0, bestH = 0, bestA = INT_MAX;
    vector<array<int,4>> bestResult(n);
    
    int side = max(1, (int)sqrt(totalArea));
    
    for (int w = side; w <= side + 30; w++) {
        int hMin = max(1, (totalArea + w - 1) / w);
        for (int h = hMin; h <= hMin + 10; h++) {
            if (w * h >= bestA) continue;
            
            vector<array<int,4>> result(n);
            if (tryPack(pieces, w, h, result)) {
                if (w * h < bestA || (w * h == bestA && (h < bestH || (h == bestH && w < bestW)))) {
                    bestA = w * h;
                    bestW = w;
                    bestH = h;
                    bestResult = result;
                }
            }
        }
    }
    
    cout << bestW << " " << bestH << "\n";
    for (int i = 0; i < n; i++) {
        cout << bestResult[i][0] << " " << bestResult[i][1] << " " 
             << bestResult[i][2] << " " << bestResult[i][3] << "\n";
    }
    
    return 0;
}