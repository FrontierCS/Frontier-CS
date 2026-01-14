#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    
    vector<vector<pair<int, int>>> polys(n);
    
    for (int i = 0; i < n; i++) {
        int k;
        cin >> k;
        polys[i].resize(k);
        for (int j = 0; j < k; j++) {
            cin >> polys[i][j].first >> polys[i][j].second;
        }
        
        // Normalize to (0,0)
        int minX = INT_MAX, minY = INT_MAX;
        for (auto [x, y] : polys[i]) {
            minX = min(minX, x);
            minY = min(minY, y);
        }
        for (auto& [x, y] : polys[i]) {
            x -= minX;
            y -= minY;
        }
    }
    
    // Grid-based placement
    int gridSize = (int)sqrt(n) + 1;
    int cellSize = 4; // Max size for each cell in grid
    
    vector<array<int, 4>> placements(n);
    
    for (int i = 0; i < n; i++) {
        int row = i / gridSize;
        int col = i % gridSize;
        
        placements[i][0] = col * cellSize; // X
        placements[i][1] = row * cellSize; // Y
        placements[i][2] = 0; // R
        placements[i][3] = 0; // F
    }
    
    // Calculate actual bounding box
    int maxX = 0, maxY = 0;
    for (int i = 0; i < n; i++) {
        for (auto [x, y] : polys[i]) {
            maxX = max(maxX, placements[i][0] + x);
            maxY = max(maxY, placements[i][1] + y);
        }
    }
    
    cout << maxX + 1 << " " << maxY + 1 << "\n";
    for (int i = 0; i < n; i++) {
        cout << placements[i][0] << " " << placements[i][1] << " " 
             << placements[i][2] << " " << placements[i][3] << "\n";
    }
    
    return 0;
}