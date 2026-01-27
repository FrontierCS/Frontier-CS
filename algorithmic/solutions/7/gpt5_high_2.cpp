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

    int maxLen = 0;
    {
        long long t = R;
        while (t > 0) { t >>= 1; maxLen++; }
        if (maxLen == 0) maxLen = 1; // not needed as R>=1
    }

    vector<int> LB(maxLen, 0), RB(maxLen, 0);
    for (int i = 0; i < maxLen; ++i) {
        LB[i] = (L >> i) & 1;
        RB[i] = (R >> i) & 1;
    }

    vector<vector<Edge>> g;
    auto newNode = [&]() {
        g.push_back({});
        return (int)g.size() - 1;
    };

    int start = newNode(); // id 0 (we will output 1-based)
    int endNode = newNode(); // id 1

    // idMap[pos][lo][hi] -> node id
    vector<vector<array<int,2>>> idMap(maxLen, vector<array<int,2>>(2, array<int,2>{-1,-1}));

    function<int(int,int,int)> ensureNode = [&](int pos, int lo, int hi) -> int {
        int &id = idMap[pos][lo][hi];
        if (id != -1) return id;
        id = newNode();

        // For b = 0 or 1, check allowed and add edges
        for (int b = 0; b <= 1; ++b) {
            bool allowed = true;
            if (lo && b < LB[pos]) allowed = false;
            if (hi && b > RB[pos]) allowed = false;
            if (!allowed) continue;

            if (pos == 0) {
                g[id].push_back({endNode, b});
            } else {
                int lo2 = lo && (b == LB[pos]);
                int hi2 = hi && (b == RB[pos]);
                int v = ensureNode(pos - 1, lo2, hi2);
                g[id].push_back({v, b});
            }
        }
        return id;
    };

    // Add start edges: choose first '1' at position p, after implicit zeros above p
    for (int p = 0; p < maxLen; ++p) {
        int lo = 1, hi = 1;
        bool valid = true;
        for (int i = maxLen - 1; i > p; --i) {
            if (lo && LB[i] == 1) { valid = false; break; }
            lo = lo && (LB[i] == 0);
            hi = hi && (RB[i] == 0);
        }
        if (!valid) continue;

        // First bit must be 1 at position p
        int b = 1;
        if (hi && b > RB[p]) continue; // not allowed due to upper bound
        // lower bound (lo && b < LB[p]) never triggers since LB[p] in {0,1} and b=1

        int lo2 = lo && (b == LB[p]);
        int hi2 = hi && (b == RB[p]);
        if (p == 0) {
            g[start].push_back({endNode, 1});
        } else {
            int v = ensureNode(p - 1, lo2, hi2);
            g[start].push_back({v, 1});
        }
    }

    // Prepare output: nodes are 1-indexed in output
    int n = (int)g.size();
    cout << n << "\n";
    for (int i = 0; i < n; ++i) {
        cout << (int)g[i].size();
        for (auto &e : g[i]) {
            cout << " " << (e.to + 1) << " " << e.w;
        }
        cout << "\n";
    }

    return 0;
}