#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static inline int gc() {
        return getchar();
    }
    bool readLongLong(long long &out) {
        int c = gc();
        while (c != EOF && (c != '-' && (c < '0' || c > '9'))) c = gc();
        if (c == EOF) return false;
        int sign = 1;
        if (c == '-') { sign = -1; c = gc(); }
        long long x = 0;
        while (c >= '0' && c <= '9') {
            x = x * 10 + (c - '0');
            c = gc();
        }
        out = x * sign;
        return true;
    }
    bool readInt(int &out) {
        long long tmp;
        if (!readLongLong(tmp)) return false;
        out = (int)tmp;
        return true;
    }
};

struct DistMatrix {
    int n;
    vector<long long> tri; // upper triangular (i<j) stored row-wise
    vector<long long> offset; // offset for i: starting index in tri for pairs (i, j>i)
    DistMatrix() : n(0) {}
    DistMatrix(int _n) { init(_n); }
    void init(int _n) {
        n = _n;
        long long m = 1LL * n * (n - 1) / 2;
        tri.assign((size_t)m, 0);
        offset.assign(n + 2, 0);
        // offset[i] = sum_{k=1}^{i-1} (n - k) = (i-1)*n - (i-1)*i/2
        for (int i = 1; i <= n; ++i) {
            offset[i] = 1LL * (i - 1) * n - 1LL * (i - 1) * i / 2;
        }
    }
    inline long long &atPairIdx(int i, int j) { // i<j
        return tri[(size_t)(offset[i] + (j - i - 1))];
    }
    inline long long get(int i, int j) const {
        if (i == j) return 0;
        if (i < j) {
            return tri[(size_t)(offset[i] + (j - i - 1))];
        } else {
            return tri[(size_t)(offset[j] + (i - j - 1))];
        }
    }
};

int N;
DistMatrix D;
vector<tuple<int,int,long long>> edges;

void reconstruct(const vector<int> &S) {
    if (S.size() <= 1) return;
    // find diameter endpoints within S using two-sweep
    int s0 = S[0];
    int t = s0;
    long long best = -1;
    for (int x : S) {
        long long dv = D.get(s0, x);
        if (dv > best) { best = dv; t = x; }
    }
    int u = t;
    best = -1;
    for (int x : S) {
        long long dv = D.get(t, x);
        if (dv > best) { best = dv; u = x; }
    }
    int a = u, b = t;
    long long Sab = D.get(a, b);

    // collect nodes on path from a to b
    vector<int> pathNodes;
    pathNodes.reserve(S.size());
    for (int x : S) {
        if (D.get(a, x) + D.get(x, b) == Sab) pathNodes.push_back(x);
    }
    sort(pathNodes.begin(), pathNodes.end(), [&](int x, int y){
        return D.get(a, x) < D.get(a, y);
    });

    // add edges along the path
    for (size_t i = 0; i + 1 < pathNodes.size(); ++i) {
        int u1 = pathNodes[i], v1 = pathNodes[i+1];
        long long w = D.get(a, v1) - D.get(a, u1);
        edges.emplace_back(u1, v1, w);
    }

    // prepare mapping: node -> index in path, and distances from a along path
    vector<int> idxInPath(N + 1, -1);
    vector<long long> distAPath(pathNodes.size());
    for (size_t i = 0; i < pathNodes.size(); ++i) {
        idxInPath[pathNodes[i]] = (int)i;
        distAPath[i] = D.get(a, pathNodes[i]);
    }

    // groups for recursion: for each path index, collect nodes not on path that project to that node
    vector<vector<int>> groups(pathNodes.size());
    vector<char> inPath(N + 1, 0);
    for (int p : pathNodes) inPath[p] = 1;

    for (int v : S) if (!inPath[v]) {
        long long da = D.get(a, v), db = D.get(b, v);
        long long delta2 = da + db - Sab; // 2*delta
        long long delta = delta2 / 2;
        long long xdist = da - delta; // distance from a to projection on path
        // binary search xdist in distAPath
        auto it = lower_bound(distAPath.begin(), distAPath.end(), xdist);
        if (it == distAPath.end() || *it != xdist) {
            // theoretically should not happen in a valid tree metric
            // but if it does, we skip to avoid crash
            continue;
        }
        int pos = (int)(it - distAPath.begin());
        groups[pos].push_back(v);
    }

    // recurse on each group
    for (size_t i = 0; i < groups.size(); ++i) {
        if (!groups[i].empty()) {
            vector<int> subS;
            subS.reserve(groups[i].size() + 1);
            subS.push_back(pathNodes[i]);
            for (int v : groups[i]) subS.push_back(v);
            reconstruct(subS);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    FastScanner fs;
    int T;
    {
        int tmp;
        if (!fs.readInt(tmp)) return 0;
        T = tmp;
    }
    for (int tc = 0; tc < T; ++tc) {
        int n;
        {
            int tmp;
            fs.readInt(tmp);
            n = tmp;
        }
        N = n;
        D.init(n);
        long long m = 1LL * n * (n - 1) / 2;
        for (int i = 1; i <= n - 1; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                long long val;
                fs.readLongLong(val);
                D.atPairIdx(i, j) = val;
            }
        }
        edges.clear();
        edges.reserve((size_t)max(0, n - 1));
        vector<int> all(n);
        for (int i = 0; i < n; ++i) all[i] = i + 1;
        reconstruct(all);

        cout << "!";
        // If by some chance we have more than n-1 due to duplicates, we can trim by using a map
        if ((int)edges.size() != n - 1) {
            // Deduplicate just in case
            map<pair<int,int>, long long> mp;
            for (auto &e : edges) {
                int u, v; long long w;
                tie(u, v, w) = e;
                if (u > v) swap(u, v);
                mp[{u, v}] = w;
            }
            edges.clear();
            edges.reserve(mp.size());
            for (auto &kv : mp) {
                edges.emplace_back(kv.first.first, kv.first.second, kv.second);
            }
        }
        for (auto &e : edges) {
            int u, v; long long w;
            tie(u, v, w) = e;
            cout << " " << u << " " << v << " " << w;
        }
        cout << "\n";
    }
    return 0;
}