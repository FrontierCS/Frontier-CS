#include <bits/stdc++.h>
using namespace std;

int n;
vector<vector<int>> C;

bool build_path(const vector<int>& verts, int start, int color, vector<int>& path) {
    int m = verts.size();
    vector<bool> vis_local(n+1, false);
    // map vertex to its index in verts? Not needed.
    // We'll use a list of available vertices.
    // Since we need to frequently find the smallest neighbor of current vertex among unvisited,
    // we can simply scan the verts list each time.
    path.clear();
    path.push_back(start);
    vis_local[start] = true;
    int cur = start;
    for (int step = 1; step < m; ++step) {
        int nxt = -1;
        // find smallest unvisited vertex in verts such that C[cur][v] == color
        for (int v : verts) {
            if (!vis_local[v] && C[cur][v] == color) {
                if (nxt == -1 || v < nxt) {
                    nxt = v;
                }
            }
        }
        if (nxt == -1) return false;
        path.push_back(nxt);
        vis_local[nxt] = true;
        cur = nxt;
    }
    return true;
}

void solve() {
    cin >> n;
    C.assign(n+1, vector<int>(n+1));
    vector<vector<int>> adj0(n+1), adj1(n+1);
    for (int i = 1; i <= n; ++i) {
        string s;
        cin >> s;
        for (int j = 1; j <= n; ++j) {
            C[i][j] = s[j-1] - '0';
            if (C[i][j] == 0) adj0[i].push_back(j);
            else adj1[i].push_back(j);
        }
    }
    // sort adjacency lists
    for (int i = 1; i <= n; ++i) {
        sort(adj0[i].begin(), adj0[i].end());
        sort(adj1[i].begin(), adj1[i].end());
    }

    // try each starting vertex
    for (int start = 1; start <= n; ++start) {
        // try both first colors
        for (int first_color = 0; first_color <= 1; ++first_color) {
            vector<bool> visited(n+1, false);
            vector<int> S;
            S.push_back(start);
            visited[start] = true;
            int x = start; // current end of S
            while (true) {
                // try to switch at x
                int b = 1 - first_color;
                // collect unvisited vertices as Tlist
                vector<int> Tlist;
                for (int v = 1; v <= n; ++v) if (!visited[v]) Tlist.push_back(v);
                if (!Tlist.empty()) {
                    // try each candidate y in increasing order (from adjacency list of x with color b)
                    const vector<int>& cand = (b == 0 ? adj0[x] : adj1[x]);
                    for (int y : cand) {
                        if (visited[y]) continue;
                        vector<int> pathT;
                        if (build_path(Tlist, y, b, pathT)) {
                            int t = pathT.back();
                            if (C[t][start] == b) {
                                // success
                                vector<int> ans = S;
                                ans.insert(ans.end(), pathT.begin(), pathT.end());
                                for (int i = 0; i < n; ++i) {
                                    cout << ans[i] << (i==n-1 ? '\n' : ' ');
                                }
                                return;
                            }
                        }
                    }
                }

                // extend S with first_color
                const vector<int>& ext = (first_color == 0 ? adj0[x] : adj1[x]);
                int nxt = -1;
                for (int u : ext) {
                    if (!visited[u]) {
                        nxt = u;
                        break;
                    }
                }
                if (nxt == -1) break;
                visited[nxt] = true;
                S.push_back(nxt);
                x = nxt;
            }
            // check if S is full
            if (S.size() == n) {
                int t = S.back();
                if (C[t][start] == first_color || C[t][start] == 1-first_color) {
                    for (int i = 0; i < n; ++i) {
                        cout << S[i] << (i==n-1 ? '\n' : ' ');
                    }
                    return;
                }
            }
        }
    }
    cout << "-1\n";
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int tests = 1;
    // read until EOF
    while (cin >> n) {
        solve();
    }
    return 0;
}