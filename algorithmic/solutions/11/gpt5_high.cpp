#include <bits/stdc++.h>
using namespace std;

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
    if (g[sr][sc] != '1' || g[er][ec] != '1') {
        cout << -1 << '\n';
        return 0;
    }
    
    // Map cells to ids
    vector<vector<int>> id(n, vector<int>(m, -1));
    vector<pair<int,int>> pos;
    int B = 0;
    int ones = 0;
    for (int i = 0; i < n; ++i) for (int j = 0; j < m; ++j) if (g[i][j] == '1') {
        id[i][j] = B++;
        pos.push_back({i,j});
        ones++;
    }
    int sid = id[sr][sc];
    int eid = id[er][ec];
    
    // Check connectivity: all '1' cells must be reachable from start
    vector<int> vis_conn(B, 0);
    queue<int> qc;
    qc.push(sid);
    vis_conn[sid] = 1;
    int dr[4] = {0,0,-1,1};
    int dc[4] = {-1,1,0,0};
    while (!qc.empty()) {
        int u = qc.front(); qc.pop();
        auto [r,c] = pos[u];
        for (int d = 0; d < 4; ++d) {
            int nr = r + dr[d], nc = c + dc[d];
            if (nr < 0 || nr >= n || nc < 0 || nc >= m) continue;
            if (g[nr][nc] != '1') continue;
            int v = id[nr][nc];
            if (!vis_conn[v]) {
                vis_conn[v] = 1;
                qc.push(v);
            }
        }
    }
    for (int i = 0; i < B; ++i) {
        if (!vis_conn[i]) {
            cout << -1 << '\n';
            return 0;
        }
    }
    
    // Precompute forward maps f[dir][id] and preimages pre[dir][dest]
    // dir indices: 0:L, 1:R, 2:U, 3:D
    const char DIRCH[4] = {'L','R','U','D'};
    int fwd[4][900]; // max B 900
    vector<int> pre[4][900];
    for (int i = 0; i < B; ++i) {
        auto [r,c] = pos[i];
        // L
        if (c-1 >= 0 && g[r][c-1] == '1') fwd[0][i] = id[r][c-1];
        else fwd[0][i] = i;
        // R
        if (c+1 < m && g[r][c+1] == '1') fwd[1][i] = id[r][c+1];
        else fwd[1][i] = i;
        // U
        if (r-1 >= 0 && g[r-1][c] == '1') fwd[2][i] = id[r-1][c];
        else fwd[2][i] = i;
        // D
        if (r+1 < n && g[r+1][c] == '1') fwd[3][i] = id[r+1][c];
        else fwd[3][i] = i;
    }
    for (int d = 0; d < 4; ++d) {
        for (int i = 0; i < B; ++i) pre[d][i].clear();
    }
    for (int i = 0; i < B; ++i) {
        for (int d = 0; d < 4; ++d) {
            int j = fwd[d][i];
            pre[d][j].push_back(i);
        }
    }
    
    // Build DFS path P visiting all cells (returns to start)
    vector<int> seen(n*m, 0);
    vector<string> Pparts;
    string P;
    int opp[4] = {1,0,3,2};
    // We'll use order: R, D, L, U
    int order[4] = {1, 3, 0, 2};
    function<void(int,int)> dfs = [&](int r, int c) {
        seen[r*m + c] = 1;
        for (int t = 0; t < 4; ++t) {
            int d = order[t];
            int nr = r + dr[d], nc = c + dc[d];
            if (nr < 0 || nr >= n || nc < 0 || nc >= m) continue;
            if (g[nr][nc] != '1') continue;
            if (!seen[nr*m + nc]) {
                P.push_back(DIRCH[d]);
                dfs(nr, nc);
                P.push_back(DIRCH[opp[d]]);
            }
        }
    };
    dfs(sr, sc);
    // P visits all and returns to start
    
    // Compute u = f_P(sid)
    int u = sid;
    auto charToDir = [&](char ch)->int {
        if (ch=='L') return 0;
        if (ch=='R') return 1;
        if (ch=='U') return 2;
        return 3;
    };
    for (char ch : P) {
        int d = charToDir(ch);
        u = fwd[d][u];
    }
    // Compute V = Pre_P({eid})
    vector<char> V(B, 0), Vnext(B, 0);
    V[eid] = 1;
    for (char ch : P) {
        int d = charToDir(ch);
        fill(Vnext.begin(), Vnext.end(), 0);
        for (int y = 0; y < B; ++y) if (V[y]) {
            for (int x : pre[d][y]) Vnext[x] = 1;
        }
        V.swap(Vnext);
    }
    
    // BFS on pair graph from initial states (u, v) for v in V to closable
    int BB = B * B;
    vector<char> vis(BB, 0);
    vector<int> par(BB, -1);
    vector<unsigned char> parMove(BB, 0);
    deque<int> q;
    for (int v = 0; v < B; ++v) if (V[v]) {
        int pid = u * B + v;
        vis[pid] = 1;
        par[pid] = -1;
        q.push_back(pid);
    }
    bool found = false;
    bool odd = false;
    char center = 0;
    int endID = -1;
    while (!q.empty() && !found) {
        size_t lvlSize = q.size();
        int evenEnd = -1;
        int oddEnd = -1;
        char oddCenter = 0;
        for (size_t it = 0; it < lvlSize; ++it) {
            int pid = q.front(); q.pop_front();
            int x = pid / B;
            int y = pid % B;
            // closability checks
            if (evenEnd == -1 && x == y) {
                evenEnd = pid;
            }
            if (evenEnd == -1 && oddEnd == -1) {
                for (int b = 0; b < 4; ++b) {
                    if (fwd[b][x] == y) {
                        oddEnd = pid;
                        oddCenter = DIRCH[b];
                        break;
                    }
                }
            }
            // Expand neighbors
            for (int c = 0; c < 4; ++c) {
                int x2 = fwd[c][x];
                auto &lst = pre[c][y];
                for (int z : lst) {
                    int nid = x2 * B + z;
                    if (!vis[nid]) {
                        vis[nid] = 1;
                        par[nid] = pid;
                        parMove[nid] = (unsigned char)c;
                        q.push_back(nid);
                    }
                }
            }
        }
        if (evenEnd != -1) {
            found = true;
            odd = false;
            endID = evenEnd;
            break;
        }
        if (oddEnd != -1) {
            found = true;
            odd = true;
            endID = oddEnd;
            center = oddCenter;
            break;
        }
    }
    if (!found) {
        // As a fallback, try without prefix (P empty)
        // Start from (sid, eid)
        fill(vis.begin(), vis.end(), 0);
        fill(par.begin(), par.end(), -1);
        fill(parMove.begin(), parMove.end(), 0);
        q.clear();
        int startPair = sid * B + eid;
        vis[startPair] = 1;
        q.push_back(startPair);
        found = false; odd = false; endID = -1; center = 0;
        while (!q.empty() && !found) {
            size_t lvlSize = q.size();
            int evenEnd = -1;
            int oddEnd = -1;
            char oddCenter = 0;
            for (size_t it = 0; it < lvlSize; ++it) {
                int pid = q.front(); q.pop_front();
                int x = pid / B;
                int y = pid % B;
                if (evenEnd == -1 && x == y) evenEnd = pid;
                if (evenEnd == -1 && oddEnd == -1) {
                    for (int b = 0; b < 4; ++b) {
                        if (fwd[b][x] == y) {
                            oddEnd = pid;
                            oddCenter = DIRCH[b];
                            break;
                        }
                    }
                }
                for (int c = 0; c < 4; ++c) {
                    int x2 = fwd[c][x];
                    auto &lst = pre[c][y];
                    for (int z : lst) {
                        int nid = x2 * B + z;
                        if (!vis[nid]) {
                            vis[nid] = 1;
                            par[nid] = pid;
                            parMove[nid] = (unsigned char)c;
                            q.push_back(nid);
                        }
                    }
                }
            }
            if (evenEnd != -1) {
                found = true;
                odd = false;
                endID = evenEnd;
                break;
            }
            if (oddEnd != -1) {
                found = true;
                odd = true;
                endID = oddEnd;
                center = oddCenter;
                break;
            }
        }
        if (!found) {
            cout << -1 << '\n';
            return 0;
        } else {
            // In this fallback, P must be empty
            P.clear();
            u = sid;
        }
    }
    
    // Reconstruct Q from BFS
    vector<char> Q;
    int cur = endID;
    while (par[cur] != -1) {
        Q.push_back(DIRCH[parMove[cur]]);
        cur = par[cur];
    }
    reverse(Q.begin(), Q.end());
    
    // Build final palindrome: prefix = P + Q; center maybe; suffix reverse(prefix)
    string prefix;
    prefix.reserve(P.size() + Q.size());
    prefix += P;
    for (char c : Q) prefix.push_back(c);
    string ans = prefix;
    if (odd) ans.push_back(center);
    string suffix = prefix;
    reverse(suffix.begin(), suffix.end());
    ans += suffix;
    
    if (ans.size() > 1000000u) {
        cout << -1 << '\n';
        return 0;
    }
    cout << ans << '\n';
    return 0;
}