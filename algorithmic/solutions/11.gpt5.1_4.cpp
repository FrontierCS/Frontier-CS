#include <bits/stdc++.h>
using namespace std;

struct Parent {
    int prev;   // previous pair index
    char dir;   // direction 0..3
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> g(n);
    for (int i = 0; i < n; ++i) cin >> g[i];
    int sr, sc, er, ec;
    cin >> sr >> sc >> er >> ec;
    --sr; --sc; --er; --ec;

    auto inb = [&](int r, int c) {
        return r >= 0 && r < n && c >= 0 && c < m;
    };

    // Check connectivity: all blank cells reachable from start, and exit reachable.
    if (g[sr][sc] != '1' || g[er][ec] != '1') {
        cout << "-1\n";
        return 0;
    }
    int totBlank = 0;
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            if (g[i][j] == '1') ++totBlank;

    vector<vector<int>> vis(n, vector<int>(m, 0));
    queue<pair<int,int>> q0;
    q0.push({sr, sc});
    vis[sr][sc] = 1;
    int cntReach = 1;
    int dr4[4] = {0, 0, -1, 1};
    int dc4[4] = {-1, 1, 0, 0};
    while (!q0.empty()) {
        auto [r, c] = q0.front(); q0.pop();
        for (int d = 0; d < 4; ++d) {
            int nr = r + dr4[d], nc = c + dc4[d];
            if (inb(nr, nc) && !vis[nr][nc] && g[nr][nc] == '1') {
                vis[nr][nc] = 1;
                ++cntReach;
                q0.push({nr, nc});
            }
        }
    }
    if (!vis[er][ec] || cntReach != totBlank) {
        cout << "-1\n";
        return 0;
    }

    // Map blank cells to indices
    vector<int> id(n * m, -1);
    vector<pair<int,int>> cells;
    cells.reserve(totBlank);
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            if (g[i][j] == '1') {
                int idx = (int)cells.size();
                cells.push_back({i, j});
                id[i * m + j] = idx;
            }

    int K = (int)cells.size();
    int sId = id[sr * m + sc];
    int tId = id[er * m + ec];

    // Precompute transitions 'to' and reverse lists 'rev'
    vector<array<int,4>> to(K);
    vector<vector<int>> rev(K * 4); // rev[dest*4 + d] = list of sources

    auto move_from = [&](int r, int c, int d) -> pair<int,int> {
        int nr = r + dr4[d], nc = c + dc4[d];
        if (inb(nr, nc) && g[nr][nc] == '1') return {nr, nc};
        return {r, c};
    };

    for (int idx = 0; idx < K; ++idx) {
        auto [r, c] = cells[idx];
        for (int d = 0; d < 4; ++d) {
            auto [nr, nc] = move_from(r, c, d);
            int nid = id[nr * m + nc];
            to[idx][d] = nid;
        }
    }
    for (int u = 0; u < K; ++u) {
        for (int d = 0; d < 4; ++d) {
            int v = to[u][d];
            rev[v * 4 + d].push_back(u);
        }
    }

    const int INF = 1e9;
    int P = K * K;
    vector<int> dist(P, INF);
    vector<char> mid_char(P, -1);
    vector<Parent> parent(P, {-1, -1});
    queue<int> q;

    // Initialize centers: (i,i) with dist 0, and single-char paths (u,v) with dist 1
    for (int i = 0; i < K; ++i) {
        int idx = i * K + i;
        dist[idx] = 0;
        q.push(idx);
    }
    for (int u = 0; u < K; ++u) {
        for (int d = 0; d < 4; ++d) {
            int v = to[u][d];
            int idx = u * K + v;
            if (dist[idx] > 1) {
                dist[idx] = 1;
                mid_char[idx] = (char)d;
                q.push(idx);
            }
        }
    }

    // BFS on pair graph from centers outward
    while (!q.empty()) {
        int idx = q.front(); q.pop();
        int a = idx / K;
        int b = idx % K;
        int curd = dist[idx];
        for (int d = 0; d < 4; ++d) {
            const vector<int>& srcs = rev[a * 4 + d];
            int y = to[b][d];
            for (int x : srcs) {
                int idx2 = x * K + y;
                if (dist[idx2] > curd + 2) {
                    dist[idx2] = curd + 2;
                    parent[idx2] = {idx, (char)d};
                    q.push(idx2);
                }
            }
        }
    }

    int startIdx = sId * K + tId;
    if (dist[startIdx] >= INF || dist[startIdx] > 1000000) {
        cout << "-1\n";
        return 0;
    }

    int dlen = dist[startIdx];
    string left, right;
    left.reserve((dlen + 1) / 2);
    right.reserve((dlen + 1) / 2);
    auto dirChar = [&](int d) {
        if (d == 0) return 'L';
        if (d == 1) return 'R';
        if (d == 2) return 'U';
        return 'D';
    };

    int cur = startIdx;
    while (dist[cur] > 1) {
        Parent p = parent[cur];
        int dir = (int)p.dir;
        left.push_back(dirChar(dir));
        right.push_back(dirChar(dir));
        cur = p.prev;
    }

    string S;
    S.reserve(dlen);
    S += left;
    if (dist[cur] == 1) {
        int midDir = (int)mid_char[cur];
        S.push_back(dirChar(midDir));
    }
    for (int i = (int)right.size() - 1; i >= 0; --i)
        S.push_back(right[i]);

    // Final safety: verify path ends at exit and is palindrome (optional sanity)
    int r = sr, c = sc;
    for (char ch : S) {
        int d;
        if (ch == 'L') d = 0;
        else if (ch == 'R') d = 1;
        else if (ch == 'U') d = 2;
        else d = 3;
        auto [nr, nc] = move_from(r, c, d);
        r = nr; c = nc;
    }
    if (r != er || c != ec) {
        // Should not happen if BFS is correct, but guard anyway
        cout << "-1\n";
        return 0;
    }

    if ((int)S.size() > 1000000) {
        cout << "-1\n";
        return 0;
    }

    cout << S << '\n';
    return 0;
}