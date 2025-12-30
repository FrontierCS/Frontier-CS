#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n;
    vector<tuple<int,int,long long>> edges;
    unordered_map<unsigned long long, long long> cache;

    static unsigned long long keyPair(int a, int b) {
        if (a > b) swap(a, b);
        return ( (unsigned long long)a << 32 ) | (unsigned long long)b;
    }

    long long query(int u, int v) {
        if (u == v) return 0;
        unsigned long long key = keyPair(u, v);
        auto it = cache.find(key);
        if (it != cache.end()) return it->second;
        cout << "? " << u << " " << v << endl;
        cout.flush();
        long long d;
        if (!(cin >> d)) {
            // In case of I/O error, terminate
            exit(0);
        }
        cache.emplace(key, d);
        return d;
    }

    void add_edge(int u, int v, long long w) {
        // Avoid duplicates just in case
        edges.emplace_back(u, v, w);
    }

    void buildGroup(vector<int>& nodes, vector<long long>& distRoot, int r) {
        int m = (int)nodes.size();
        if (m <= 1) return;

        // Find farthest from r in this group using distRoot
        int idx_x = 0;
        long long Dmax = distRoot[0];
        for (int i = 1; i < m; ++i) {
            if (distRoot[i] > Dmax) {
                Dmax = distRoot[i];
                idx_x = i;
            }
        }
        int x = nodes[idx_x];
        long long D = Dmax; // distance from r to x within the group (in the tree)

        // Query distances from x to all nodes in this group
        vector<long long> dx(m);
        for (int i = 0; i < m; ++i) {
            dx[i] = query(x, nodes[i]);
        }

        // Identify nodes on the path r-x: those i with distRoot[i] + dx[i] == D
        vector<pair<long long,int>> pathList; // (distRoot value, node id)
        vector<int> pathIndices; // indices in nodes/distRoot arrays that are on the path
        pathList.reserve(m);
        pathIndices.reserve(m);
        for (int i = 0; i < m; ++i) {
            if (distRoot[i] + dx[i] == D) {
                pathIndices.push_back(i);
            }
        }

        // Sort path nodes by distRoot increasing
        sort(pathIndices.begin(), pathIndices.end(), [&](int a, int b){
            return distRoot[a] < distRoot[b];
        });

        // Add edges along the path r-x
        for (int i = 0; i + 1 < (int)pathIndices.size(); ++i) {
            int u = nodes[pathIndices[i]];
            int v = nodes[pathIndices[i+1]];
            long long w = distRoot[pathIndices[i+1]] - distRoot[pathIndices[i]];
            add_edge(u, v, w);
        }

        // Prepare mapping from path distance coordinate to node id (use arrays and binary search)
        int k = (int)pathIndices.size();
        vector<long long> pathDist(k);
        vector<int> pathNode(k);
        for (int i = 0; i < k; ++i) {
            int idx = pathIndices[i];
            pathDist[i] = distRoot[idx];
            pathNode[i] = nodes[idx];
        }

        // Groups bucketed by projection onto the path r-x
        vector<vector<int>> groupIdx(k);
        for (int i = 0; i < m; ++i) {
            long long numerator = distRoot[i] + D - dx[i];
            // It should be even; but we proceed regardless
            long long t = numerator / 2;
            // Binary search in pathDist
            int pos = int(lower_bound(pathDist.begin(), pathDist.end(), t) - pathDist.begin());
            if (pos == k || pathDist[pos] != t) {
                // Inconsistent due to I/O mismatch; attempt to clamp
                if (pos >= k) pos = k - 1;
                else if (pos < 0) pos = 0;
            }
            groupIdx[pos].push_back(i);
        }

        // Recurse on each group anchored at the corresponding path node
        for (int pos = 0; pos < k; ++pos) {
            vector<int>& idxs = groupIdx[pos];
            if ((int)idxs.size() <= 1) continue; // only the path node itself
            int g = pathNode[pos];

            vector<int> subNodes;
            subNodes.reserve(idxs.size());
            vector<long long> subDist;
            subDist.reserve(idxs.size());
            for (int idx : idxs) {
                subNodes.push_back(nodes[idx]);
                long long dd = (distRoot[idx] + dx[idx] - D) / 2;
                subDist.push_back(dd);
            }
            buildGroup(subNodes, subDist, g);
        }
    }

    void solve_case() {
        cin >> n;
        edges.clear();
        cache.clear();

        if (n == 1) {
            cout << "! " << endl;
            cout.flush();
            return;
        }

        // Initial root r = 1; query distances from r to all nodes
        int r = 1;
        vector<int> nodes(n);
        vector<long long> distRoot(n);
        for (int i = 0; i < n; ++i) nodes[i] = i + 1;
        distRoot[0] = 0;
        for (int i = 2; i <= n; ++i) {
            distRoot[i-1] = query(r, i);
        }

        buildGroup(nodes, distRoot, r);

        // Output the reconstructed edges
        cout << "! ";
        for (auto &e : edges) {
            int u, v;
            long long w;
            tie(u, v, w) = e;
            cout << u << " " << v << " " << w << " ";
        }
        cout << endl;
        cout.flush();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    Solver solver;
    while (T--) {
        solver.solve_case();
    }
    return 0;
}