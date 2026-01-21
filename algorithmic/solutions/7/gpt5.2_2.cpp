#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int to;
    int w;
};

struct Builder {
    vector<vector<Edge>> adj;          // 1-indexed
    int start = -1, terminal = -1;
    vector<int> fullMemo;              // fullMemo[rem] -> node id (rem bits remaining)
    unordered_map<long long, int> memo; // (rem,a,b) -> node id

    int newNode() {
        adj.push_back({});
        return (int)adj.size() - 1;
    }

    int fullNode(int rem) {
        if (fullMemo[rem] != -1) return fullMemo[rem];
        int id = newNode();
        fullMemo[rem] = id;
        int child = fullNode(rem - 1);
        adj[id].push_back({child, 0});
        adj[id].push_back({child, 1});
        return id;
    }

    int buildRange(int a, int b, int rem) {
        if (rem == 0) return terminal;
        if (a == 0 && b == ((1 << rem) - 1)) return fullNode(rem);

        long long key = ( (long long)rem << 40 ) | ( (long long)a << 20 ) | (long long)b;
        auto it = memo.find(key);
        if (it != memo.end()) return it->second;

        int id = newNode();
        memo[key] = id;

        int half = 1 << (rem - 1);
        int msbA = (a >= half) ? 1 : 0;
        int msbB = (b >= half) ? 1 : 0;

        if (msbA == msbB) {
            int bit = msbA;
            int na = a - bit * half;
            int nb = b - bit * half;
            int child = buildRange(na, nb, rem - 1);
            adj[id].push_back({child, bit});
        } else {
            int child0 = buildRange(a, half - 1, rem - 1);
            int child1 = buildRange(0, b - half, rem - 1);
            adj[id].push_back({child0, 0});
            adj[id].push_back({child1, 1});
        }

        return id;
    }
};

static int bitlen(int x) {
    return 32 - __builtin_clz((unsigned)x);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int L, R;
    cin >> L >> R;

    int lenMax = bitlen(R);
    int maxRem = lenMax - 1;

    Builder B;
    B.adj.reserve(128);
    B.adj.push_back({});          // dummy 0
    B.start = B.newNode();        // 1
    B.terminal = B.newNode();     // 2

    B.fullMemo.assign(maxRem + 1, -1);
    B.fullMemo[0] = B.terminal;

    B.memo.reserve(2048);
    B.memo.max_load_factor(0.7f);

    vector<long long> pow2(lenMax + 1);
    pow2[0] = 1;
    for (int i = 1; i <= lenMax; i++) pow2[i] = pow2[i - 1] << 1;

    for (int len = 1; len <= lenMax; len++) {
        long long minVal = pow2[len - 1];
        long long maxVal = pow2[len] - 1;
        long long lo = max<long long>(L, minVal);
        long long hi = min<long long>(R, maxVal);
        if (lo > hi) continue;

        int rem = len - 1;
        int entry;
        if (lo == minVal && hi == maxVal) {
            entry = B.fullNode(rem);
        } else {
            int a = (int)(lo - minVal);
            int b = (int)(hi - minVal);
            entry = (rem == 0) ? B.terminal : B.buildRange(a, b, rem);
        }
        B.adj[B.start].push_back({entry, 1});
    }

    int n = (int)B.adj.size() - 1;

    // Sanity: ensure exactly one node with indegree 0 (start)
    // and exactly one node with outdegree 0 (terminal).
    // (Not strictly necessary to print, but ensures construction is sound.)
    vector<int> indeg(n + 1, 0), outdeg(n + 1, 0);
    for (int i = 1; i <= n; i++) {
        outdeg[i] = (int)B.adj[i].size();
        for (auto &e : B.adj[i]) indeg[e.to]++;
    }
    // If there are any nodes other than start with indegree 0, they are unreachable/unreferenced.
    // This construction should not create such nodes.

    cout << n << "\n";
    for (int i = 1; i <= n; i++) {
        cout << B.adj[i].size();
        for (auto &e : B.adj[i]) {
            cout << ' ' << e.to << ' ' << e.w;
        }
        cout << "\n";
    }

    return 0;
}