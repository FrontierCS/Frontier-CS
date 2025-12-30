#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

ll query(int u, int v) {
    cout << "? " << u << " " << v << endl;
    cout.flush();
    ll res;
    cin >> res;
    return res;
}

void solve() {
    int n;
    cin >> n;
    if (n == 1) {
        cout << "!" << endl;
        return;
    }

    vector<ll> d1(n+1), dB(n+1);
    // query from vertex 1 to all others
    for (int i = 2; i <= n; ++i) {
        d1[i] = query(1, i);
    }
    d1[1] = 0;

    // find farthest vertex from 1
    int B = 2;
    for (int i = 3; i <= n; ++i) {
        if (d1[i] > d1[B]) B = i;
    }

    // query from B to all others
    for (int i = 1; i <= n; ++i) {
        if (i != B) {
            dB[i] = query(B, i);
        }
    }
    dB[B] = 0;

    ll L = d1[B];
    vector<ll> x(n+1), off(n+1);
    // vertices on the main path have off=0
    vector<int> path;
    for (int i = 1; i <= n; ++i) {
        x[i] = (d1[i] + L - dB[i]) / 2;
        off[i] = (d1[i] - L + dB[i]) / 2;
        if (off[i] == 0) {
            path.push_back(i);
        }
    }

    // sort path vertices by distance from 1 (i.e., by x)
    sort(path.begin(), path.end(), [&](int a, int b) {
        return d1[a] < d1[b];
    });

    // map from x value (distance from 1) to the vertex on the path with that x
    map<ll, int> x_to_vertex;
    for (int v : path) {
        x_to_vertex[d1[v]] = v;   // note: for path vertices, x = d1[v]
    }

    // group vertices by attachment point
    vector<vector<int>> groups(n+1);
    for (int i = 1; i <= n; ++i) {
        if (off[i] == 0) {
            // on the path, attach to itself
            groups[i].push_back(i);
        } else {
            int att = x_to_vertex[x[i]];
            groups[att].push_back(i);
        }
    }

    vector<tuple<int, int, ll>> edges;

    // add edges on the main path
    for (size_t i = 0; i + 1 < path.size(); ++i) {
        int u = path[i], v = path[i+1];
        ll w = d1[v] - d1[u];
        edges.emplace_back(u, v, w);
    }

    // process each group
    for (int root : path) {
        vector<int>& group = groups[root];
        if (group.size() <= 1) continue; // only root itself

        // sort group by off value (root has off=0, others positive)
        sort(group.begin(), group.end(), [&](int a, int b) {
            return off[a] < off[b];
        });

        // nodes currently in the tree, sorted by off
        vector<int> nodes = {root};

        // process vertices in increasing order of off (skip root)
        for (int v : group) {
            if (v == root) continue;

            // binary search for parent in nodes
            int lo = 0, hi = nodes.size();
            while (hi - lo > 1) {
                int mid = (lo + hi) / 2;
                int u = nodes[mid];
                ll dist = query(v, u);
                if (dist == off[v] - off[u]) {
                    lo = mid;   // u is an ancestor
                } else {
                    hi = mid;
                }
            }
            int parent = nodes[lo];
            edges.emplace_back(parent, v, off[v] - off[parent]);

            // insert v into nodes at the correct position to maintain sorted order by off
            // (since we process in increasing off, v should be inserted at the end)
            nodes.push_back(v);
            // keep nodes sorted by off (not necessary for binary search, but for clarity)
            for (int i = nodes.size()-1; i > 0; --i) {
                if (off[nodes[i]] < off[nodes[i-1]]) {
                    swap(nodes[i], nodes[i-1]);
                } else break;
            }
        }
    }

    // output answer
    cout << "!";
    for (auto [u, v, w] : edges) {
        cout << " " << u << " " << v << " " << w;
    }
    cout << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        solve();
    }
    return 0;
}