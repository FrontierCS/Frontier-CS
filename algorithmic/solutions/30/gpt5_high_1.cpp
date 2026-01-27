#include <bits/stdc++.h>
using namespace std;

struct Fenwick {
    int n;
    vector<int> f;
    Fenwick() {}
    Fenwick(int n): n(n), f(n+2, 0) {}
    void init(int n_) { n = n_; f.assign(n+2, 0); }
    void add(int i, int v) {
        for (; i <= n; i += i & -i) f[i] += v;
    }
    int sumPrefix(int i) const {
        int s = 0;
        for (; i > 0; i -= i & -i) s += f[i];
        return s;
    }
    int sumRange(int l, int r) const {
        if (l > r) return 0;
        return sumPrefix(r) - sumPrefix(l-1);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> g(n+1);
        for (int i = 0; i < n-1; ++i) {
            int u, v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }
        vector<int> parent(n+1), depth(n+1), tin(n+1), tout(n+1), euler(2*n+5);
        int timer = 0;
        function<void(int,int)> dfs = [&](int u, int p){
            parent[u] = p;
            tin[u] = ++timer;
            euler[timer] = u;
            for (int v : g[u]) {
                if (v == p) continue;
                depth[v] = depth[u] + 1;
                dfs(v, u);
            }
            tout[u] = timer + 1; // exclusive
        };
        depth[1] = 0;
        dfs(1, 0);
        // Initialize candidate set Y: all nodes possible initially
        vector<char> inY(n+1, 1);
        int Ysize = n;

        auto choose_best_query = [&](const vector<char>& mark)->int {
            // Build Fenwick of marks on Euler order to get In_x counts
            Fenwick bit(n+2);
            bit.init(n+2);
            for (int v = 1; v <= n; ++v) if (mark[v]) bit.add(tin[v], 1);
            vector<int> inCount(n+1, 0);
            for (int x = 1; x <= n; ++x) {
                inCount[x] = bit.sumRange(tin[x], tout[x]-1);
            }
            // Build A[p], minTin[p], maxTin[p]
            vector<int> A(n+1, 0);
            vector<int> minTin(n+1, INT_MAX), maxTin(n+1, -INT_MAX);
            bool rootInY = mark[1];
            for (int v = 1; v <= n; ++v) {
                if (!mark[v]) continue;
                if (v != 1) {
                    int p = parent[v];
                    A[p]++;
                    int tv = tin[v];
                    if (tv < minTin[p]) minTin[p] = tv;
                    if (tv > maxTin[p]) maxTin[p] = tv;
                }
            }
            int totalParents = 0;
            vector<pair<int,int>> intervals; intervals.reserve(n);
            for (int p = 1; p <= n; ++p) {
                if (A[p] > 0) {
                    totalParents++;
                    intervals.emplace_back(minTin[p], maxTin[p]);
                }
            }
            // Compute AllInsideCount[x] for all x: number of intervals fully inside subtree x
            // Condition: L >= tin[x] and R < tout[x]
            vector<pair<int,int>> queries; queries.reserve(n);
            for (int x = 1; x <= n; ++x) {
                queries.emplace_back(tin[x], x);
            }
            sort(queries.begin(), queries.end(), [](const pair<int,int>& a, const pair<int,int>& b){
                if (a.first != b.first) return a.first > b.first; // descending tin
                return a.second < b.second;
            });
            sort(intervals.begin(), intervals.end(), [](const pair<int,int>& a, const pair<int,int>& b){
                if (a.first != b.first) return a.first > b.first; // descending L
                return a.second < b.second;
            });
            Fenwick bitR(n+2);
            bitR.init(n+2);
            vector<int> allInsideCnt(n+1, 0);
            int ptr = 0;
            for (auto &qq : queries) {
                int tx = qq.first;
                int x = qq.second;
                while (ptr < (int)intervals.size() && intervals[ptr].first >= tx) {
                    int R = intervals[ptr].second;
                    bitR.add(R, 1);
                    ++ptr;
                }
                int outR = tout[x] - 1;
                if (outR < 1) allInsideCnt[x] = 0;
                else allInsideCnt[x] = bitR.sumPrefix(outR);
            }
            // Compute PNot[x]
            vector<int> pnot(n+1, 0);
            for (int x = 1; x <= n; ++x) {
                int val = totalParents - allInsideCnt[x];
                if (rootInY && x != 1) {
                    bool extra = false;
                    if (A[1] == 0) extra = true;
                    else {
                        if (minTin[1] >= tin[x] && maxTin[1] < tout[x]) extra = true;
                    }
                    if (extra) val += 1;
                }
                pnot[x] = val;
            }
            // Choose x minimizing max(inCount[x], pnot[x]); tie-break by smaller depth
            int bestX = 1;
            int bestW = INT_MAX;
            for (int x = 1; x <= n; ++x) {
                int w = max(inCount[x], pnot[x]);
                if (w < bestW) {
                    bestW = w;
                    bestX = x;
                } else if (w == bestW) {
                    if (depth[x] < depth[bestX]) bestX = x;
                }
            }
            return bestX;
        };

        int queries_used = 0;
        while (true) {
            if (Ysize == 1) {
                int ansNode = -1;
                for (int v = 1; v <= n; ++v) if (inY[v]) { ansNode = v; break; }
                cout << "! " << ansNode << "\n";
                cout.flush();
                break;
            }
            int x = choose_best_query(inY);
            cout << "? " << x << "\n";
            cout.flush();
            int r;
            if (!(cin >> r)) return 0;
            queries_used++;
            vector<char> nextMark(n+1, 0);
            if (r == 1) {
                // Keep those y in subtree x
                for (int v = 1; v <= n; ++v) if (inY[v]) {
                    if (tin[v] >= tin[x] && tin[v] < tout[x]) nextMark[v] = 1;
                }
            } else {
                // Move those not in subtree x to their parent (root stays root)
                for (int v = 1; v <= n; ++v) if (inY[v]) {
                    if (!(tin[v] >= tin[x] && tin[v] < tout[x])) {
                        int u = (v == 1 ? 1 : parent[v]);
                        nextMark[u] = 1;
                    }
                }
            }
            inY.swap(nextMark);
            Ysize = 0;
            for (int v = 1; v <= n; ++v) if (inY[v]) Ysize++;
            if (queries_used > 160) {
                // In interactive CF, should terminate; Here, just print something to avoid infinite loop
                int ansNode = -1;
                for (int v = 1; v <= n; ++v) if (inY[v]) { ansNode = v; break; }
                if (ansNode == -1) ansNode = 1;
                cout << "! " << ansNode << "\n";
                cout.flush();
                break;
            }
        }
    }
    return 0;
}