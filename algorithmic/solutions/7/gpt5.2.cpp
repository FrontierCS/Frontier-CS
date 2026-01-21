#include <bits/stdc++.h>
using namespace std;

struct Node {
    vector<pair<int,int>> out; // (to, weight)
};

static int bitlen(int x) {
    return 32 - __builtin_clz((unsigned)x);
}

static vector<int> toBits(int x, int k) {
    vector<int> b(k);
    for (int i = 0; i < k; i++) b[i] = (x >> (k - 1 - i)) & 1;
    return b;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int L, R;
    cin >> L >> R;

    int maxLen = bitlen(R);

    vector<Node> nodes(1); // 1-indexed
    auto newNode = [&]() -> int {
        nodes.push_back(Node{});
        return (int)nodes.size() - 1;
    };

    int start = newNode();
    int end = newNode();

    vector<int> Gen(maxLen, -1); // Gen[t] generates exactly t bits then reaches end
    Gen[0] = end;
    for (int t = 1; t < maxLen; t++) {
        int id = newNode();
        Gen[t] = id;
        nodes[id].out.push_back({Gen[t-1], 0});
        nodes[id].out.push_back({Gen[t-1], 1});
    }

    auto addEdge = [&](int u, int v, int w) {
        nodes[u].out.push_back({v, w});
    };

    auto buildGE = [&](int k, const vector<int>& aBits) -> int {
        vector<int> memo(k + 1, -1);
        function<int(int)> dfs = [&](int pos) -> int {
            int rem = k - pos;
            if (rem == 0) return end;
            int &res = memo[pos];
            if (res != -1) return res;
            int id = newNode();
            res = id;

            int lb = aBits[pos];
            if (lb == 0) {
                addEdge(id, dfs(pos + 1), 0);
                addEdge(id, Gen[rem - 1], 1);
            } else {
                addEdge(id, dfs(pos + 1), 1);
            }
            return id;
        };
        return dfs(1);
    };

    auto buildLE = [&](int k, const vector<int>& bBits) -> int {
        vector<int> memo(k + 1, -1);
        function<int(int)> dfs = [&](int pos) -> int {
            int rem = k - pos;
            if (rem == 0) return end;
            int &res = memo[pos];
            if (res != -1) return res;
            int id = newNode();
            res = id;

            int hb = bBits[pos];
            if (hb == 0) {
                addEdge(id, dfs(pos + 1), 0);
            } else {
                addEdge(id, Gen[rem - 1], 0);
                addEdge(id, dfs(pos + 1), 1);
            }
            return id;
        };
        return dfs(1);
    };

    auto buildBetween = [&](int k, const vector<int>& aBits, const vector<int>& bBits) -> int {
        static int memo[25][2][2];
        for (int i = 0; i <= k; i++)
            for (int tl = 0; tl < 2; tl++)
                for (int th = 0; th < 2; th++)
                    memo[i][tl][th] = -1;

        function<int(int,int,int)> dfs = [&](int pos, int tL, int tH) -> int {
            int rem = k - pos;
            if (rem == 0) return end;
            if (!tL && !tH) return Gen[rem];

            int &res = memo[pos][tL][tH];
            if (res != -1) return res;
            int id = newNode();
            res = id;

            int lo = tL ? aBits[pos] : 0;
            int hi = tH ? bBits[pos] : 1;
            for (int x = lo; x <= hi; x++) {
                int ntL = tL && (x == aBits[pos]);
                int ntH = tH && (x == bBits[pos]);
                int to = dfs(pos + 1, ntL, ntH);
                addEdge(id, to, x);
            }
            return id;
        };

        return dfs(1, 1, 1);
    };

    int lenL = bitlen(L), lenR = bitlen(R);

    for (int k = lenL; k <= lenR; k++) {
        long long minK = 1LL << (k - 1);
        long long maxK = (1LL << k) - 1;
        long long low = max<long long>(L, minK);
        long long high = min<long long>(R, maxK);
        if (low > high) continue;

        int entry = -1;

        if (low == minK && high == maxK) {
            entry = Gen[k - 1];
        } else if (high == maxK) {
            auto aBits = toBits((int)low, k);
            entry = buildGE(k, aBits);
        } else if (low == minK) {
            auto bBits = toBits((int)high, k);
            entry = buildLE(k, bBits);
        } else {
            auto aBits = toBits((int)low, k);
            auto bBits = toBits((int)high, k);
            entry = buildBetween(k, aBits, bBits);
        }

        addEdge(start, entry, 1);
    }

    int n = (int)nodes.size() - 1;
    if (n > 100) {
        // Should not happen with this construction for given constraints.
        // If it does, fall back to a trivial (but invalid by constraints) output to avoid UB.
        // However, expected never to trigger.
        return 0;
    }

    cout << n << "\n";
    for (int i = 1; i <= n; i++) {
        cout << nodes[i].out.size();
        for (auto [to, w] : nodes[i].out) {
            cout << ' ' << to << ' ' << w;
        }
        cout << "\n";
    }
    return 0;
}