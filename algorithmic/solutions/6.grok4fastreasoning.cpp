#include <bits/stdc++.h>
using namespace std;

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    vector<vector<int>> adj(N + 1);
    for (int i = 0; i < M; i++) {
        int a = A[i], b = B[i];
        adj[a].push_back(b);
        adj[b].push_back(a);
    }
    // Choose root with max degree
    int root = 1;
    int max_deg = 0;
    for (int i = 1; i <= N; i++) {
        if ((int)adj[i].size() > max_deg) {
            max_deg = adj[i].size();
            root = i;
        }
    }
    // Build spanning tree from root
    vector<vector<int>> tree_children(N + 1);
    vector<int> par(N + 1, -1);
    vector<bool> visited(N + 1, false);
    queue<int> q;
    q.push(root);
    visited[root] = true;
    par[root] = 0;
    set<pair<int, int>> tree_edges;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (int v : adj[u]) {
            if (!visited[v]) {
                visited[v] = true;
                par[v] = u;
                tree_children[u].push_back(v);
                q.push(v);
                int aa = min(u, v), bb = max(u, v);
                tree_edges.insert({aa, bb});
            }
        }
    }
    // Precompute widths and heights
    vector<int> widths(N + 1), heights(N + 1);
    function<void(int)> precompute = [&](int u) {
        int d = tree_children[u].size();
        int inner_w = 0;
        int max_ch_h = 0;
        for (int v : tree_children[u]) {
            precompute(v);
            inner_w += widths[v];
            max_ch_h = max(max_ch_h, heights[v]);
            if (d > 1) inner_w += 1;  // gaps d-1 total
        }
        if (d > 1) inner_w -= (d - 1);  // wait, no, add gaps separately
        inner_w += max(0, d - 1);
        widths[u] = inner_w + 3;  // buffers
        heights[u] = 1 + max_ch_h + 1;  // bar + max child + bottom buffer
    };
    precompute(root);
    // Now heights and widths ready
    int need_h = heights[root];
    int need_w = widths[root];
    int KK = max(need_h, need_w);
    vector<vector<int>> grid(KK, vector<int>(KK, 0));
    // color_cells
    vector<vector<pair<int, int>>> color_cells(N + 1);
    // Placement function
    function<int(int, int, int, int, int)> place_subtree = [&](int u, int p, int g_row, int l_col, int w) -> int {
        int d = tree_children[u].size();
        int inner_start = l_col + 1;
        int cur_c = inner_start;
        int max_ch_h = 0;
        if (d == 0) {
            // leaf
            grid[g_row][inner_start] = u;
            color_cells[u].push_back({g_row, inner_start});
        } else {
            for (int i = 0; i < d; i++) {
                int v = tree_children[i];
                // place bar
                grid[g_row][cur_c] = u;
                color_cells[u].push_back({g_row, cur_c});
                // place child
                int v_h = place_subtree(v, u, g_row + 1, cur_c, widths[v]);
                max_ch_h = max(max_ch_h, v_h);
                cur_c += widths[v];
                if (i < d - 1) cur_c += 1;
            }
        }
        int ret_h = 1 + max_ch_h + 1;
        return ret_h;
    };
    place_subtree(root, -1, 0, 0, widths[root]);
    // Now extra edges
    vector<pair<int, int>> orig;
    for (int i = 0; i < M; i++) {
        int a = A[i], b = B[i];
        int aa = min(a, b), bb = max(a, b);
        orig.push_back({aa, bb});
    }
    auto is_adj = [&](int aa, int bb) {
        for (int vv : adj[aa]) if (vv == bb) return true;
        return false;
    };
    auto try_attach = [&](int base, int att) -> bool {
        auto& cells = color_cells[base];
        for (auto [r, c] : cells) {
            int dirs[4][2] = {{0,1},{0,-1},{1,0},{-1,0}};
            for (int di = 0; di < 4; di++) {
                int dr = dirs[di][0], dc = dirs[di][1];
                int nr = r + dr, nc = c + dc;
                if (nr < 0 || nr >= KK || nc < 0 || nc >= KK || grid[nr][nc] != 0) continue;
                // check other 3 neighbors
                bool good = true;
                for (int ddi = 0; ddi < 4; ddi++) {
                    int ddr = dirs[ddi][0], ddc = dirs[ddi][1];
                    if (ddr == dr && ddc == dc) continue;  // the base
                    int nnr = nr + ddr, nnc = nc + ddc;
                    if (nnr < 0 || nnr >= KK || nnc < 0 || nnc >= KK) {
                        good = false;
                        break;
                    }
                    if (grid[nnr][nnc] != 0) {
                        int other = grid[nnr][nnc];
                        if (other != base && !is_adj(other, att)) {
                            good = false;
                            break;
                        }
                    }
                }
                if (good) {
                    grid[nr][nc] = att;
                    color_cells[att].push_back({nr, nc});
                    return true;
                }
            }
        }
        return false;
    };
    for (auto e : orig) {
        int a = e.first, b = e.second;
        if (tree_edges.count(e)) continue;
        try_attach(a, b) || try_attach(b, a);
    }
    // Now fill function
    function<void(int, int, int, int, int)> fill_tree = [&](int u, int g_row, int l_col, int w, int hh) {
        // recurse children
        int d = tree_children[u].size();
        int inner_start = l_col + 1;
        int cur_c = inner_start;
        for (int i = 0; i < d; i++) {
            int v = tree_children[u][i];
            int v_w = widths[v];
            int v_hh = heights[v];
            fill_tree(v, g_row + 1, cur_c, v_w, v_hh);
            cur_c += v_w;
            if (i < d - 1) cur_c += 1;
        }
        // fill empty in box with u
        int min_rr = g_row;
        int max_rr = g_row + hh - 1;
        int min_cc = l_col;
        int max_cc = l_col + w - 1;
        for (int rr = min_rr; rr <= max_rr; rr++) {
            for (int cc = min_cc; cc <= max_cc; cc++) {
                if (grid[rr][cc] == 0) {
                    grid[rr][cc] = u;
                }
            }
        }
    };
    fill_tree(root, 0, 0, widths[root], heights[root]);
    // Pad if necessary
    if (need_w < KK) {
        // pad right columns
        for (int rr = 0; rr < KK; rr++) {
            for (int cc = widths[root]; cc < KK; cc++) {
                grid[rr][cc] = root;
            }
        }
    }
    if (need_h < KK) {
        // pad bottom rows
        for (int rr = heights[root]; rr < KK; rr++) {
            for (int cc = 0; cc < KK; cc++) {
                grid[rr][cc] = root;
            }
        }
    }
    return grid;
}

int main() {
    int T;
    cin >> T;
    for (int t = 0; t < T; t++) {
        int N, M;
        cin >> N >> M;
        vector<int> A(M), B(M);
        for (int i = 0; i < M; i++) {
            cin >> A[i] >> B[i];
        }
        auto map_grid = create_map(N, M, A, B);
        int P = map_grid.size();
        cout << P << endl;
        for (int i = 0; i < P; i++) {
            cout << P;
            if (i < P - 1) cout << " ";
            else cout << endl;
        }
        cout << endl;
        for (int i = 0; i < P; i++) {
            for (int j = 0; j < P; j++) {
                cout << map_grid[i][j];
                if (j < P - 1) cout << " ";
                else cout << endl;
            }
        }
    }
    return 0;
}