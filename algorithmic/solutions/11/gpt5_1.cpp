#include <bits/stdc++.h>
using namespace std;

static const int DX[4] = {0, 0, -1, 1};   // L, R, U, D
static const int DY[4] = {-1, 1, 0, 0};
static const char DIRC[4] = {'L','R','U','D'};
static const int OPP[4] = {1,0,3,2};

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

    vector<vector<int>> id(n, vector<int>(m, -1));
    vector<pair<int,int>> cells;
    int B = 0;
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            if (grid[i][j] == '1') {
                id[i][j] = B++;
                cells.emplace_back(i,j);
            }

    if (sr < 0 || sr >= n || sc < 0 || sc >= m || er < 0 || er >= n || ec < 0 || ec >= m) {
        cout << -1 << '\n';
        return 0;
    }
    if (id[sr][sc] == -1 || id[er][ec] == -1) {
        cout << -1 << '\n';
        return 0;
    }
    int S = id[sr][sc], E = id[er][ec];

    // Precompute next state for each cell and direction (with "stay" behavior)
    vector<array<int,4>> nxt(B);
    for (int u = 0; u < B; ++u) {
        int x = cells[u].first, y = cells[u].second;
        for (int d = 0; d < 4; ++d) {
            int nx = x + DX[d], ny = y + DY[d];
            if (nx >= 0 && nx < n && ny >= 0 && ny < m && id[nx][ny] != -1) nxt[u][d] = id[nx][ny];
            else nxt[u][d] = u;
        }
    }

    // Check connectivity from S: must reach all blanks and E
    vector<char> vis(B, 0);
    queue<int> q;
    vis[S] = 1;
    q.push(S);
    int cnt = 1;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int d = 0; d < 4; ++d) {
            int v = nxt[u][d];
            if (v != u && !vis[v]) {
                vis[v] = 1;
                q.push(v);
                ++cnt;
            }
        }
    }
    if (!vis[E] || cnt != B) {
        cout << -1 << '\n';
        return 0;
    }

    // Helper lambdas
    auto simulate_from = [&](int start, const string &moves) {
        int pos = start;
        for (char c : moves) {
            int d = (c=='L'?0:(c=='R'?1:(c=='U'?2:3)));
            pos = nxt[pos][d];
        }
        return pos;
    };

    // Build DFS traversal path P that visits all and returns to S
    string P;
    vector<char> used(B, 0);
    function<void(int)> dfs = [&](int u) {
        used[u] = 1;
        // Default neighbor direction order; can be tweaked if needed
        int x = cells[u].first, y = cells[u].second;
        for (int d = 0; d < 4; ++d) {
            int nxr = x + DX[d], nyc = y + DY[d];
            if (nxr >= 0 && nxr < n && nyc >= 0 && nyc < m && id[nxr][nyc] != -1) {
                int v = id[nxr][nyc];
                if (!used[v]) {
                    P.push_back(DIRC[d]);
                    dfs(v);
                    P.push_back(DIRC[OPP[d]]);
                }
            }
        }
    };
    dfs(S);

    // Compute reverse(P), and mapping after reverse(P) for all states
    string Prev = P;
    reverse(Prev.begin(), Prev.end());

    vector<int> mapAfterRevP(B);
    for (int v = 0; v < B; ++v) {
        int pos = v;
        for (char c : Prev) {
            int d = (c=='L'?0:(c=='R'?1:(c=='U'?2:3)));
            pos = nxt[pos][d];
        }
        mapAfterRevP[v] = pos;
    }
    vector<char> isT(B, 0);
    for (int v = 0; v < B; ++v) if (mapAfterRevP[v] == E) isT[v] = 1;

    // Evaluate function phi(W, p) for W defined by pairs list ds (outer to inner) and optional center c
    auto eval_phi = [&](const vector<int>& ds, bool hasCenter, int centerChar) -> int {
        function<int(int,int)> rec = [&](int idx, int posIn) -> int {
            if (idx == (int)ds.size()) {
                if (!hasCenter) return posIn;
                return nxt[posIn][centerChar];
            } else {
                int d = ds[idx];
                int pos1 = nxt[posIn][d];
                int inner = rec(idx+1, pos1);
                return nxt[inner][d];
            }
        };
        return rec(0, S);
    };

    // Try direct without any W
    {
        int qpos = simulate_from(S, ""); // S unchanged
        if (isT[qpos]) {
            string Sfinal = P + "" + Prev;
            cout << Sfinal << '\n';
            return 0;
        }
    }

    // Enumerate palindromic W: ds length up to maxPairs, optional center
    bool found = false;
    string Wstr_found;
    int maxPairs = 9; // Depth limit; should be plenty
    vector<int> ds;
    function<void(int,int)> enumerate = [&](int idx, int k) {
        if (found) return;
        if (idx == k) {
            // No center
            int qpos = eval_phi(ds, false, -1);
            if (isT[qpos]) {
                // reconstruct W string
                string Wstr;
                for (int i = 0; i < k; ++i) Wstr.push_back(DIRC[ds[i]]);
                for (int i = k-1; i >= 0; --i) Wstr.push_back(DIRC[ds[i]]);
                Wstr_found = Wstr;
                found = true;
                return;
            }
            // With center
            for (int c = 0; c < 4 && !found; ++c) {
                int qpos2 = eval_phi(ds, true, c);
                if (isT[qpos2]) {
                    string Wstr;
                    for (int i = 0; i < k; ++i) Wstr.push_back(DIRC[ds[i]]);
                    Wstr.push_back(DIRC[c]);
                    for (int i = k-1; i >= 0; --i) Wstr.push_back(DIRC[ds[i]]);
                    Wstr_found = Wstr;
                    found = true;
                    return;
                }
            }
            return;
        } else {
            for (int d = 0; d < 4 && !found; ++d) {
                ds[idx] = d;
                enumerate(idx+1, k);
            }
        }
    };

    for (int k = 0; k <= maxPairs && !found; ++k) {
        ds.assign(k, 0);
        enumerate(0, k);
    }

    if (!found) {
        cout << -1 << '\n';
        return 0;
    }

    string Sfinal = P + Wstr_found + Prev;
    // Optional final verification (not necessary but safe)
    int finalPos = simulate_from(S, Sfinal);
    if (finalPos != E) {
        // Should not happen due to construction
        cout << -1 << '\n';
        return 0;
    }

    cout << Sfinal << '\n';
    return 0;
}