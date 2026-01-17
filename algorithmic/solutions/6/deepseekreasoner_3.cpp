#include <bits/stdc++.h>
using namespace std;

vector<vector<int>> create_map(int N, int M,
                               vector<int> A, vector<int> B) {
    // adjacency matrix
    vector<vector<bool>> adj(N+1, vector<bool>(N+1, false));
    vector<vector<int>> g(N+1);
    for (int i = 0; i < M; ++i) {
        int a = A[i], b = B[i];
        adj[a][b] = adj[b][a] = true;
        g[a].push_back(b);
        g[b].push_back(a);
    }

    // ---------- spanning tree (BFS from 1) ----------
    vector<bool> vis(N+1, false);
    vector<vector<int>> tree(N+1);
    vector<vector<bool>> is_tree_edge(N+1, vector<bool>(N+1, false));
    queue<int> q;
    q.push(1);
    vis[1] = true;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : g[u]) {
            if (!vis[v]) {
                vis[v] = true;
                tree[u].push_back(v);
                tree[v].push_back(u);
                if (u < v) is_tree_edge[u][v] = true;
                else       is_tree_edge[v][u] = true;
                q.push(v);
            }
        }
    }

    // ---------- DFS traversal of the tree (start and end at 1) ----------
    vector<int> seq;
    function<void(int,int)> dfs = [&](int u, int p) {
        seq.push_back(u);
        for (int v : tree[u]) {
            if (v != p) {
                dfs(v, u);
                seq.push_back(u);
            }
        }
    };
    dfs(1, 0);
    int L = seq.size();   // L = 2*N - 1

    // ---------- initial two rows ----------
    vector<vector<int>> grid;
    vector<vector<bool>> fixed;   // which cells are not allowed to be changed

    // row 0: the DFS sequence
    grid.push_back(seq);
    fixed.push_back(vector<bool>(L, true));

    // row 1: first element 1, then seq[1..]
    vector<int> row1(L);
    row1[0] = 1;
    for (int i = 1; i < L; ++i) row1[i] = seq[i];
    grid.push_back(row1);
    fixed.push_back(vector<bool>(L, true));

    // ---------- collect non‑tree edges ----------
    vector<pair<int,int>> non_tree;
    for (int i = 0; i < M; ++i) {
        int a = A[i], b = B[i];
        if (a > b) swap(a, b);
        if (!is_tree_edge[a][b])
            non_tree.emplace_back(A[i], B[i]);
    }

    // ---------- place each non‑tree edge ----------
    for (auto [u, v] : non_tree) {
        bool placed = false;
        while (!placed) {
            int rows = grid.size();
            vector<int>& cur_row = grid.back();
            vector<bool>& cur_fixed = fixed.back();
            vector<int>& prev_row = grid[rows-2];   // row above

            // try to find two consecutive free cells
            for (int i = 0; i < L-1; ++i) {
                if (cur_fixed[i] || cur_fixed[i+1]) continue;
                if (!adj[prev_row[i]][u]) continue;
                if (!adj[prev_row[i+1]][v]) continue;
                if (i > 0 && !adj[cur_row[i-1]][u]) continue;
                if (i+1 < L-1 && !adj[v][cur_row[i+2]]) continue;
                // place the edge here
                cur_row[i] = u;
                cur_row[i+1] = v;
                cur_fixed[i] = cur_fixed[i+1] = true;
                placed = true;
                break;
            }
            if (!placed) {
                // add a new row (copy of the last row, all cells changeable)
                grid.push_back(grid.back());
                fixed.push_back(vector<bool>(L, false));
            }
        }
    }

    // ---------- make the grid square ----------
    int R = grid.size();
    int C = L;
    int K = max(R, C);

    // extend rows by duplicating the last row
    while ((int)grid.size() < K) {
        grid.push_back(grid.back());
    }

    // extend columns by duplicating the last column of each row
    for (int i = 0; i < K; ++i) {
        while ((int)grid[i].size() < K) {
            grid[i].push_back(grid[i].back());
        }
    }

    return grid;
}