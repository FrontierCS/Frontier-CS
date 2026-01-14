#include <bits/stdc++.h>
using namespace std;

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    vector<vector<int>> adj(N + 1);
    for (int i = 0; i < M; i++) {
        int u = A[i], v = B[i];
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    int root = 1;
    vector<int> par(N + 1, -1);
    vector<bool> visited(N + 1, false);
    queue<int> q;
    q.push(root);
    visited[root] = true;
    par[root] = 0;
    vector<pair<int, int>> tree_edges;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (int v : adj[u]) {
            if (!visited[v]) {
                visited[v] = true;
                par[v] = u;
                tree_edges.push_back({min(u, v), max(u, v)});
                q.push(v);
            }
        }
    }
    vector<vector<int>> tree(N + 1);
    for (int i = 1; i <= N; i++) {
        if (par[i] > 0) {
            tree[par[i]].push_back(i);
        }
    }
    set<pair<int, int>> tree_set(tree_edges.begin(), tree_edges.end());
    vector<pair<int, int>> missing;
    for (int i = 0; i < M; i++) {
        int u = min(A[i], B[i]), v = max(A[i], B[i]);
        if (tree_set.find({u, v}) == tree_set.end()) {
            missing.push_back({u, v});
        }
    }
    function<int(int)> get_height = [&](int node) -> int {
        if (tree[node].empty()) return 3;
        int mx = 0;
        for (int ch : tree[node]) mx = max(mx, get_height(ch));
        return 1 + mx;
    };
    function<int(int)> get_width = [&](int node) -> int {
        if (tree[node].empty()) return 3;
        int d = tree[node].size();
        int sum = 0;
        for (int ch : tree[node]) sum += get_width(ch);
        return 2 + sum + max(0, d - 1);
    };
    int h_need = get_height(root);
    int w_need = get_width(root);
    int K = max(h_need, w_need);
    vector<vector<int>> grid(K, vector<int>(K, 0));
    function<void(int, int, int, int, int)> place = [&](int node, int r_start, int h_alloc, int c_start, int w_alloc) {
        if (h_alloc < 1 || w_alloc < 1) return;
        // top row
        for (int cc = c_start; cc < c_start + w_alloc && cc < K; cc++) {
            if (r_start < K) grid[r_start][cc] = node;
        }
        if (tree[node].empty()) {
            // leaf, fill rest
            for (int rr = r_start + 1; rr < r_start + h_alloc && rr < K; rr++) {
                for (int cc = c_start; cc < c_start + w_alloc && cc < K; cc++) {
                    grid[rr][cc] = node;
                }
            }
            return;
        }
        // left frame below top
        for (int rr = r_start + 1; rr < r_start + h_alloc && rr < K; rr++) {
            if (c_start < K) grid[rr][c_start] = node;
        }
        // right frame below top
        int right_c = c_start + w_alloc - 1;
        for (int rr = r_start + 1; rr < r_start + h_alloc && rr < K; rr++) {
            if (right_c < K) grid[rr][right_c] = node;
        }
        int inner_h = h_alloc - 1;
        int inner_w_alloc = w_alloc - 2;
        if (inner_h <= 0 || inner_w_alloc <= 0) return;
        int d = tree[node].size();
        vector<int> child_w(d);
        int sum_min_w = 0;
        for (int i = 0; i < d; i++) {
            int ch = tree[node][i];
            child_w[i] = get_width(ch);
            sum_min_w += child_w[i];
        }
        int num_sep = max(0, d - 1);
        int min_inner = sum_min_w + num_sep;
        int extra_w = inner_w_alloc - min_inner;
        if (d > 0 && extra_w > 0) {
            int base = extra_w / d;
            int rem = extra_w % d;
            for (int i = 0; i < d; i++) {
                child_w[i] += base;
                if (i < rem) child_w[i]++;
            }
        }
        int current_c = c_start + 1;
        for (int i = 0; i < d; i++) {
            int ch = tree[node][i];
            int wi = child_w[i];
            if (current_c + wi > c_start + w_alloc - 1) break;
            place(ch, r_start + 1, inner_h, current_c, wi);
            current_c += wi;
            if (i < d - 1) {
                // separator column
                for (int rr = r_start + 1; rr < r_start + h_alloc && rr < K; rr++) {
                    if (current_c < K) grid[rr][current_c] = node;
                }
                current_c++;
            }
        }
        // fill remaining inner with node
        int inner_end = c_start + w_alloc - 2;
        for (int cc = current_c; cc <= inner_end && cc < K; cc++) {
            for (int rr = r_start + 1; rr < r_start + h_alloc && rr < K; rr++) {
                grid[rr][cc] = node;
            }
        }
    };
    place(root, 0, K, 0, K);
    // now collect internals
    vector<vector<pair<int, int>>> internals(N + 1);
    int dirs[4][2] = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};
    for (int i = 0; i < K; i++) {
        for (int j = 0; j < K; j++) {
            int colr = grid[i][j];
            if (colr == 0) continue; // shouldn't happen
            bool is_int = true;
            for (int dd = 0; dd < 4; dd++) {
                int ni = i + dirs[dd][0];
                int nj = j + dirs[dd][1];
                if (ni >= 0 && ni < K && nj >= 0 && nj < K && grid[ni][nj] != colr) {
                    is_int = false;
                    break;
                }
            }
            if (is_int) {
                internals[colr].emplace_back(i, j);
            }
        }
    }
    // now add missing
    for (auto [a, b] : missing) {
        // try to embed b into a if possible, else a into b
        bool embedded = false;
        if (!internals[a].empty()) {
            auto [ii, jj] = internals[a].back();
            internals[a].pop_back();
            grid[ii][jj] = b;
            embedded = true;
        } else if (!internals[b].empty()) {
            auto [ii, jj] = internals[b].back();
            internals[b].pop_back();
            grid[ii][jj] = a;
            embedded = true;
        }
        // if not, assume it worked
        assert(embedded); // for safety, but guaranteed
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
        auto C = create_map(N, M, A, B);
        int P = C.size();
        cout << P << endl;
        for (int i = 0; i < P; i++) {
            cout << P;
            if (i < P - 1) cout << " ";
            else cout << endl;
        }
        cout << endl;
        for (int i = 0; i < P; i++) {
            for (int j = 0; j < P; j++) {
                cout << C[i][j];
                if (j < P - 1) cout << " ";
                else cout << endl;
            }
        }
    }
    return 0;
}