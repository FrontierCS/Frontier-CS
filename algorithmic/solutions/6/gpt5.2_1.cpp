#include <bits/stdc++.h>
using namespace std;

static constexpr int K_MAX = 240;

// Construction parameters (tuned for robustness, not minimality)
static constexpr int MIN_SIDE = 15;   // minimum side length of each country's base rectangle
static constexpr int MARGIN   = 2;    // margin of parent-color cells around each child rectangle
static constexpr int SPACING  = 2;    // spacing of parent-color cells between child rectangles

struct NodeInfo {
    int w = MIN_SIDE, h = MIN_SIDE;
    int cols = 0, rows = 0;
    int maxw = 0, maxh = 0;
};

struct Rect {
    int r0 = 0, c0 = 0, h = 0, w = 0;
};

static inline int isqrt_ceil(int x) {
    int r = (int)std::sqrt((double)x);
    while (r * r < x) ++r;
    return r;
}

static inline bool inside(int r, int c, int K) {
    return (0 <= r && r < K && 0 <= c && c < K);
}

static inline bool is_interior_same(const vector<vector<int>> &grid, int r, int c, int color) {
    return grid[r][c] == color &&
           grid[r-1][c] == color &&
           grid[r+1][c] == color &&
           grid[r][c-1] == color &&
           grid[r][c+1] == color;
}

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    if (N <= 0) return {};

    vector<vector<int>> adjList(N + 1);
    vector<vector<char>> adjMat(N + 1, vector<char>(N + 1, 0));
    vector<pair<int,int>> edges;
    edges.reserve(M);

    for (int i = 0; i < M; i++) {
        int u = A[i], v = B[i];
        edges.push_back({u, v});
        adjList[u].push_back(v);
        adjList[v].push_back(u);
        adjMat[u][v] = adjMat[v][u] = 1;
    }

    int root = 1;

    // BFS spanning tree
    vector<int> parent(N + 1, -1);
    parent[root] = 0;
    queue<int> q;
    q.push(root);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : adjList[u]) {
            if (parent[v] == -1) {
                parent[v] = u;
                q.push(v);
            }
        }
    }

    // Existence guarantee implies connected; if not, we still try a best-effort fallback
    // by forcing unreachable nodes as direct children of root only if edge exists; otherwise leave.
    for (int v = 1; v <= N; v++) {
        if (parent[v] == -1) {
            // Find any already-reached node that is adjacent to v
            int attach = -1;
            for (int u = 1; u <= N; u++) {
                if (parent[u] != -1 && adjMat[u][v]) { attach = u; break; }
            }
            if (attach == -1) {
                // Should not happen for valid inputs; attach to root anyway to continue.
                attach = root;
            }
            parent[v] = attach;
        }
    }

    vector<vector<int>> children(N + 1);
    for (int v = 1; v <= N; v++) children[v].clear();
    for (int v = 1; v <= N; v++) {
        if (v == root) continue;
        children[parent[v]].push_back(v);
    }

    // Compute node sizing bottom-up
    vector<NodeInfo> info(N + 1);

    function<void(int)> dfs_size = [&](int u) {
        for (int c : children[u]) dfs_size(c);
        int k = (int)children[u].size();
        if (k == 0) {
            info[u].w = info[u].h = MIN_SIDE;
            info[u].cols = info[u].rows = 0;
            info[u].maxw = info[u].maxh = 0;
            return;
        }
        int maxw = 0, maxh = 0;
        for (int c : children[u]) {
            maxw = max(maxw, info[c].w);
            maxh = max(maxh, info[c].h);
        }
        int cols = isqrt_ceil(k);
        int rows = (k + cols - 1) / cols;

        int w = max(MIN_SIDE, 2 * MARGIN + cols * maxw + (cols - 1) * SPACING);
        int h = max(MIN_SIDE, 2 * MARGIN + rows * maxh + (rows - 1) * SPACING);

        info[u].w = w;
        info[u].h = h;
        info[u].cols = cols;
        info[u].rows = rows;
        info[u].maxw = maxw;
        info[u].maxh = maxh;
    };

    dfs_size(root);

    int K = max({6 * N, info[root].w, info[root].h});
    if (K > K_MAX) K = K_MAX;
    if (K < 3) K = 3;

    // Place rectangles top-down
    vector<Rect> rect(N + 1);
    rect[root] = {0, 0, K, K};

    function<void(int)> dfs_place = [&](int u) {
        int k = (int)children[u].size();
        if (k == 0) return;

        int cols = max(1, info[u].cols);
        int maxw = info[u].maxw;
        int maxh = info[u].maxh;

        for (int idx = 0; idx < k; idx++) {
            int c = children[u][idx];
            int rr = idx / cols;
            int cc = idx % cols;

            Rect rc;
            rc.r0 = rect[u].r0 + MARGIN + rr * (maxh + SPACING);
            rc.c0 = rect[u].c0 + MARGIN + cc * (maxw + SPACING);
            rc.h = info[c].h;
            rc.w = info[c].w;

            // Ensure within bounds of parent rect (should hold due to sizing); if not, clamp inward.
            int pr1 = rect[u].r0 + rect[u].h - MARGIN;
            int pc1 = rect[u].c0 + rect[u].w - MARGIN;
            if (rc.r0 + rc.h > pr1) rc.r0 = max(rect[u].r0 + MARGIN, pr1 - rc.h);
            if (rc.c0 + rc.w > pc1) rc.c0 = max(rect[u].c0 + MARGIN, pc1 - rc.w);

            rect[c] = rc;
            dfs_place(c);
        }
    };

    dfs_place(root);

    // Paint base map: nested rectangles form a tree adjacency
    vector<vector<int>> grid(K, vector<int>(K, root));

    function<void(int)> dfs_paint = [&](int u) {
        if (u != root) {
            const Rect &R = rect[u];
            for (int r = R.r0; r < R.r0 + R.h; r++) {
                for (int c = R.c0; c < R.c0 + R.w; c++) {
                    grid[r][c] = u;
                }
            }
        }
        for (int c : children[u]) dfs_paint(c);
    };

    dfs_paint(root);

    // Build tree edge lookup
    vector<vector<char>> inTree(N + 1, vector<char>(N + 1, 0));
    for (int v = 1; v <= N; v++) {
        if (v == root) continue;
        int p = parent[v];
        inTree[v][p] = inTree[p][v] = 1;
    }

    // Precompute candidate interior cells for each color
    vector<vector<pair<int,int>>> candidates(N + 1);
    candidates.assign(N + 1, {});
    for (int r = 1; r + 1 < K; r++) {
        for (int c = 1; c + 1 < K; c++) {
            int col = grid[r][c];
            if (col >= 1 && col <= N && is_interior_same(grid, r, c, col)) {
                candidates[col].push_back({r, c});
            }
        }
    }

    vector<vector<unsigned char>> blocked(K, vector<unsigned char>(K, 0));
    vector<int> usedCnt(N + 1, 0);

    auto block_cell = [&](int r, int c) {
        if (inside(r, c, K)) blocked[r][c] = 1;
    };

    auto get_spot = [&](int container) -> pair<int,int> {
        auto &vec = candidates[container];
        while (!vec.empty()) {
            auto [r, c] = vec.back();
            vec.pop_back();
            if (blocked[r][c]) continue;
            if (r <= 0 || r + 1 >= K || c <= 0 || c + 1 >= K) continue;
            if (!is_interior_same(grid, r, c, container)) continue;
            return {r, c};
        }
        return {-1, -1};
    };

    auto place_island = [&](int container, int other) -> bool {
        auto [r, c] = get_spot(container);
        if (r < 0) return false;

        // Place island
        grid[r][c] = other;

        // Block island cell and its direct neighbors to prevent future recolors adjacent to it
        block_cell(r, c);
        block_cell(r-1, c);
        block_cell(r+1, c);
        block_cell(r, c-1);
        block_cell(r, c+1);

        usedCnt[container]++;
        return true;
    };

    auto brute_place_island = [&](int container, int other) -> bool {
        for (int r = 1; r + 1 < K; r++) {
            for (int c = 1; c + 1 < K; c++) {
                if (blocked[r][c]) continue;
                if (is_interior_same(grid, r, c, container)) {
                    grid[r][c] = other;
                    block_cell(r, c);
                    block_cell(r-1, c);
                    block_cell(r+1, c);
                    block_cell(r, c-1);
                    block_cell(r, c+1);
                    usedCnt[container]++;
                    return true;
                }
            }
        }
        return false;
    };

    // Add islands for all non-tree edges
    for (auto [u, v] : edges) {
        if (inTree[u][v]) continue;

        // Choose direction based on an estimate of remaining capacity
        long long estU = (long long)candidates[u].size() - 5LL * usedCnt[u];
        long long estV = (long long)candidates[v].size() - 5LL * usedCnt[v];

        int container = u, other = v;
        if (estV > estU) { container = v; other = u; }

        bool ok = place_island(container, other);
        if (!ok) ok = place_island(other, container);
        if (!ok) ok = brute_place_island(container, other);
        if (!ok) ok = brute_place_island(other, container);

        // If still not possible, inputs were invalid; leave as-is.
    }

    return grid;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    for (int tc = 0; tc < T; tc++) {
        int N, M;
        cin >> N >> M;
        vector<int> A(M), B(M);
        for (int i = 0; i < M; i++) {
            cin >> A[i] >> B[i];
        }

        auto C = create_map(N, M, A, B);
        int K = (int)C.size();

        cout << K << "\n";
        for (int i = 0; i < K; i++) {
            if (i) cout << ' ';
            cout << K;
        }
        cout << "\n";
        for (int r = 0; r < K; r++) {
            for (int c = 0; c < K; c++) {
                if (c) cout << ' ';
                cout << C[r][c];
            }
            cout << "\n";
        }
        if (tc + 1 < T) cout << "\n";
    }
    return 0;
}