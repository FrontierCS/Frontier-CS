#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cassert>

using namespace std;

bool ask(int v, const vector<int>& s) {
    if (s.empty()) {
        return false;
    }
    cout << "? " << s.size() << " " << v;
    for (int u : s) {
        cout << " " << u;
    }
    cout << endl;
    int response;
    cin >> response;
    if (response == -1) exit(0);
    return response == 1;
}

// Is v on path between u and w?
bool is_on_path(int v, int u, int w) {
    if (v == u || v == w) return true;
    return ask(v, {u, w});
}

// Partition cand based on whether they are in the same component as pivot wrt root
void partition_by_component(int root, int pivot, const vector<int>& cand, vector<int>& in_pivot_comp, vector<int>& not_in_pivot_comp) {
    if (cand.empty()) {
        return;
    }
    
    vector<int> query_set = cand;
    query_set.push_back(pivot);
    
    if (!ask(root, query_set)) {
        in_pivot_comp.insert(in_pivot_comp.end(), cand.begin(), cand.end());
        return;
    }
    
    if (cand.size() == 1) {
        not_in_pivot_comp.push_back(cand[0]);
        return;
    }
    
    int mid = cand.size() / 2;
    vector<int> left(cand.begin(), cand.begin() + mid);
    vector<int> right(cand.begin() + mid, cand.end());
    
    partition_by_component(root, pivot, left, in_pivot_comp, not_in_pivot_comp);
    partition_by_component(root, pivot, right, in_pivot_comp, not_in_pivot_comp);
}


vector<pair<int, int>> edges;
int N;

void solve(const vector<int>& V_sub, int root) {
    if (V_sub.size() <= 1) {
        return;
    }
    
    vector<int> unclassified;
    for (int v : V_sub) {
        if (v != root) {
            unclassified.push_back(v);
        }
    }
    
    if (unclassified.empty()) {
        return;
    }
    
    vector<vector<int>> components;
    while (!unclassified.empty()) {
        int pivot = unclassified[0];
        vector<int> current_comp = {pivot};
        
        vector<int> cand;
        if (unclassified.size() > 1) {
            cand.assign(unclassified.begin() + 1, unclassified.end());
        }
        
        vector<int> in_pivot_comp, not_in_pivot_comp;
        partition_by_component(root, pivot, cand, in_pivot_comp, not_in_pivot_comp);
        
        current_comp.insert(current_comp.end(), in_pivot_comp.begin(), in_pivot_comp.end());
        components.push_back(current_comp);
        
        unclassified = not_in_pivot_comp;
    }
    
    for (const auto& comp : components) {
        if (comp.empty()) continue;
        
        int handle = comp[0];
        for (size_t i = 1; i < comp.size(); ++i) {
            if (is_on_path(comp[i], root, handle)) {
                handle = comp[i];
            }
        }
        
        edges.push_back({root, handle});
        solve(comp, handle);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N;
    
    if (N == 1) {
        cout << "!" << endl;
        return 0;
    }
    
    vector<int> all_vertices(N);
    iota(all_vertices.begin(), all_vertices.end(), 1);
    
    solve(all_vertices, 1);
    
    cout << "!" << endl;
    for (const auto& edge : edges) {
        cout << edge.first << " " << edge.second << endl;
    }

    return 0;
}