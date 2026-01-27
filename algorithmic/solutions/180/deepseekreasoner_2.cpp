#include <bits/stdc++.h>
using namespace std;

int n, m;

int compute_delta(int a, int b, const vector<int>& mapping, const vector<vector<int>>& adj2, const vector<bitset<2000>>& adj1_mat) {
    int delta = 0;
    int pa = mapping[a], pb = mapping[b];
    for (int w : adj2[a]) {
        if (w == b) continue;
        bool old = adj1_mat[pa][mapping[w]];
        bool new_ = adj1_mat[pb][mapping[w]];
        delta += (int)new_ - (int)old;
    }
    for (int w : adj2[b]) {
        if (w == a) continue;
        bool old = adj1_mat[pb][mapping[w]];
        bool new_ = adj1_mat[pa][mapping[w]];
        delta += (int)new_ - (int)old;
    }
    return delta;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    cin >> n >> m;
    vector<vector<int>> adj1(n), adj2(n);
    vector<bitset<2000>> adj1_mat(n), adj2_mat(n);
    
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        u--; v--;
        adj1[u].push_back(v);
        adj1[v].push_back(u);
        adj1_mat[u][v] = adj1_mat[v][u] = 1;
    }
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        u--; v--;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
        adj2_mat[u][v] = adj2_mat[v][u] = 1;
    }
    
    vector<int> deg1(n), deg2(n);
    for (int i = 0; i < n; i++) {
        deg1[i] = adj1[i].size();
        deg2[i] = adj2[i].size();
    }
    
    // Weisfeiler-Lehman labeling (3 iterations)
    vector<int> label1 = deg1, label2 = deg2;
    const int WL_ITER = 3;
    for (int iter = 0; iter < WL_ITER; iter++) {
        vector<size_t> hash1(n), hash2(n);
        unordered_map<size_t, int> hash_to_label;
        int new_label_counter = 0;
        // G1
        for (int i = 0; i < n; i++) {
            vector<int> neigh_labels;
            for (int nb : adj1[i]) neigh_labels.push_back(label1[nb]);
            sort(neigh_labels.begin(), neigh_labels.end());
            size_t h = label1[i];
            for (int x : neigh_labels) h = h * 1000000007 + x + 123;
            hash1[i] = h;
            if (!hash_to_label.count(h)) hash_to_label[h] = new_label_counter++;
        }
        // G2
        for (int i = 0; i < n; i++) {
            vector<int> neigh_labels;
            for (int nb : adj2[i]) neigh_labels.push_back(label2[nb]);
            sort(neigh_labels.begin(), neigh_labels.end());
            size_t h = label2[i];
            for (int x : neigh_labels) h = h * 1000000007 + x + 123;
            hash2[i] = h;
            if (!hash_to_label.count(h)) hash_to_label[h] = new_label_counter++;
        }
        // assign new labels
        for (int i = 0; i < n; i++) label1[i] = hash_to_label[hash1[i]];
        for (int i = 0; i < n; i++) label2[i] = hash_to_label[hash2[i]];
    }
    
    // Group vertices by label
    unordered_map<int, vector<int>> map1, map2;
    for (int i = 0; i < n; i++) map1[label1[i]].push_back(i);
    for (int i = 0; i < n; i++) map2[label2[i]].push_back(i);
    
    vector<int> mapping(n, -1);
    vector<bool> used1(n, false);
    vector<int> unmatched1, unmatched2;
    
    // Collect all labels that appear in either graph
    set<int> all_labels;
    for (auto& p : map1) all_labels.insert(p.first);
    for (auto& p : map2) all_labels.insert(p.first);
    
    for (int L : all_labels) {
        vector<int> list1, list2;
        if (map1.count(L)) list1 = map1[L];
        if (map2.count(L)) list2 = map2[L];
        sort(list1.begin(), list1.end(), [&](int a, int b) {
            return tie(deg1[a], a) < tie(deg1[b], b);
        });
        sort(list2.begin(), list2.end(), [&](int a, int b) {
            return tie(deg2[a], a) < tie(deg2[b], b);
        });
        int sz = min(list1.size(), list2.size());
        for (int i = 0; i < sz; i++) {
            mapping[list2[i]] = list1[i];
            used1[list1[i]] = true;
        }
        for (int i = sz; i < (int)list1.size(); i++) unmatched1.push_back(list1[i]);
        for (int i = sz; i < (int)list2.size(); i++) unmatched2.push_back(list2[i]);
    }
    
    sort(unmatched1.begin(), unmatched1.end(), [&](int a, int b) { return deg1[a] < deg1[b]; });
    sort(unmatched2.begin(), unmatched2.end(), [&](int a, int b) { return deg2[a] < deg2[b]; });
    for (int i = 0; i < (int)unmatched1.size(); i++) {
        mapping[unmatched2[i]] = unmatched1[i];
    }
    
    // Compute initial matched edges
    int matched = 0;
    for (int u = 0; u < n; u++) {
        for (int v : adj2[u]) {
            if (v > u) continue; // count each edge once
            if (adj1_mat[mapping[u]][mapping[v]]) matched++;
        }
    }
    
    // Local search: deterministic swaps within small label groups (size <= 5)
    const int MAX_GROUP_SIZE = 5;
    for (auto& p : map2) {
        vector<int>& group = p.second;
        if (group.size() <= MAX_GROUP_SIZE) {
            int sz = group.size();
            for (int i = 0; i < sz; i++) {
                for (int j = i+1; j < sz; j++) {
                    int a = group[i], b = group[j];
                    int delta = compute_delta(a, b, mapping, adj2, adj1_mat);
                    if (delta > 0) {
                        swap(mapping[a], mapping[b]);
                        matched += delta;
                    }
                }
            }
        }
    }
    
    // Random swaps
    const int RANDOM_SWAPS = 200000;
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist(0, n-1);
    for (int iter = 0; iter < RANDOM_SWAPS; iter++) {
        int a = dist(rng);
        int b = dist(rng);
        if (a == b) continue;
        int delta = compute_delta(a, b, mapping, adj2, adj1_mat);
        if (delta > 0) {
            swap(mapping[a], mapping[b]);
            matched += delta;
        }
    }
    
    // Output mapping (1-indexed)
    for (int i = 0; i < n; i++) {
        cout << mapping[i] + 1 << (i+1 == n ? '\n' : ' ');
    }
    
    return 0;
}