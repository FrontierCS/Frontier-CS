#include <bits/stdc++.h>
using namespace std;

struct Item {
    int id; // >=1 child vertex, 0 gadget
    int w, h; // padded width/height
};

struct Placed {
    int id;
    int x, y; // top-left within inner area (rows, cols)
    int w, h; // padded width/height
};

struct NodeInfo {
    int W = 3, H = 3;       // total rect size (width, height)
    int innerW = 1, innerH = 1; // packing area size
    vector<Placed> layout;

    bool hasGadget = false;
    int gW = 0, gH = 0;     // gadget rectangle size (un-padded), inside u
    int gCols = 0, gRows = 0;

    int gTop = -1, gLeft = -1; // absolute coordinates assigned during placement
};

static pair<int, vector<Placed>> packShelf(const vector<Item>& itemsSorted, int W_in) {
    int curRow = 0, curCol = 0, rowH = 0;
    vector<Placed> placed;
    placed.reserve(itemsSorted.size());

    for (auto &it : itemsSorted) {
        if (it.w > W_in) return {INT_MAX / 4, {}};
        if (curCol + it.w > W_in) {
            curRow += rowH;
            curCol = 0;
            rowH = 0;
        }
        placed.push_back(Placed{it.id, curRow, curCol, it.w, it.h});
        curCol += it.w;
        rowH = max(rowH, it.h);
    }
    int H_in = curRow + rowH;
    return {H_in, placed};
}

static int isqrt_ceil(int x) {
    int r = (int)floor(sqrt((double)x));
    while (r * r < x) r++;
    return r;
}

static vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    if (N == 1) return vector<vector<int>>(1, vector<int>(1, 1));

    vector<vector<int>> adj(N + 1);
    vector<vector<char>> hasEdge(N + 1, vector<char>(N + 1, 0));
    vector<int> deg(N + 1, 0);

    for (int i = 0; i < M; i++) {
        int u = A[i], v = B[i];
        adj[u].push_back(v);
        adj[v].push_back(u);
        hasEdge[u][v] = hasEdge[v][u] = 1;
        deg[u]++; deg[v]++;
    }

    int root = 1;
    for (int i = 1; i <= N; i++) {
        if (deg[i] > deg[root] || (deg[i] == deg[root] && i < root)) root = i;
    }

    vector<int> parent(N + 1, -1);
    queue<int> q;
    parent[root] = 0;
    q.push(root);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : adj[u]) {
            if (parent[v] == -1) {
                parent[v] = u;
                q.push(v);
            }
        }
    }

    // Fallback if disconnected (shouldn't happen when map exists)
    for (int i = 1; i <= N; i++) {
        if (parent[i] == -1) parent[i] = root;
    }

    vector<vector<int>> children(N + 1);
    vector<vector<char>> treeEdge(N + 1, vector<char>(N + 1, 0));
    for (int v = 1; v <= N; v++) {
        if (v == root) continue;
        int p = parent[v];
        if (p < 0) p = root;
        children[p].push_back(v);
        treeEdge[p][v] = treeEdge[v][p] = 1;
    }

    // Host non-tree edges at smaller endpoint id
    vector<vector<int>> hostList(N + 1);
    for (int i = 0; i < M; i++) {
        int u = A[i], v = B[i];
        if (treeEdge[u][v]) continue;
        int host = min(u, v);
        int other = max(u, v);
        hostList[host].push_back(other);
    }

    // Postorder traversal
    vector<int> order;
    order.reserve(N);
    {
        vector<int> st;
        st.push_back(root);
        while (!st.empty()) {
            int u = st.back(); st.pop_back();
            order.push_back(u);
            for (int v : children[u]) st.push_back(v);
        }
        reverse(order.begin(), order.end());
    }

    vector<NodeInfo> info(N + 1);

    auto computeNode = [&](int u) {
        vector<Item> items;

        // Children items (padded by 1 on all sides => +2 in each dimension)
        for (int v : children[u]) {
            int cw = info[v].W;
            int ch = info[v].H;
            items.push_back(Item{v, cw + 2, ch + 2});
        }

        // Gadget item (also padded by 1 on all sides for separation)
        int t = (int)hostList[u].size();
        if (t > 0) {
            info[u].hasGadget = true;
            int cols = isqrt_ceil(t);
            int rows = (t + cols - 1) / cols;
            int gW = max(3, 2 * cols + 1);
            int gH = max(3, 2 * rows + 1);
            info[u].gW = gW;
            info[u].gH = gH;
            info[u].gCols = cols;
            info[u].gRows = rows;
            items.push_back(Item{0, gW + 2, gH + 2});
        } else {
            info[u].hasGadget = false;
            info[u].gW = info[u].gH = 0;
            info[u].gCols = info[u].gRows = 0;
        }

        if (items.empty()) {
            info[u].innerW = 1;
            info[u].innerH = 1;
            info[u].W = 3;
            info[u].H = 3;
            info[u].layout.clear();
            return;
        }

        // Sort items by height descending (then width)
        vector<Item> itemsSorted = items;
        sort(itemsSorted.begin(), itemsSorted.end(), [](const Item& a, const Item& b) {
            if (a.h != b.h) return a.h > b.h;
            return a.w > b.w;
        });

        int lb = 1, sumW = 0;
        for (auto &it : itemsSorted) {
            lb = max(lb, it.w);
            sumW += it.w;
        }

        int maxInner = (u == root ? 238 : 236); // keep room for outer margin; non-root must allow padding into parent
        int ub = min(maxInner, max(lb, sumW));

        int bestW = -1, bestH = -1;
        vector<Placed> bestLayout;
        int bestMaxDim = INT_MAX / 4;
        long long bestArea = (1LL << 60);

        for (int W_in = lb; W_in <= ub; W_in++) {
            auto [H_in, placed] = packShelf(itemsSorted, W_in);
            if (H_in >= INT_MAX / 8) continue;
            if (H_in > maxInner) continue; // keep node not too tall as well
            int maxDim = max(W_in, H_in);
            long long area = 1LL * W_in * H_in;
            if (maxDim < bestMaxDim || (maxDim == bestMaxDim && area < bestArea) ||
                (maxDim == bestMaxDim && area == bestArea && W_in < bestW)) {
                bestMaxDim = maxDim;
                bestArea = area;
                bestW = W_in;
                bestH = H_in;
                bestLayout = std::move(placed);
            }
        }

        // If failed under constraints, relax height constraint but still cap width
        if (bestW == -1) {
            ub = maxInner;
            for (int W_in = lb; W_in <= ub; W_in++) {
                auto [H_in, placed] = packShelf(itemsSorted, W_in);
                if (H_in >= INT_MAX / 8) continue;
                int maxDim = max(W_in, H_in);
                long long area = 1LL * W_in * H_in;
                if (maxDim < bestMaxDim || (maxDim == bestMaxDim && area < bestArea) ||
                    (maxDim == bestMaxDim && area == bestArea && W_in < bestW)) {
                    bestMaxDim = maxDim;
                    bestArea = area;
                    bestW = W_in;
                    bestH = H_in;
                    bestLayout = std::move(placed);
                }
            }
        }

        // Absolute fallback (should not happen): single column packing
        if (bestW == -1) {
            int W_in = lb;
            auto [H_in, placed] = packShelf(itemsSorted, W_in);
            bestW = W_in;
            bestH = H_in;
            bestLayout = std::move(placed);
        }

        info[u].innerW = bestW;
        info[u].innerH = bestH;
        info[u].W = bestW + 2;
        info[u].H = bestH + 2;
        if (info[u].W < 3) info[u].W = 3;
        if (info[u].H < 3) info[u].H = 3;
        info[u].layout = std::move(bestLayout);
    };

    for (int u : order) computeNode(u);

    int K = max(info[root].W, info[root].H);
    if (K < 1) K = 1;
    if (K > 240) K = 240; // should not happen with constraints above

    vector<vector<int>> grid(K, vector<int>(K, root));

    auto fillRect = [&](int top, int left, int h, int w, int color) {
        int r0 = max(0, top), c0 = max(0, left);
        int r1 = min(K, top + h), c1 = min(K, left + w);
        for (int r = r0; r < r1; r++) {
            for (int c = c0; c < c1; c++) grid[r][c] = color;
        }
    };

    function<void(int,int,int)> draw = [&](int u, int top, int left) {
        if (u != root) fillRect(top, left, info[u].H, info[u].W, u);

        int originR = top + 1;
        int originC = left + 1;

        for (auto &pl : info[u].layout) {
            int padTop = originR + pl.x;
            int padLeft = originC + pl.y;
            if (pl.id >= 1) {
                int v = pl.id;
                int childTop = padTop + 1;
                int childLeft = padLeft + 1;
                draw(v, childTop, childLeft);
            } else if (pl.id == 0) {
                info[u].gTop = padTop + 1;
                info[u].gLeft = padLeft + 1;
            }
        }

        if (info[u].hasGadget) {
            int gt = info[u].gTop, gl = info[u].gLeft;
            if (gt >= 0 && gl >= 0) {
                int cols = info[u].gCols;
                for (int idx = 0; idx < (int)hostList[u].size(); idx++) {
                    int rr = idx / cols;
                    int cc = idx % cols;
                    int r = gt + 1 + 2 * rr;
                    int c = gl + 1 + 2 * cc;
                    if (0 <= r && r < K && 0 <= c && c < K) {
                        grid[r][c] = hostList[u][idx];
                    }
                }
            }
        }
    };

    draw(root, 0, 0);

    return grid;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int N, M;
        cin >> N >> M;
        vector<int> A(M), B(M);
        for (int i = 0; i < M; i++) cin >> A[i] >> B[i];

        auto C = create_map(N, M, A, B);
        int K = (int)C.size();

        cout << K << "\n";
        for (int i = 0; i < K; i++) {
            if (i) cout << ' ';
            cout << K;
        }
        cout << "\n\n";
        for (int i = 0; i < K; i++) {
            for (int j = 0; j < K; j++) {
                if (j) cout << ' ';
                cout << C[i][j];
            }
            cout << "\n";
        }
        if (T) cout << "\n";
    }
    return 0;
}