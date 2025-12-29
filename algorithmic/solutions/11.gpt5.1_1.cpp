#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> grid(n);
    for (int i = 0; i < n; ++i) cin >> grid[i];

    int sr, sc, er, ec;
    cin >> sr >> sc >> er >> ec;
    --sr; --sc; --er; --ec;

    // Map blank cells to ids
    static int id[30][30];
    memset(id, -1, sizeof(id));
    vector<pair<int,int>> coords;
    int B = 0;
    int totalBlank = 0;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            if (grid[i][j] == '1') {
                id[i][j] = B++;
                coords.push_back({i,j});
                ++totalBlank;
            }
        }
    }

    if (grid[sr][sc] != '1' || grid[er][ec] != '1') {
        cout << "-1\n";
        return 0;
    }

    int startID = id[sr][sc];
    int exitID  = id[er][ec];

    // Connectivity check: all blanks must be reachable from start
    {
        vector<vector<int>> vis(n, vector<int>(m, 0));
        queue<pair<int,int>> q;
        if (grid[sr][sc] == '1') {
            vis[sr][sc] = 1;
            q.push({sr, sc});
        }
        int cnt = 0;
        static const int dx4[4] = {0,0,-1,1};
        static const int dy4[4] = {-1,1,0,0};
        while (!q.empty()) {
            auto [x,y] = q.front(); q.pop();
            ++cnt;
            for (int d = 0; d < 4; ++d) {
                int nx = x + dx4[d];
                int ny = y + dy4[d];
                if (nx < 0 || nx >= n || ny < 0 || ny >= m) continue;
                if (grid[nx][ny] == '1' && !vis[nx][ny]) {
                    vis[nx][ny] = 1;
                    q.push({nx,ny});
                }
            }
        }
        if (cnt != totalBlank) {
            cout << "-1\n";
            return 0;
        }
    }

    if (B == 0) {
        cout << "-1\n";
        return 0;
    }

    // Precompute transitions succ and predecessors pred
    static const char DIRS[4] = {'L','R','U','D'};
    static const int dx[4] = {0,0,-1,1};
    static const int dy[4] = {-1,1,0,0};

    vector<array<int,4>> succ(B);
    for (int v = 0; v < B; ++v) {
        int x = coords[v].first;
        int y = coords[v].second;
        for (int d = 0; d < 4; ++d) {
            int nx = x + dx[d];
            int ny = y + dy[d];
            if (nx >= 0 && nx < n && ny >= 0 && ny < m && grid[nx][ny] == '1') {
                succ[v][d] = id[nx][ny];
            } else {
                succ[v][d] = v; // blocked -> stay
            }
        }
    }

    vector<array<vector<int>,4>> pred(B);
    for (int u = 0; u < B; ++u) {
        for (int d = 0; d < 4; ++d) {
            int v = succ[u][d];
            pred[v][d].push_back(u);
        }
    }

    int TOT = B * B;
    vector<uint8_t> visited(TOT, 0);
    vector<int> parent(TOT, -1);
    vector<char> parentChar(TOT, 0);
    vector<int> dist(TOT, 0);

    auto encode = [B](int u, int v) { return u * B + v; };

    int root = encode(startID, exitID);
    queue<int> q;
    q.push(root);
    visited[root] = 1;
    parent[root] = -1;
    dist[root] = 0;

    const int INF = (int)1e9;
    int bestLen = INF;
    bool bestIsOdd = false;
    int bestState = -1;
    char bestCenterChar = 0;
    bool found = false;

    while (!q.empty()) {
        int idx = q.front(); q.pop();
        int d = dist[idx];
        if (found && 2 * d >= bestLen) break;

        int u = idx / B;
        int v = idx % B;

        // Even-length candidate: center vertex
        if (u == v) {
            int len = 2 * d;
            if (len < bestLen) {
                bestLen = len;
                bestIsOdd = false;
                bestState = idx;
                found = true;
            }
        }

        // Odd-length candidates: center edge
        for (int c = 0; c < 4; ++c) {
            if (succ[u][c] == v) {
                int len = 2 * d + 1;
                if (len < bestLen) {
                    bestLen = len;
                    bestIsOdd = true;
                    bestState = idx;
                    bestCenterChar = DIRS[c];
                    found = true;
                }
            }
        }

        // Expand to neighbors
        for (int c = 0; c < 4; ++c) {
            int nu = succ[u][c];
            const vector<int> &pv = pred[v][c];
            for (int nv : pv) {
                int nxt = encode(nu, nv);
                if (!visited[nxt]) {
                    visited[nxt] = 1;
                    parent[nxt] = idx;
                    parentChar[nxt] = DIRS[c];
                    dist[nxt] = d + 1;
                    q.push(nxt);
                }
            }
        }
    }

    if (!found || bestLen > 1000000) {
        cout << "-1\n";
        return 0;
    }

    // Reconstruct palindrome string
    vector<char> half;
    int cur = bestState;
    while (parent[cur] != -1) {
        half.push_back(parentChar[cur]);
        cur = parent[cur];
    }
    reverse(half.begin(), half.end());

    string ans;
    ans.reserve(bestLen);
    for (char c : half) ans.push_back(c);
    if (bestIsOdd) ans.push_back(bestCenterChar);
    for (int i = (int)half.size() - 1; i >= 0; --i) ans.push_back(half[i]);

    cout << ans << '\n';
    return 0;
}