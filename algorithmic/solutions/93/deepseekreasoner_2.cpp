#include <bits/stdc++.h>
using namespace std;

int n, ty;
vector<int> f;
vector<int> order;
vector<int> parent;

int query(const vector<int>& seq) {
    cout << "? " << seq.size();
    for (int x : seq) cout << " " << x;
    cout << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
}

bool is_antichain(const vector<int>& s) {
    // query any order of s, returns true if greedy picks all
    int res = query(s);
    return (res == (int)s.size());
}

bool is_comparable(int a, int b) {
    vector<int> s = {a, b};
    return !is_antichain(s);
}

// Try to determine if a is ancestor of b using up to K witnesses
bool is_ancestor(int a, int b) {
    if (a == b) return false;
    if (!is_comparable(a, b)) return false;
    // We need to find a witness z such that {a,z} not antichain and {b,z} antichain.
    // Limit search to first 50 nodes in the order (excluding a and b)
    int K = 50;
    int tried = 0;
    for (int z : order) {
        if (z == a || z == b) continue;
        tried++;
        if (tried > K) break;
        bool az = !is_antichain({a, z});
        if (!az) continue;
        bool bz = is_antichain({b, z});
        if (bz) return true;
    }
    // If not found, assume not ancestor (may be wrong but hope for the best)
    return false;
}

int main() {
    cin >> n >> ty;
    f.resize(n+1);
    // Compute f[i] for each node i
    for (int i = 1; i <= n; ++i) {
        vector<int> seq;
        seq.push_back(i);
        for (int j = 1; j <= n; ++j)
            if (j != i) seq.push_back(j);
        f[i] = query(seq);
    }
    // Create order sorted by f increasing
    vector<int> ids(n);
    iota(ids.begin(), ids.end(), 1);
    sort(ids.begin(), ids.end(), [&](int x, int y) {
        return f[x] < f[y];
    });
    order = ids;
    parent.resize(n+1, 0);
    parent[order[0]] = 0; // root
    // For each subsequent node, find its parent
    for (size_t i = 1; i < order.size(); ++i) {
        int x = order[i];
        // Scan backwards to find the deepest ancestor
        for (int j = i-1; j >= 0; --j) {
            int p = order[j];
            if (is_ancestor(p, x)) {
                parent[x] = p;
                break;
            }
        }
    }
    // Output answer
    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << parent[i];
    cout << endl;
    cout.flush();
    return 0;
}