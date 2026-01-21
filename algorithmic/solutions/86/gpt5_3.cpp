#include <bits/stdc++.h>
using namespace std;

static mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

int n;

// Cache for queries to reduce number of real queries
unordered_map<long long, int> qcache;

// Encode a sorted triple (a,b,c) into a 64-bit key
inline long long enc(int a, int b, int c) {
    int x = a, y = b, z = c;
    if (x > y) swap(x, y);
    if (y > z) swap(y, z);
    if (x > y) swap(x, y);
    // pack into 63 bits: need only up to 11 bits each (n<=1000)
    return ( (long long)x << 42 ) ^ ( (long long)y << 21 ) ^ (long long)z;
}

int query(int a, int b, int c) {
    long long key = enc(a, b, c);
    auto it = qcache.find(key);
    if (it != qcache.end()) return it->second;
    cout << "0 " << a << " " << b << " " << c << "\n";
    cout.flush();
    int ans;
    if (!(cin >> ans)) exit(0);
    qcache[key] = ans;
    return ans;
}

vector<pair<int,int>> edges;
unordered_set<long long> edgeSet;

inline long long edgeKey(int u, int v) {
    if (u > v) swap(u, v);
    return ((long long)u << 32) ^ (long long)v;
}

void add_edge(int u, int v) {
    if (u == v) return;
    long long k = edgeKey(u, v);
    if (edgeSet.insert(k).second) {
        edges.emplace_back(u, v);
    }
}

bool cmp_on_path_with_a(int a, int u, int v) {
    int m = query(a, u, v);
    return (m == u);
}

void build(const vector<int>& S) {
    int sz = (int)S.size();
    if (sz <= 1) return;
    if (sz == 2) {
        add_edge(S[0], S[1]);
        return;
    }

    int a = S[uniform_int_distribution<int>(0, sz - 1)(rng)];
    int b;
    do {
        b = S[uniform_int_distribution<int>(0, sz - 1)(rng)];
    } while (b == a);

    unordered_map<int,int> proj;
    proj.reserve(sz * 2);
    for (int x : S) {
        if (x == a || x == b) {
            proj[x] = x;
        } else {
            proj[x] = query(a, b, x);
        }
    }

    vector<int> pathNodes;
    pathNodes.reserve(sz);
    for (int x : S) {
        if (proj[x] == x) pathNodes.push_back(x);
    }

    // Ensure a and b are on path
    if (find(pathNodes.begin(), pathNodes.end(), a) == pathNodes.end()) pathNodes.push_back(a);
    if (find(pathNodes.begin(), pathNodes.end(), b) == pathNodes.end()) pathNodes.push_back(b);

    // Remove a and b to sort internal nodes
    vector<int> inner;
    inner.reserve(pathNodes.size());
    for (int v : pathNodes) if (v != a && v != b) inner.push_back(v);

    auto cmp = [&](int u, int v) {
        return cmp_on_path_with_a(a, u, v);
    };
    sort(inner.begin(), inner.end(), cmp);

    vector<int> order;
    order.reserve(pathNodes.size());
    order.push_back(a);
    for (int v : inner) order.push_back(v);
    order.push_back(b);

    for (size_t i = 0; i + 1 < order.size(); ++i) {
        add_edge(order[i], order[i+1]);
    }

    unordered_map<int, vector<int>> groups;
    groups.reserve(order.size() * 2);
    for (int x : S) {
        int v = proj[x];
        groups[v].push_back(x);
    }

    for (auto &kv : groups) {
        // To avoid infinite recursion when group equals S (shouldn't happen as there are at least a and b on path)
        if ((int)kv.second.size() == sz) continue;
        build(kv.second);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;
    vector<int> all(n);
    iota(all.begin(), all.end(), 1);

    build(all);

    // Ensure we have exactly n-1 edges; if not, attempt to fill missing edges arbitrarily (shouldn't happen ideally)
    if ((int)edges.size() > n - 1) {
        edges.resize(n - 1);
    } else if ((int)edges.size() < n - 1) {
        // Fallback: connect remaining components arbitrarily
        vector<int> parent(n + 1);
        iota(parent.begin(), parent.end(), 0);
        function<int(int)> findp = [&](int x) {
            return parent[x] == x ? x : parent[x] = findp(parent[x]);
        };
        auto unite = [&](int a, int b) {
            a = findp(a); b = findp(b);
            if (a != b) parent[a] = b;
        };
        for (auto &e : edges) unite(e.first, e.second);
        int lastRoot = -1;
        for (int i = 1; i <= n; ++i) {
            int r = findp(i);
            if (lastRoot == -1) lastRoot = r;
            else if (r != lastRoot) {
                add_edge(lastRoot, r);
                unite(lastRoot, r);
                lastRoot = findp(lastRoot);
                if ((int)edges.size() == n - 1) break;
            }
        }
    }

    cout << "1";
    for (auto &e : edges) cout << " " << e.first << " " << e.second;
    cout << "\n";
    cout.flush();
    return 0;
}