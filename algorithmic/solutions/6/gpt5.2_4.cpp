#include <bits/stdc++.h>
using namespace std;

struct Layout {
    int w = 0, h = 0;            // total rectangle size including 1-cell border
    int innerW = 0, innerH = 0;  // inner size
    int childrenH = 0;           // packed children height inside inner area
    int sep = 0;                // separator rows between children and gadgets (0/1)
    int gadgetW = 0, gadgetH = 0;
    int gadgetStartY = 0;        // relative to top of rectangle
    vector<int> order;           // children order
    vector<pair<int,int>> pos;   // child positions in inner coords (y,x), aligned with order
};

static int pack_children_height(const vector<int>& order, const vector<Layout>& lay, int innerW) {
    if (order.empty()) return 0;
    int x = 0, y = 0, rowH = 0;
    for (int v : order) {
        int wv = lay[v].w;
        int hv = lay[v].h;
        if (x > 0 && x + wv > innerW) {
            y += rowH + 1; // 1-row gap between shelves
            x = 0;
            rowH = 0;
        }
        // place at (y, x)
        x += wv;
        if (x < innerW) x += 1; // 1-col gap to next
        rowH = max(rowH, hv);
    }
    return y + rowH;
}

static int pack_children_positions(const vector<int>& order, const vector<Layout>& lay, int innerW, vector<pair<int,int>>& outPos) {
    outPos.clear();
    if (order.empty()) return 0;
    outPos.reserve(order.size());
    int x = 0, y = 0, rowH = 0;
    for (int v : order) {
        int wv = lay[v].w;
        int hv = lay[v].h;
        if (x > 0 && x + wv > innerW) {
            y += rowH + 1;
            x = 0;
            rowH = 0;
        }
        outPos.push_back({y, x});
        x += wv;
        if (x < innerW) x += 1;
        rowH = max(rowH, hv);
    }
    return y + rowH;
}

struct Builder {
    int N = 0, M = 0;
    vector<int> A, B;

    vector<vector<int>> adj;
    bool isEdge[41][41]{};
    bool isTree[41][41]{};

    vector<int> parent;
    vector<vector<int>> children;
    vector<vector<int>> gadgets;

    vector<Layout> lay;

    int slotRows = 2; // gadget slots rows count => gadgetH = 2*slotRows-1 = 3
    int gadgetHConst = 3;

