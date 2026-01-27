#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int to;
    int w;
};

static vector<vector<Edge>> g;
static int startNode, endNode;
static vector<int> anyMemo; // anyMemo[k] = node id for generating any k bits then end
static unordered_map<long long, int> rangeMemo;

static int newNode() {
    g.push_back({});
    return (int)g.size() - 1;
}

static int ensureAny(int k) {
    if (k == 0) return endNode;
    if (anyMemo[k]) return anyMemo[k];
    int v = newNode();
    anyMemo[k] = v;
    int child = ensureAny(k - 1);
    g[v].push_back({child, 0});
    g[v].push_back({child, 1});
    return v;
}

// Generates exactly all k-bit strings whose numeric value in [a,b] (0 <= a <= b < 2^k).
static int rangeNode(int k, int a, int b) {
    if (k == 0) return endNode; // only possible interval is [0,0]
    int full = (1 << k) - 1;
    if (a == 0 && b == full) return ensureAny(k);

    long long key = ( (long long)k << 40 ) | ( (long long)a << 20 ) | (long long)b;
    auto it = rangeMemo.find(key);
    if (it != rangeMemo.end()) return it->second;

    int half = 1 << (k - 1);
    int v = newNode();

    if (b < half) {
        int child = rangeNode(k - 1, a, b);
        g[v].push_back({child, 0});
    } else if (a >= half) {
        int child = rangeNode(k - 1, a - half, b - half);
        g[v].push_back({child, 1});
    } else {
        int leftChild = rangeNode(k - 1, a, half - 1);
        int rightChild = rangeNode(k - 1, 0, b - half);
        g[v].push_back({leftChild, 0});
        g[v].push_back({rightChild, 1});
    }

    rangeMemo[key] = v;
    return v;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int L, R;
    cin >> L >> R;

    g.reserve(105);
    g.push_back({}); // dummy 0-index
    startNode = newNode(); // 1
    endNode = newNode();   // 2

    int maxLen = 32 - __builtin_clz((unsigned)R); // bit length of R, 1..20
    int maxSuffix = maxLen - 1;

    anyMemo.assign(maxSuffix + 1, 0);
    anyMemo[0] = endNode;

    for (int m = 1; m <= maxLen; m++) {
        long long blockLo = 1LL << (m - 1);
        long long blockHi = (1LL << m) - 1;

        long long lo = max<long long>(L, blockLo);
        long long hi = min<long long>(R, blockHi);
        if (lo > hi) continue;

        int k = m - 1;
        int target;
        if (L <= blockLo && blockHi <= R) {
            target = ensureAny(k);
        } else {
            int a = (int)(lo - blockLo);
            int b = (int)(hi - blockLo);
            target = rangeNode(k, a, b);
        }
        g[startNode].push_back({target, 1});
    }

    int n = (int)g.size() - 1;
    // Guaranteed by construction: n <= 100
    cout << n << "\n";
    for (int i = 1; i <= n; i++) {
        cout << g[i].size();
        for (const auto &e : g[i]) {
            cout << ' ' << e.to << ' ' << e.w;
        }
        cout << "\n";
    }
    return 0;
}