#include <bits/stdc++.h>
using namespace std;

struct PalResult {
    vector<int> half; // sequence of dirs for the left half
    bool odd = false;
    int center = -1;  // dir for center if odd
    bool ok = false;
};

// Directions: 0=U,1=D,2=L,3=R
static const int DR[4] = {-1, 1, 0, 0};
static const int DC[4] = {0, 0, -1, 1};
static const char DCH[4] = {'U','D','L','R'};
static int OPP[4] = {1,0,3,2};

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

    // Map blank cells to IDs
    vector<vector<int>> id(n, vector<int>(m, -1));
    vector<pair<int,int>> pos;
    int N = 0;
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            if (g[i][j] == '1') {
                id[i][j] = N++;
                pos.push_back({i,j});
            }

    if (id[sr][sc] == -1 || id[er][ec] == -1) {
        cout << -1 << "\n";
        return 0;
    }

    // Build adjacency for connectivity (undirected)
    vector<vector<int>> adj(N);
    for (int u = 0; u < N; ++u) {
        int r = pos[u].first, c = pos[u].second;
        for (int d = 0; d < 4; ++d) {
            int nr = r + DR[d], nc = c + DC[d];
            if (nr >= 0 && nr < n && nc >= 0 && nc < m && id[nr][nc] != -1) {
                int v = id[nr][nc];
                adj[u].push_back(v);
            }
        }
    }

    // Check all blank cells are connected and e reachable from s
    int S = id[sr][sc];
    int E = id[er][ec];
    vector<int> q;
    vector<char> vis(N, 0);
    q.push_back(S);
    vis[S] = 1;
    for (size_t qi = 0; qi < q.size(); ++qi) {
        int u = q[qi];
        for (int v : adj[u]) if (!vis[v]) { vis[v] = 1; q.push_back(v); }
    }
    if (!vis[E]) {
        cout << -1 << "\n";
        return 0;
    }
    for (int u = 0; u < N; ++u) if (g[pos[u].first][pos[u].second] == '1' && !vis[u]) {
        cout << -1 << "\n";
        return 0;
    }

    // Precompute transition functions f_d: trans[d][u] = new position after attempting d at u
    vector<array<int,4>> trans(N);
    for (int u = 0; u < N; ++u) {
        int r = pos[u].first, c = pos[u].second;
        for (int d = 0; d < 4; ++d) {
            int nr = r + DR[d], nc = c + DC[d];
            if (nr >= 0 && nr < n && nc >= 0 && nc < m && id[nr][nc] != -1) {
                trans[u][d] = id[nr][nc];
            } else {
                trans[u][d] = u; // stay if invalid
            }
        }
    }

    // Precompute preimages: for each d and y, list of r such that trans[r][d] == y
    vector<vector<array<int,2>>> pre(4, vector<array<int,2>>(N, array<int,2>{-1,-1}));
    vector<vector<int>> precnt(4, vector<int>(N, 0));
    for (int u = 0; u < N; ++u) {
        for (int d = 0; d < 4; ++d) {
            int y = trans[u][d];
            int &cnt = precnt[d][y];
            if (cnt < 2) pre[d][y][cnt] = u;
            cnt = min(cnt+1, 2);
        }
    }

    auto pal_bfs = [&](int A, int B)->PalResult {
        PalResult res;
        int M = N * N;
        vector<int> dist(M, -1), par(M, -1);
        vector<unsigned char> par_dir(M, 0);
        deque<int> dq;
        auto enc = [&](int x, int y){ return x * N + y; };
        auto dec = [&](int code){ return pair<int,int>(code / N, code % N); };
        int start = enc(A,B);
        dist[start] = 0;
        dq.push_back(start);
        bool found = false;
        int bestDist = INT_MAX;
        int goal = -1;
        bool goalOdd = false;
        int goalOddCenter = -1;

        while (!dq.empty() && !found) {
            int sz = dq.size();
            // record candidates at this level
            int evenGoalAtLevel = -1;
            int oddGoalAtLevel = -1;
            int oddCenterAtLevel = -1;
            vector<int> next;
            next.reserve(sz * 8);
            for (int it = 0; it < sz; ++it) {
                int ucode = dq.front(); dq.pop_front();
                auto [x, y] = dec(ucode);
                if (evenGoalAtLevel == -1 && x == y) {
                    evenGoalAtLevel = ucode;
                    // don't break yet; keep scanning rest of this level to maintain minimality
                } else if (oddGoalAtLevel == -1) {
                    // check odd base possibility
                    for (int d = 0; d < 4; ++d) {
                        if (trans[x][d] == y) {
                            oddGoalAtLevel = ucode;
                            oddCenterAtLevel = d;
                            break;
                        }
                    }
                }
                // expand neighbors
                for (int d = 0; d < 4; ++d) {
                    int x2 = trans[x][d];
                    int cnt = precnt[d][y];
                    for (int k = 0; k < cnt; ++k) {
                        int r = pre[d][y][k];
                        if (r < 0) continue;
                        int vcode = enc(x2, r);
                        if (dist[vcode] == -1) {
                            dist[vcode] = dist[ucode] + 1;
                            par[vcode] = ucode;
                            par_dir[vcode] = (unsigned char)d;
                            next.push_back(vcode);
                        }
                    }
                }
            }
            if (evenGoalAtLevel != -1) {
                found = true;
                goal = evenGoalAtLevel;
                goalOdd = false;
                break;
            }
            if (oddGoalAtLevel != -1) {
                found = true;
                goal = oddGoalAtLevel;
                goalOdd = true;
                goalOddCenter = oddCenterAtLevel;
                break;
            }
            for (int v : next) dq.push_back(v);
        }

        if (!found) {
            res.ok = false;
            return res;
        }

        // reconstruct path from start to goal
        vector<int> stack_dirs;
        for (int v = goal; v != start; v = par[v]) {
            stack_dirs.push_back((int)par_dir[v]);
        }
        reverse(stack_dirs.begin(), stack_dirs.end());
        res.half = stack_dirs;
        res.odd = goalOdd;
        res.center = goalOddCenter;
        res.ok = true;
        return res;
    };

    // Get palindrome mapping from S to E (prefer even)
    PalResult base = pal_bfs(S, E);
    if (!base.ok) {
        cout << -1 << "\n";
        return 0;
    }
    // Build base palindrome string S0 and compute anchor
    string leftHalf;
    int anchor = S;
    for (int d : base.half) {
        leftHalf.push_back(DCH[d]);
        anchor = trans[anchor][d];
    }
    string rightHalf = leftHalf;
    reverse(rightHalf.begin(), rightHalf.end());
    string S0 = leftHalf;
    if (base.odd) {
        S0.push_back(DCH[base.center]);
        // update anchor after center? For insertion of loops, easier to target even center.
        // We'll convert to even by surrounding with two same letters if needed.
        // But we can keep odd: We'll use anchor as state before center.
        // We will insert our big palindrome exactly at the center before the center letter.
    }
    S0 += rightHalf;

    // Build exploration path Z from anchor that visits all cells (closed DFS returning to anchor)
    vector<char> vis2(N, 0);
    vector<int> Z; Z.reserve(2 * max(1, N-1));
    function<void(int)> dfs = [&](int u) {
        vis2[u] = 1;
        int r = pos[u].first, c = pos[u].second;
        for (int d = 0; d < 4; ++d) {
            int v = trans[u][d];
            if (v != u && !vis2[v]) {
                Z.push_back(d);
                dfs(v);
                Z.push_back(OPP[d]);
            }
        }
    };
    dfs(anchor);

    // Compute H = F_reverse(Z)
    vector<int> H(N);
    for (int i = 0; i < N; ++i) H[i] = i;
    for (int i = (int)Z.size() - 1; i >= 0; --i) {
        int d = Z[i];
        for (int u = 0; u < N; ++u) {
            H[u] = trans[H[u]][d];
        }
    }
    // q = F_Z(anchor)
    int qpos = anchor;
    for (int d : Z) qpos = trans[qpos][d];

    // P = { r : H[r] == anchor }
    vector<int> Pset;
    for (int r = 0; r < N; ++r) if (H[r] == anchor) Pset.push_back(r);

    // Find K palindrome mapping from qpos to any r in Pset
    string Kstr;
    bool Kfound = false;
    if (!Pset.empty()) {
        for (int rtarget : Pset) {
            PalResult Kres = pal_bfs(qpos, rtarget);
            if (Kres.ok) {
                string halfK;
                for (int d : Kres.half) halfK.push_back(DCH[d]);
                string revHalfK = halfK; reverse(revHalfK.begin(), revHalfK.end());
                Kstr = halfK;
                if (Kres.odd) Kstr.push_back(DCH[Kres.center]);
                Kstr += revHalfK;
                Kfound = true;
                break;
            }
        }
    }
    if (!Kfound) {
        // Fallback: try open DFS that ends at a leaf far from anchor
        // Build BFS tree from anchor to get a far leaf
        vector<int> dist1(N, -1), parent1(N, -1);
        deque<int> dq;
        dq.push_back(anchor);
        dist1[anchor] = 0;
        while (!dq.empty()) {
            int u = dq.front(); dq.pop_front();
            for (int v : adj[u]) if (dist1[v] == -1) {
                dist1[v] = dist1[u] + 1;
                parent1[v] = u;
                dq.push_back(v);
            }
        }
        int leaf = anchor;
        for (int i = 0; i < N; ++i) if ((int)adj[i].size() <= 1 && dist1[i] != -1) {
            if (dist1[i] > dist1[leaf]) leaf = i;
        }
        // Build DFS path that ends at leaf: traverse tree, but do not backtrack from leaf branch
        vector<int> tin(N, 0), tout(N, 0);
        vector<int> Z2;
        vector<char> used(N, 0);
        // build adjacency order using tree edges
        vector<vector<int>> tree(N);
        for (int v = 0; v < N; ++v) {
            if (parent1[v] != -1) {
                tree[parent1[v]].push_back(v);
                tree[v].push_back(parent1[v]);
            }
        }
        vector<int> parent2(N, -1);
        // DFS on tree, avoiding backtracking from leaf
        function<void(int)> dfs2 = [&](int u){
            used[u] = 1;
            for (int v : tree[u]) if (v != parent2[u]) {
                parent2[v] = u;
                int r1 = pos[u].first, c1 = pos[u].second;
                int r2 = pos[v].first, c2 = pos[v].second;
                int dd;
                if (r2 == r1-1 && c2 == c1) dd = 0;
                else if (r2 == r1+1 && c2 == c1) dd = 1;
                else if (r2 == r1 && c2 == c1-1) dd = 2;
                else dd = 3;
                Z2.push_back(dd);
                dfs2(v);
                if (v != leaf) {
                    Z2.push_back(OPP[dd]);
                }
            }
        };
        parent2[anchor] = -1;
        dfs2(anchor);
        // recompute H with Z2
        vector<int> H2(N);
        for (int i = 0; i < N; ++i) H2[i] = i;
        for (int i = (int)Z2.size() - 1; i >= 0; --i) {
            int d = Z2[i];
            for (int u = 0; u < N; ++u) H2[u] = trans[H2[u]][d];
        }
        int q2 = anchor;
        for (int d : Z2) q2 = trans[q2][d];
        vector<int> P2;
        for (int r = 0; r < N; ++r) if (H2[r] == anchor) P2.push_back(r);
        if (!P2.empty()) {
            for (int rtarget : P2) {
                PalResult Kres = pal_bfs(q2, rtarget);
                if (Kres.ok) {
                    string halfK;
                    for (int d : Kres.half) halfK.push_back(DCH[d]);
                    string revHalfK = halfK; reverse(revHalfK.begin(), revHalfK.end());
                    Kstr = halfK;
                    if (Kres.odd) Kstr.push_back(DCH[Kres.center]);
                    Kstr += revHalfK;
                    // Use Z2 instead of Z
                    Z = Z2;
                    H = H2;
                    qpos = q2;
                    Kfound = true;
                    break;
                }
            }
        }
        if (!Kfound) {
            // As a last resort, set Z empty and K empty to avoid failure (may not cover all cells)
            Z.clear();
            Kstr.clear();
        }
    }

    // Build T = Z + K + reverse(Z)
    string Zstr;
    Zstr.reserve(Z.size());
    for (int d : Z) Zstr.push_back(DCH[d]);
    string revZstr = Zstr;
    reverse(revZstr.begin(), revZstr.end());
    string Tstr = Zstr + Kstr + revZstr;

    // Assemble final palindrome: base leftHalf + (if odd base, insert T before center and mirror) + rightHalf
    string result;
    if (!base.odd) {
        result.reserve(leftHalf.size() + Tstr.size() + rightHalf.size());
        result += leftHalf;
        result += Tstr;
        result += rightHalf;
    } else {
        // base is left + center + right; insert T in the middle around center to keep palindrome:
        // S = left + T + center + reverse(T) + right
        // But to avoid changing anchor effects, we want T to be palindromic loop starting/ending at anchor before center.
        // Our T is palindrome mapping anchor->anchor, so this is fine.
        string revT = Tstr;
        reverse(revT.begin(), revT.end());
        result.reserve(leftHalf.size() + Tstr.size() + 1 + revT.size() + rightHalf.size());
        result += leftHalf;
        result += Tstr;
        result.push_back(DCH[base.center]);
        result += revT;
        result += rightHalf;
    }

    // Verify by simulation; ensure not exceeding 1e6
    if ((int)result.size() > 1000000) {
        // If too long, fallback to just base (might not cover all cells though). Try base only; if covers all, use it else print -1.
        result = S0;
    }

    // Simulate result
    vector<char> visited(N, 0);
    int cur = S;
    visited[cur] = 1;
    for (char ch : result) {
        int d;
        if (ch == 'U') d = 0;
        else if (ch == 'D') d = 1;
        else if (ch == 'L') d = 2;
        else d = 3;
        cur = trans[cur][d];
        visited[cur] = 1;
    }
    bool allVisited = true;
    for (int i = 0; i < N; ++i) if (!visited[i]) { allVisited = false; break; }
    if (cur != E || !allVisited) {
        // As a fallback, if base alone works, use it; else print -1
        string fallback = S0;
        fill(visited.begin(), visited.end(), 0);
        cur = S;
        visited[cur] = 1;
        for (char ch : fallback) {
            int d;
            if (ch == 'U') d = 0;
            else if (ch == 'D') d = 1;
            else if (ch == 'L') d = 2;
            else d = 3;
            cur = trans[cur][d];
            visited[cur] = 1;
        }
        allVisited = true;
        for (int i = 0; i < N; ++i) if (!visited[i]) { allVisited = false; break; }
        if (cur == E && allVisited) {
            cout << fallback << "\n";
        } else {
            // Try a larger central exploration using simple snake over bounding box as last resort
            // Construct a simple big palindrome centered at anchor to try cover more cells
            // Build a naive sweep Z3: perform long DFS closed from anchor again (already did).
            // If still fails, print -1.
            if (result.size() <= 1000000 && cur == E) {
                cout << result << "\n";
            } else {
                cout << -1 << "\n";
            }
        }
        return 0;
    }

    cout << result << "\n";
    return 0;
}