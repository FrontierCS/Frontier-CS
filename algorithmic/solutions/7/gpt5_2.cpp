#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int to;
    int w;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long L, R;
    if (!(cin >> L >> R)) return 0;

    auto bitlen = [&](long long x)->int{
        int b = 0;
        while (x) { b++; x >>= 1; }
        return b;
    };

    int maxLen = bitlen(R); // maximum number of bits needed
    // Graph structures
    vector<vector<Edge>> g(1); // 1-based; g[0] unused

    auto newNode = [&]()->int{
        g.push_back({});
        return (int)g.size() - 1;
    };

    auto addEdge = [&](int u, int v, int w){
        // avoid duplicate identical edges
        for (auto &e : g[u]) {
            if (e.to == v && e.w == w) return;
        }
        g[u].push_back({v, w});
    };

    int root = newNode(); // id = 1

    // Prepare suffix nodes S[k]: represent "k remaining arbitrary bits"
    // S[0] is sink; S[k] (k>=1) has edges 0/1 -> S[k-1]
    vector<int> S(maxLen + 1, -1);
    S[0] = newNode(); // sink
    for (int k = 1; k <= maxLen; ++k) {
        S[k] = newNode();
    }
    for (int k = 1; k <= maxLen; ++k) {
        addEdge(S[k], S[k-1], 0);
        addEdge(S[k], S[k-1], 1);
    }

    // Map prefix (value,len) -> node id
    unordered_map<unsigned long long, int> prefId;
    prefId.reserve(4096);
    prefId.max_load_factor(0.7f);
    auto keyOf = [](unsigned int val, int len)->unsigned long long{
        return ( (unsigned long long)val << 6 ) | (unsigned long long)len; // len <= 60 safe here (we use <= 20)
    };

    // Ensure path for prefix (val, len) from root exists; return node id
    function<int(unsigned int,int)> ensurePrefix = [&](unsigned int val, int len)->int{
        if (len == 0) return root;
        unsigned long long key = keyOf(val, len);
        auto it = prefId.find(key);
        if (it != prefId.end()) return it->second;

        // Build path from root
        int cur = root;
        for (int i = 1; i <= len; ++i) {
            unsigned int pval = val >> (len - i); // prefix value of length i
            unsigned long long pkey = keyOf(pval, i);
            auto it2 = prefId.find(pkey);
            int nxt;
            int bit = (pval & 1); // i-th bit of full prefix (most significant first)
            if (it2 != prefId.end()) {
                nxt = it2->second;
            } else {
                nxt = newNode();
                prefId[pkey] = nxt;
            }
            // add edge from cur to nxt with label 'bit'
            addEdge(cur, nxt, bit);
            cur = nxt;
        }
        return cur;
    };

    // Decompose [L, R] per bit-length to avoid leading zeros
    int lowLen = bitlen(L);
    for (int len = lowLen; len <= maxLen; ++len) {
        long long lo = max(L, 1LL << (len - 1));
        long long hi = min(R, (1LL << len) - 1);
        if (lo > hi) continue;

        long long x = lo;
        while (x <= hi) {
            int k = 0;
            // Find largest block 2^k such that x is divisible by 2^k and x + 2^k - 1 <= hi
            // Equivalent to k = min(ctz(x), floor(log2(hi - x + 1)))
            int tz = 0;
            if (x != 0) tz = __builtin_ctzll(x);
            int lim = 63 - __builtin_clzll(hi - x + 1);
            k = min(tz, lim);
            // Also ensure k <= len-1 (since within fixed length)
            k = min(k, len - 1);
            // However, due to restriction within [2^{len-1}, 2^len-1], it's safe.

            long long blockSize = 1LL << k;
            long long a = x;
            // prefix value and length
            unsigned int prefVal = (unsigned int)(a >> k);
            int prefLen = len - k;

            if (k > 0) {
                int pnode = ensurePrefix(prefVal, prefLen);
                // From this prefix, allow any k bits
                addEdge(pnode, S[k-1], 0);
                addEdge(pnode, S[k-1], 1);
            } else {
                // Single number; add edge from parent prefix to sink with last bit
                int preLen = prefLen - 1;
                unsigned int preVal = (preLen > 0) ? (prefVal >> 1) : 0;
                int parentNode = ensurePrefix(preVal, preLen);
                int lastBit = prefVal & 1;
                addEdge(parentNode, S[0], lastBit);
            }

            x += blockSize;
        }
    }

    // Output
    int n = (int)g.size() - 1;
    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        cout << (int)g[i].size();
        for (auto &e : g[i]) {
            cout << " " << e.to << " " << e.w;
        }
        cout << "\n";
    }
    return 0;
}