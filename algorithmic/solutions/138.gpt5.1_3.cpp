#include <bits/stdc++.h>
using namespace std;

struct Op {
    int op, x, y;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m, k;
    if (!(cin >> n >> m >> k)) return 0;
    vector<string> A(n), B(n);
    for (int i = 0; i < n; ++i) cin >> A[i];
    for (int i = 0; i < n; ++i) cin >> B[i];
    
    struct Preset {
        int h, w;
        vector<string> g;
    };
    vector<Preset> presets(k + 1); // 1-based
    
    auto idxChar = [](char c) {
        if ('a' <= c && c <= 'z') return c - 'a';
        if ('A' <= c && c <= 'Z') return 26 + (c - 'A');
        return 52 + (c - '0'); // '0'-'9'
    };
    
    // read presets
    for (int i = 1; i <= k; ++i) {
        int h, w;
        cin >> h >> w;
        presets[i].h = h;
        presets[i].w = w;
        presets[i].g.assign(h, "");
        for (int r = 0; r < h; ++r) cin >> presets[i].g[r];
    }
    
    // map for 1x1 presets for each character
    const int T = 62;
    vector<int> oneByOne(T, -1);
    for (int i = 1; i <= k; ++i) {
        if (presets[i].h == 1 && presets[i].w == 1) {
            char c = presets[i].g[0][0];
            int id = idxChar(c);
            if (oneByOne[id] == -1) oneByOne[id] = i;
        }
    }
    
    // check if we can paint every target cell individually
    bool canPaint = true;
    for (int i = 0; i < n && canPaint; ++i) {
        for (int j = 0; j < m && canPaint; ++j) {
            int id = idxChar(B[i][j]);
            if (oneByOne[id] == -1) canPaint = false;
        }
    }
    
    vector<Op> ops;
    
    if (canPaint) {
        // Just paint each cell to target using 1x1 presets
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < m; ++j) {
                int id = idxChar(B[i][j]);
                int p = oneByOne[id];
                ops.push_back({p, i + 1, j + 1});
            }
        }
        cout << (int)ops.size() << '\n';
        for (auto &op : ops) {
            cout << op.op << ' ' << op.x << ' ' << op.y << '\n';
        }
        return 0;
    }
    
    // Else, ignore presets and try to solve using swaps only.
    // Check if multisets of characters in A and B are equal.
    vector<int> cntA(T, 0), cntB(T, 0);
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j) {
            cntA[idxChar(A[i][j])]++;
            cntB[idxChar(B[i][j])]++;
        }
    if (cntA != cntB) {
        cout << -1 << '\n';
        return 0;
    }
    
    // Function to add a swap operation between adjacent cells
    auto add_swap = [&](int r1, int c1, int r2, int c2) {
        // r, c are 0-based internally, output 1-based
        int op;
        int x, y;
        if (r1 == r2) {
            if (c1 + 1 == c2) {
                op = -1; x = r1 + 1; y = c1 + 1;
            } else if (c1 - 1 == c2) {
                op = -2; x = r1 + 1; y = c1 + 1;
            } else {
                return;
            }
        } else if (c1 == c2) {
            if (r1 + 1 == r2) {
                op = -4; x = r1 + 1; y = c1 + 1;
            } else if (r1 - 1 == r2) {
                op = -3; x = r1 + 1; y = c1 + 1;
            } else {
                return;
            }
        } else {
            return;
        }
        ops.push_back({op, x, y});
    };
    
    // Current board
    vector<string> cur = A;
    
    int N = n * m;
    const int INF = 1e9;
    
    // For each position in row-major order except last, place correct character
    for (int pos = 0; pos < N - 1; ++pos) {
        int ti = pos / m, tj = pos % m;
        char need = B[ti][tj];
        if (cur[ti][tj] == need) continue;
        
        // find position of needed char in remaining part
        int pi = -1, pj = -1;
        int bestDist = INF;
        for (int p = pos + 1; p < N; ++p) {
            int i = p / m, j = p % m;
            if (cur[i][j] == need) {
                int d = abs(i - ti) + abs(j - tj);
                if (d < bestDist) {
                    bestDist = d;
                    pi = i; pj = j;
                }
            }
        }
        if (pi == -1) {
            // Should not happen as counts match
            cout << -1 << '\n';
            return 0;
        }
        
        // BFS for path from (pi,pj) to (ti,tj) avoiding prefix cells (<pos) except destination
        vector<vector<int>> dist(n, vector<int>(m, -1));
        vector<vector<pair<int,int>>> par(n, vector<pair<int,int>>(m, {-1,-1}));
        vector<vector<bool>> blocked(n, vector<bool>(m, false));
        
        for (int p = 0; p < pos; ++p) {
            int bi = p / m, bj = p % m;
            blocked[bi][bj] = true;
        }
        blocked[pi][pj] = false;
        blocked[ti][tj] = false;
        
        queue<pair<int,int>> q;
        q.push({pi, pj});
        dist[pi][pj] = 0;
        
        int dr[4] = {-1,1,0,0};
        int dc[4] = {0,0,-1,1};
        
        while (!q.empty()) {
            auto [x, y] = q.front(); q.pop();
            if (x == ti && y == tj) break;
            for (int dir = 0; dir < 4; ++dir) {
                int nx = x + dr[dir];
                int ny = y + dc[dir];
                if (nx < 0 || nx >= n || ny < 0 || ny >= m) continue;
                if (dist[nx][ny] != -1) continue;
                if (blocked[nx][ny] && !(nx == ti && ny == tj)) continue;
                dist[nx][ny] = dist[x][y] + 1;
                par[nx][ny] = {x, y};
                q.push({nx, ny});
            }
        }
        
        if (dist[ti][tj] == -1) {
            // No path (shouldn't happen)
            cout << -1 << '\n';
            return 0;
        }
        
        // Reconstruct path from src (pi,pj) to dest (ti,tj)
        vector<pair<int,int>> path;
        int cx = ti, cy = tj;
        while (!(cx == pi && cy == pj)) {
            path.push_back({cx, cy});
            auto pr = par[cx][cy];
            cx = pr.first; cy = pr.second;
        }
        path.push_back({pi, pj});
        reverse(path.begin(), path.end());
        
        // Perform swaps along path
        for (int t = 0; t + 1 < (int)path.size(); ++t) {
            int r1 = path[t].first, c1 = path[t].second;
            int r2 = path[t+1].first, c2 = path[t+1].second;
            add_swap(r1, c1, r2, c2);
            swap(cur[r1][c1], cur[r2][c2]);
        }
    }
    
    // By construction, last cell will also match since multisets equal
    if (cur != B) {
        // As a safety, though it should match
        cout << -1 << '\n';
        return 0;
    }
    
    if ((int)ops.size() > 400000) {
        // Should not happen with this algorithm, but respect limit
        cout << -1 << '\n';
        return 0;
    }
    
    cout << (int)ops.size() << '\n';
    for (auto &op : ops) {
        cout << op.op << ' ' << op.x << ' ' << op.y << '\n';
    }
    
    return 0;
}