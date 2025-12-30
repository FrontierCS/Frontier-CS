#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int N;
    cin >> N;
    int sr, sc;
    cin >> sr >> sc;
    sr--; sc--;
    
    // Knight moves
    const int dx[8] = {2, 2, -2, -2, 1, 1, -1, -1};
    const int dy[8] = {1, -1, 1, -1, 2, -2, 2, -2};
    
    // Initialize degree and visited
    vector<vector<int>> deg(N, vector<int>(N, 0));
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            for (int k = 0; k < 8; k++) {
                int ni = i + dx[k];
                int nj = j + dy[k];
                if (ni >= 0 && ni < N && nj >= 0 && nj < N) {
                    deg[i][j]++;
                }
            }
        }
    }
    
    vector<vector<bool>> vis(N, vector<bool>(N, false));
    vector<pair<int,int>> path;
    
    // Function to update degrees after visiting (x,y)
    auto update_deg = [&](int x, int y) {
        for (int k = 0; k < 8; k++) {
            int nx = x + dx[k];
            int ny = y + dy[k];
            if (nx >= 0 && nx < N && ny >= 0 && ny < N && !vis[nx][ny]) {
                deg[nx][ny]--;
            }
        }
    };
    
    // Start
    vis[sr][sc] = true;
    path.emplace_back(sr, sc);
    update_deg(sr, sc);
    
    int curx = sr, cury = sc;
    
    while (true) {
        vector<array<int,4>> candidates; // d1, min_d2, nx, ny
        for (int k = 0; k < 8; k++) {
            int nx = curx + dx[k];
            int ny = cury + dy[k];
            if (nx >= 0 && nx < N && ny >= 0 && ny < N && !vis[nx][ny]) {
                int d1 = deg[nx][ny];
                // compute min_d2 among unvisited neighbors of (nx,ny)
                int min_d2 = 9; // large
                for (int k2 = 0; k2 < 8; k2++) {
                    int nx2 = nx + dx[k2];
                    int ny2 = ny + dy[k2];
                    if (nx2 >= 0 && nx2 < N && ny2 >= 0 && ny2 < N && !vis[nx2][ny2]) {
                        min_d2 = min(min_d2, deg[nx2][ny2]);
                    }
                }
                // if d1 == 0, min_d2 is irrelevant; set to 9 to prioritize others if any.
                if (d1 == 0) min_d2 = 9;
                candidates.push_back({d1, min_d2, nx, ny});
            }
        }
        if (candidates.empty()) break;
        
        // Separate candidates with d1 > 0 and d1 == 0
        vector<array<int,4>> good, dead;
        for (auto& arr : candidates) {
            if (arr[0] > 0) good.push_back(arr);
            else dead.push_back(arr);
        }
        array<int,4> chosen;
        if (!good.empty()) {
            // sort good by d1 ascending, then min_d2 ascending
            sort(good.begin(), good.end(), [](const array<int,4>& a, const array<int,4>& b) {
                if (a[0] != b[0]) return a[0] < b[0];
                return a[1] < b[1];
            });
            chosen = good[0];
        } else {
            // all are dead ends, choose any
            chosen = dead[0];
        }
        
        int nx = chosen[2], ny = chosen[3];
        vis[nx][ny] = true;
        path.emplace_back(nx, ny);
        update_deg(nx, ny);
        curx = nx;
        cury = ny;
    }
    
    // Output
    cout << path.size() << '\n';
    for (auto& p : path) {
        cout << p.first+1 << ' ' << p.second+1 << '\n';
    }
    
    return 0;
}