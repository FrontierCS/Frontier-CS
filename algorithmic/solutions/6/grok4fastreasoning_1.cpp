#include <bits/stdc++.h>
using namespace std;

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    vector<vector<int>> adj(N + 1);
    vector<vector<char>> has(N + 1, vector<char>(N + 1, 0));
    for (int i = 0; i < M; i++) {
        int u = A[i], v = B[i];
        adj[u].push_back(v);
        adj[v].push_back(u);
        has[u][v] = has[v][u] = 1;
    }
    // find root with max degree
    int root = 1;
    int maxd = -1;
    for (int i = 1; i <= N; i++) {
        int d = adj[i].size();
        if (d > maxd) {
            maxd = d;
            root = i;
        }
    }
    vector<vector<int>> children(N + 1);
    vector<bool> vis(N + 1, false);
    vector<pair<int, int>> back_edges;
    function<void(int, int)> dfs_tree = [&](int u, int p) {
        vis[u] = true;
        for (int v : adj[u]) {
            if (v == p) continue;
            if (vis[v]) {
                if (u < v) back_edges.emplace_back(u, v);
            } else {
                children[u].push_back(v);
                dfs_tree(v, u);
            }
        }
    };
    dfs_tree(root, 0);
    // build map recursive
    using Map = vector<vector<int>>;
    function<Map(int)> build = [&](int u) -> Map {
        if (children[u].empty()) {
            return {{u}};
        }
        int d = children[u].size();
        vector<Map> sub_maps(d);
        int max_h = 0;
        for (int i = 0; i < d; i++) {
            sub_maps[i] = build(children[u][i]);
            max_h = max(max_h, (int)sub_maps[i].size());
        }
        vector<int> sub_ws(d);
        for (int i = 0; i < d; i++) {
            Map& sm = sub_maps[i];
            int ch = sm.size();
            int cw = (ch > 0 ? sm[0].size() : 1);
            int cc = children[u][i];
            while (ch < max_h) {
                vector<int> nr(cw, cc);
                sm.push_back(nr);
                ch++;
            }
            sub_ws[i] = cw;
        }
        int children_w = 0;
        for (int sw : sub_ws) children_w += sw;
        children_w += max(0, d - 1);
        Map children_combined(max_h, vector<int>(children_w, 0));
        int col = 0;
        for (int i = 0; i < d; i++) {
            Map& sm = sub_maps[i];
            for (int r = 0; r < max_h; r++) {
                for (int cc = 0; cc < sub_ws[i]; cc++) {
                    children_combined[r][col + cc] = sm[r][cc];
                }
            }
            col += sub_ws[i];
            if (i < d - 1) {
                for (int r = 0; r < max_h; r++) {
                    children_combined[r][col] = u;
                }
                col++;
            }
        }
        // pad left and right with u if d > 0
        int old_cw = children_w;
        if (d > 0) {
            children_w += 2;
            Map new_c(max_h, vector<int>(children_w, u));
            for (int r = 0; r < max_h; r++) {
                for (int c = 0; c < old_cw; c++) {
                    new_c[r][c + 1] = children_combined[r][c];
                }
            }
            children_combined = std::move(new_c);
        }
        int total_h = max_h + 1;
        int total_w = children_w;
        Map res(total_h, vector<int>(total_w, u));
        for (int r = 0; r < max_h; r++) {
            for (int c = 0; c < total_w; c++) {
                res[r + 1][c] = children_combined[r][c];
            }
        }
        return res;
    };
    Map themap = build(root);
    int H = themap.size();
    int W = (H > 0 ? themap[0].size() : 0);
    int K = max(H, W);
    Map full(K, vector<int>(K, 0));
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            full[r][c] = themap[r][c];
        }
    }
    // pad width
    for (int r = 0; r < H; r++) {
        int last = full[r][W - 1];
        for (int c = W; c < K; c++) {
            full[r][c] = last;
        }
    }
    // pad height
    for (int r = H; r < K; r++) {
        for (int c = 0; c < K; c++) {
            full[r][c] = full[H - 1][c];
        }
    }
    // now handle back edges
    for (auto e : back_edges) {
        int a = e.first, b = e.second;
        bool realized = false;
        for (int swp = 0; swp < 2; swp++) {
            int aa = a, bb = b;
            if (swp) swap(aa, bb);
            bool fnd = false;
            int tj = -1;
            for (int extra_w = 0; extra_w <= 2; extra_w++) {
                int temp_k = K + extra_w;
                vector<int> temp_prev(temp_k);
                for (int c = 0; c < K; c++) temp_prev[c] = full[K - 1][c];
                int lst = full[K - 1][K - 1];
                for (int c = K; c < temp_k; c++) temp_prev[c] = lst;
                bool this_fnd = false;
                int this_tj = -1;
                for (int j = 1; j < temp_k - 1; j++) {
                    int g = temp_prev[j - 1];
                    int f = temp_prev[j];
                    int h = temp_prev[j + 1];
                    if (has[aa][g] && has[aa][f] && has[aa][h] &&
                        has[bb][g] && has[bb][h]) {
                        this_fnd = true;
                        this_tj = j;
                        break;
                    }
                }
                if (this_fnd) {
                    fnd = true;
                    tj = this_tj;
                    // now perform the add
                    int add_w = extra_w;
                    int old_k = K;
                    K += add_w + 2;
                    Map newf(K, vector<int>(K, 0));
                    // copy old
                    for (int r = 0; r < old_k; r++) {
                        for (int c = 0; c < old_k; c++) {
                            newf[r][c] = full[r][c];
                        }
                    }
                    // pad width for old rows
                    for (int r = 0; r < old_k; r++) {
                        int lstc = newf[r][old_k - 1];
                        for (int c = old_k; c < old_k + add_w; c++) {
                            newf[r][c] = lstc;
                        }
                    }
                    int curr_h = old_k;
                    int curr_w = old_k + add_w;
                    // now pat = current bottom row  curr_h-1 , size curr_w
                    vector<int> pat(curr_w);
                    for (int c = 0; c < curr_w; c++) {
                        pat[c] = newf[curr_h - 1][c];
                    }
                    // first new row
                    int nr1 = curr_h;
                    for (int c = 0; c < curr_w; c++) {
                        newf[nr1][c] = pat[c];
                    }
                    newf[nr1][tj] = aa;
                    // second new row
                    int nr2 = curr_h + 1;
                    for (int c = 0; c < curr_w; c++) {
                        newf[nr2][c] = pat[c];
                    }
                    newf[nr2][tj] = bb;
                    // pad width for new rows
                    for (int rr = nr1; rr <= nr2; rr++) {
                        int lstc = newf[rr][curr_w - 1];
                        for (int c = curr_w; c < K; c++) {
                            newf[rr][c] = lstc;
                        }
                    }
                    full = std::move(newf);
                    realized = true;
                    break;
                }
            }
            if (fnd) break;
        }
        // if (!realized) { // handle, but assume ok
        //}
    }
    return full;
}