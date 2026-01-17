#include <bits/stdc++.h>
using namespace std;

vector<pair<int, int>> edges;

vector<vector<int>> get_clusters(int r, vector<int> nodes) {
    int nn = nodes.size();
    if (nn == 0) return {};
    random_shuffle(nodes.begin(), nodes.end());
    vector<vector<int>> clusters;
    vector<int> remaining = nodes;
    srand(time(0)); // for random_shuffle if needed
    while (!remaining.empty()) {
        int p = remaining.back();
        remaining.pop_back();
        vector<int> cluster = {p};
        size_t j = 0;
        while (j < remaining.size()) {
            int u = remaining[j];
            cout << 0 << " " << u << " " << p << " " << r << endl;
            int med;
            cin >> med;
            if (med != r) {
                cluster.push_back(u);
                remaining[j] = remaining.back();
                remaining.pop_back();
            } else {
                ++j;
            }
        }
        clusters.push_back(cluster);
    }
    return clusters;
}

void build(int root, vector<int> subtree_nodes) {
    vector<int> D;
    for (int nd : subtree_nodes) {
        if (nd != root) D.push_back(nd);
    }
    auto clusters = get_clusters(root, D);
    for (auto& clus : clusters) {
        if (clus.empty()) continue;
        int pi;
        if (clus.size() == 1) {
            pi = clus[0];
        } else {
            // pick two random
            int idx1 = rand() % clus.size();
            int v1 = clus[idx1];
            int idx2 = rand() % clus.size();
            while (idx2 == idx1) idx2 = rand() % clus.size();
            int v2 = clus[idx2];
            // S1
            vector<int> S1;
            for (int x : clus) {
                if (x == v1) {
                    S1.push_back(x);
                    continue;
                }
                cout << 0 << " " << root << " " << v1 << " " << x << endl;
                int med;
                cin >> med;
                if (med == x) S1.push_back(x);
            }
            // S2
            vector<int> S2;
            for (int x : clus) {
                if (x == v2) {
                    S2.push_back(x);
                    continue;
                }
                cout << 0 << " " << root << " " << v2 << " " << x << endl;
                int med;
                cin >> med;
                if (med == x) S2.push_back(x);
            }
            // intersection I
            sort(S1.begin(), S1.end());
            sort(S2.begin(), S2.end());
            vector<int> I;
            set_intersection(S1.begin(), S1.end(), S2.begin(), S2.end(), back_inserter(I));
            // now sort I if >1
            if (I.size() > 1) {
                sort(I.begin(), I.end(), [root](int aa, int bb) {
                    cout << 0 << " " << root << " " << aa << " " << bb << endl;
                    int med;
                    cin >> med;
                    return med == aa;
                });
            }
            pi = I[0];
        }
        edges.emplace_back(root, pi);
        // sub subtree is clus, rooted at pi
        vector<int> sub_nodes = clus;
        build(pi, sub_nodes);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    cin >> n;
    vector<int> all_nodes(n);
    for (int i = 0; i < n; ++i) all_nodes[i] = i + 1;
    build(1, all_nodes);
    cout << 1;
    for (auto& e : edges) {
        cout << " " << e.first << " " << e.second;
    }
    cout << endl;
    return 0;
}