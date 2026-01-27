#include <bits/stdc++.h>
using namespace std;

struct Parent {
    unsigned char type; // 0: eps, 1: single, 2: aSa
    unsigned char dir;  // 0:L,1:R,2:U,3:D
    short x, y;         // middle pair for type 2
};

const int MAXV = 900;
const int INF = 1000000007;

int distPal[MAXV][MAXV];
Parent parentPal[MAXV][MAXV];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if(!(cin >> n >> m)) return 0;
    vector<string> g(n);
    for (int i = 0; i < n; ++i) cin >> g[i];
    int sr, sc, er, ec;
    cin >> sr >> sc >> er >> ec;
    --sr; --sc; --er; --ec;

    int id[30][30];
    memset(id, -1, sizeof(id));
    int cnt = 0;
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            if (g[i][j] == '1')
                id[i][j] = cnt++;

    if (id[sr][sc] < 0 || id[er][ec] < 0) {
        cout << -1 << '\n';
        return 0;
    }
    int s_id = id[sr][sc];
    int e_id = id[er][ec];

    // Check connectivity of all blank cells from start (ignoring "stay" moves)
    vector<vector<int>> adj(cnt);
    int dr[4] = {0, 0, -1, 1};
    int dc[4] = {-1, 1, 0, 0};
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            if (id[i][j] == -1) continue;
            int u = id[i][j];
            for (int d = 0; d < 4; ++d) {
                int ni = i + dr[d], nj = j + dc[d];
                if (ni >= 0 && ni < n && nj >= 0 && nj < m && id[ni][nj] != -1) {
                    int v = id[ni][nj];
                    adj[u].push_back(v);
                }
            }
        }
    }

    vector<int> dist0(cnt, -1);
    queue<int> q0;
    dist0[s_id] = 0;
    q0.push(s_id);
    int visited_cnt = 0;
    while (!q0.empty()) {
        int u = q0.front(); q0.pop();
        ++visited_cnt;
        for (int v : adj[u]) {
            if (dist0[v] == -1) {
                dist0[v] = dist0[u] + 1;
                q0.push(v);
            }
        }
    }
    if (visited_cnt != cnt || dist0[e_id] == -1) {
        cout << -1 << '\n';
        return 0;
    }

    // Build transitions including "stay" edges
    char letters[4] = {'L','R','U','D'};
    vector<vector<int>> out[4], in[4];
    for (int d = 0; d < 4; ++d) {
        out[d].assign(cnt, vector<int>());
        in[d].assign(cnt, vector<int>());
    }

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            if (id[i][j] == -1) continue;
            int u = id[i][j];
            for (int d = 0; d < 4; ++d) {
                int ni = i + dr[d], nj = j + dc[d];
                int v;
                if (ni >= 0 && ni < n && nj >= 0 && nj < m && g[ni][nj] == '1') {
                    v = id[ni][nj];
                } else {
                    v = u; // stay in place
                }
                out[d][u].push_back(v);
                in[d][v].push_back(u);
            }
        }
    }

    // Initialize palindrome DP
    for (int i = 0; i < cnt; ++i)
        for (int j = 0; j < cnt; ++j) {
            distPal[i][j] = INF;
            parentPal[i][j].type = 0;
            parentPal[i][j].dir = 0;
            parentPal[i][j].x = parentPal[i][j].y = -1;
        }

    queue<pair<int,int>> q;
    // epsilon transitions
    for (int u = 0; u < cnt; ++u) {
        distPal[u][u] = 0;
        parentPal[u][u].type = 0;
        q.push({u,u});
    }
    // single-letter palindromes
    for (int d = 0; d < 4; ++d) {
        for (int u = 0; u < cnt; ++u) {
            for (int v : out[d][u]) {
                if (distPal[u][v] > 1) {
                    distPal[u][v] = 1;
                    parentPal[u][v].type = 1;
                    parentPal[u][v].dir = (unsigned char)d;
                    parentPal[u][v].x = parentPal[u][v].y = -1;
                    q.push({u,v});
                }
            }
        }
    }

    const int MAXLEN = 1000000;

    // BFS for productions S -> a S a
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        int baseLen = distPal[x][y];
        if (baseLen > MAXLEN) continue;
        for (int d = 0; d < 4; ++d) {
            const auto &preds = in[d][x];
            const auto &succs = out[d][y];
            for (int u : preds) {
                for (int v : succs) {
                    int newLen = baseLen + 2;
                    if (newLen <= MAXLEN && newLen < distPal[u][v]) {
                        distPal[u][v] = newLen;
                        parentPal[u][v].type = 2;
                        parentPal[u][v].dir = (unsigned char)d;
                        parentPal[u][v].x = (short)x;
                        parentPal[u][v].y = (short)y;
                        q.push({u,v});
                    }
                }
            }
        }
    }

    if (distPal[s_id][e_id] == INF || distPal[s_id][e_id] > MAXLEN) {
        cout << -1 << '\n';
        return 0;
    }

    // Reconstruct palindrome path from s_id to e_id
    string res;
    res.reserve(distPal[s_id][e_id]);

    struct Frame { int u, v; char stage; };
    vector<Frame> st;
    st.push_back({s_id, e_id, 0});

    while (!st.empty()) {
        Frame &f = st.back();
        Parent &par = parentPal[f.u][f.v];
        if (par.type == 0) {
            st.pop_back();
        } else if (par.type == 1) {
            res.push_back(letters[par.dir]);
            st.pop_back();
        } else { // type 2
            if (f.stage == 0) {
                res.push_back(letters[par.dir]); // left char
                f.stage = 1;
                st.push_back({par.x, par.y, 0}); // expand middle
            } else {
                res.push_back(letters[par.dir]); // right char
                st.pop_back();
            }
        }
    }

    cout << res << '\n';
    return 0;
}