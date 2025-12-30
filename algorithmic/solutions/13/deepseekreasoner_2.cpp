#include <bits/stdc++.h>
using namespace std;

const int N = 54; // square size, N^2 = 2916 ≤ 3000

int main() {
    int sx, sy;
    cin >> sx >> sy;
    
    // Collect perimeter cells of the square [1, N] x [1, N]
    set<pair<int, int>> per_set;
    for (int x = 1; x <= N; ++x) {
        per_set.insert({x, 1});
        per_set.insert({x, N});
    }
    for (int y = 2; y <= N - 1; ++y) {
        per_set.insert({1, y});
        per_set.insert({N, y});
    }
    vector<pair<int, int>> perimeter(per_set.begin(), per_set.end());
    
    // Sort perimeter by Chebyshev distance from the initial robot position
    sort(perimeter.begin(), perimeter.end(),
         [&](const pair<int, int>& a, const pair<int, int>& b) {
             int da = max(abs(a.first - sx), abs(a.second - sy));
             int db = max(abs(b.first - sx), abs(b.second - sy));
             return da < db;
         });
    
    // Collect interior cells (excluding the perimeter)
    vector<pair<int, int>> interior;
    for (int x = 2; x <= N - 1; ++x)
        for (int y = 2; y <= N - 1; ++y)
            interior.push_back({x, y});
    sort(interior.begin(), interior.end()); // row-major order
    
    // Combine: first mark the perimeter, then the interior
    vector<pair<int, int>> cells = perimeter;
    cells.insert(cells.end(), interior.begin(), interior.end());
    
    int rx = sx, ry = sy;
    size_t idx = 0;
    for (int t = 0; t < 3000 && idx < cells.size(); ++t) {
        int mx = cells[idx].first, my = cells[idx].second;
        ++idx;
        cout << mx << " " << my << endl;
        cout.flush();
        
        int nrx, nry;
        cin >> nrx >> nry;
        if (nrx == 0 && nry == 0)
            return 0; // robot exploded
        rx = nrx;
        ry = nry;
    }
    
    return 0;
}