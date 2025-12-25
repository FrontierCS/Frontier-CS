#include <bits/stdc++.h>
using namespace std;

typedef pair<int, int> pii;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        int n;
        cin >> n;
        if (n == 1) {
            cout << "!\n";
            cout.flush();
            continue;
        }

        vector<int> depth(n + 1);
        depth[1] = 0;
        // query distances from root 1 to all other nodes
        for (int i = 2; i <= n; i++) {
            cout << "? 1 " << i << endl;
            cout.flush();
            int d;
            cin >> d;
            depth[i] = d;
        }

        // nodes except root sorted by depth
        vector<int> order(n - 1);
        iota(order.begin(), order.end(), 2);
        sort(order.begin(), order.end(),
             [&](int a, int b) { return depth[a] < depth[b]; });

        // processed nodes in increasing depth order (root first, then others)
        vector<int> processed;
        processed.push_back(1);

        vector<int> parent(n + 1, 0);
        map<pii, int> cache;
        // store known distances from root
        for (int i = 2; i <= n; i++) {
            cache[{1, i}] = depth[i];
            cache[{i, 1}] = depth[i];
        }

        for (int u : order) {
            int sz = processed.size();
            int sample_cnt = min(30, sz);
            // take the deepest 'sample_cnt' nodes from processed
            vector<int> samples;
            for (int i = 0; i < sample_cnt; i++) {
                samples.push_back(processed[sz - 1 - i]);
            }

            int Lmax = -1;
            for (int v : samples) {
                int d_uv;
                auto it = cache.find({u, v});
                if (it != cache.end()) {
                    d_uv = it->second;
                } else {
                    cout << "? " << u << " " << v << endl;
                    cout.flush();
                    cin >> d_uv;
                    cache[{u, v}] = d_uv;
                    cache[{v, u}] = d_uv;
                }
                int L = (depth[u] + depth[v] - d_uv) / 2;
                if (L > Lmax) Lmax = L;
            }

            bool found = false;
            // check nodes with depth == Lmax (from deepest to shallowest)
            for (int idx = sz - 1; idx >= 0; idx--) {
                int v = processed[idx];
                if (depth[v] < Lmax) break;
                if (depth[v] == Lmax) {
                    int d_uv;
                    auto it = cache.find({u, v});
                    if (it != cache.end()) {
                        d_uv = it->second;
                    } else {
                        cout << "? " << u << " " << v << endl;
                        cout.flush();
                        cin >> d_uv;
                        cache[{u, v}] = d_uv;
                        cache[{v, u}] = d_uv;
                    }
                    if (d_uv == depth[u] - depth[v]) {
                        parent[u] = v;
                        found = true;
                        break;
                    }
                }
            }

            if (!found) {
                // fallback: check all processed nodes from deepest to shallowest
                for (int idx = sz - 1; idx >= 0; idx--) {
                    int v = processed[idx];
                    int d_uv;
                    auto it = cache.find({u, v});
                    if (it != cache.end()) {
                        d_uv = it->second;
                    } else {
                        cout << "? " << u << " " << v << endl;
                        cout.flush();
                        cin >> d_uv;
                        cache[{u, v}] = d_uv;
                        cache[{v, u}] = d_uv;
                    }
                    if (d_uv == depth[u] - depth[v]) {
                        parent[u] = v;
                        found = true;
                        break;
                    }
                }
            }

            // add u to processed list (maintain sorted by depth)
            processed.push_back(u);
        }

        // output answer
        cout << "!";
        for (int u = 2; u <= n; u++) {
            int p = parent[u];
            int w = depth[u] - depth[p];
            cout << " " << p << " " << u << " " << w;
        }
        cout << endl;
        cout.flush();
    }

    return 0;
}