    bool build_spanning_tree() {
        parent.assign(N + 1, -1);
        children.assign(N + 1, {});
        queue<int> q;
        parent[1] = 0;
        q.push(1);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (parent[v] == -1) {
                    parent[v] = u;
                    q.push(v);
                }
            }
        }
        for (int i = 2; i <= N; i++) {
            if (parent[i] == -1) return false;
            int p = parent[i];
            isTree[min(i,p)][max(i,p)] = true;
            children[p].push_back(i);
        }
        return true;
    }

    void assign_gadgets() {
        gadgets.assign(N + 1, {});
        vector<int> load(N + 1, 0);
        for (int i = 0; i < M; i++) {
            int a = A[i], b = B[i];
            int x = min(a,b), y = max(a,b);
            if (isTree[x][y]) continue;
            int u;
            if (load[a] < load[b]) u = a;
            else if (load[b] < load[a]) u = b;
            else u = min(a,b);
            int v = (u == a ? b : a);
            gadgets[u].push_back(v);
            load[u]++;
        }
    }

    void compute_gadget_dims(int u, int& gW, int& gH) {
        int g = (int)gadgets[u].size();
        if (g == 0) { gW = 0; gH = 0; return; }
        int cols = (g + slotRows - 1) / slotRows;
        gW = 2 * cols - 1;
        gH = gadgetHConst;
    }

    bool dfs_size(int u, int Kmax) {
        for (int v : children[u]) {
            if (!dfs_size(v, Kmax)) return false;
        }

        Layout L;
        int gW, gH;
        compute_gadget_dims(u, gW, gH);
        L.gadgetW = gW;
        L.gadgetH = gH;

        // child order: sort by width desc, then height desc
        L.order = children[u];
        sort(L.order.begin(), L.order.end(), [&](int a, int b) {
            if (lay[a].w != lay[b].w) return lay[a].w > lay[b].w;
            return lay[a].h > lay[b].h;
        });

        int maxChildW = 0;
        for (int v : L.order) maxChildW = max(maxChildW, lay[v].w);

        int minInnerW = max(1, max(maxChildW, gW));
        int bestInnerW = -1;
        int bestInnerH = -1;
        int bestChildrenH = -1;
        int bestSep = 0;
        long long bestMetric = (1LL << 60);

        for (int innerW = minInnerW; innerW <= Kmax - 2; innerW++) {
            int cH = pack_children_height(L.order, lay, innerW);
            int sep = (cH > 0 && gH > 0) ? 1 : 0;
            int innerH = cH + sep + gH;
            if (innerH < 1) innerH = 1;

            int W = innerW + 2;
            int H = innerH + 2;
            if (W > Kmax || H > Kmax) continue;

            long long metric = (long long)max(W, H) * 1000000LL + (long long)(W + H);
            if (metric < bestMetric) {
                bestMetric = metric;
                bestInnerW = innerW;
                bestInnerH = innerH;
                bestChildrenH = cH;
                bestSep = sep;
            }
        }
        if (bestInnerW == -1) return false;

        L.innerW = bestInnerW;
        L.innerH = bestInnerH;
        L.w = bestInnerW + 2;
        L.h = bestInnerH + 2;
        L.childrenH = bestChildrenH;
        L.sep = bestSep;
        L.gadgetStartY = 1 + bestChildrenH + bestSep;

        // store positions
        pack_children_positions(L.order, lay, bestInnerW, L.pos);

        lay[u] = std::move(L);
        return true;
    }

    void paint(int u, int top, int left, vector<vector<int>>& C) {
        const Layout& L = lay[u];
        for (int i = 0; i < L.h; i++) {
            for (int j = 0; j < L.w; j++) {
                C[top + i][left + j] = u;
            }
        }

        // children
        for (size_t i = 0; i < L.order.size(); i++) {
            int v = L.order[i];
            int y = L.pos[i].first;
            int x = L.pos[i].second;
            paint(v, top + 1 + y, left + 1 + x, C);
        }

        // gadgets (only overwrite in gadget area)
        int g = (int)gadgets[u].size();
        if (g > 0) {
            int baseY = top + L.gadgetStartY;
            int baseX = left + 1;
            for (int idx = 0; idx < g; idx++) {
                int rr = (idx % slotRows) * 2;
                int cc = (idx / slotRows) * 2;
                C[baseY + rr][baseX + cc] = gadgets[u][idx];
            }
        }
    }

    vector<vector<int>> create_map() {
        if (N == 1) return vector<vector<int>>(1, vector<int>(1, 1));

        adj.assign(N + 1, {});
        memset(isEdge, 0, sizeof(isEdge));
        memset(isTree, 0, sizeof(isTree));

        for (int i = 0; i < M; i++) {
            int a = A[i], b = B[i];
            isEdge[a][b] = isEdge[b][a] = true;
            adj[a].push_back(b);
            adj[b].push_back(a);
        }

        if (!build_spanning_tree()) {
            // Shouldn't happen due to guarantee; fallback to trivial (may be invalid)
            return vector<vector<int>>(1, vector<int>(1, 1));
        }

        assign_gadgets();

        int Kfound = -1;
        int Kfinal = -1;
        int Kstart = max(3, N);
        lay.assign(N + 1, Layout());

        for (int K = Kstart; K <= 240; K++) {
            lay.assign(N + 1, Layout());
            if (!dfs_size(1, K)) continue;
            int rw = lay[1].w, rh = lay[1].h;
            if (rw <= K && rh <= K) {
                Kfound = K;
                Kfinal = max(rw, rh);
                break;
            }
        }
        if (Kfound == -1) {
            // Guaranteed to exist; last resort
            Kfinal = 240;
            lay.assign(N + 1, Layout());
            dfs_size(1, 240);
        }

        vector<vector<int>> C(Kfinal, vector<int>(Kfinal, 1));
        paint(1, 0, 0, C);
        return C;
    }
};

static vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    Builder b;
    b.N = N;
    b.M = M;
    b.A = std::move(A);
    b.B = std::move(B);
    return b.create_map();
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
    }
    return 0;
}