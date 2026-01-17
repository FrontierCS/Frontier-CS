#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

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
    int result;
    cin >> result;
    if (result == -1) {
        exit(0);
    }
    return result == 1;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    if (n == 1) {
        cout << "!" << endl;
        return 0;
    }

    vector<pair<int, int>> edges;
    vector<int> processed_nodes;
    processed_nodes.push_back(1);
    vector<bool> is_processed(n + 1, false);
    is_processed[1] = true;

    for (int i = 1; i < n; ++i) {
        vector<int> unprocessed_nodes;
        for (int j = 1; j <= n; ++j) {
            if (!is_processed[j]) {
                unprocessed_nodes.push_back(j);
            }
        }

        vector<int> s_query = processed_nodes;
        s_query.insert(s_query.end(), unprocessed_nodes.begin(), unprocessed_nodes.end());

        int v_to_attach = -1;
        // Heuristic: find a leaf in the remaining component to attach.
        // This makes the search for a parent more structured.
        if (unprocessed_nodes.size() > 1) {
            for (int v : unprocessed_nodes) {
                vector<int> others;
                for(int u : unprocessed_nodes) {
                    if (u != v) others.push_back(u);
                }
                others.insert(others.end(), processed_nodes.begin(), processed_nodes.end());
                if (!ask(v, others)) {
                    v_to_attach = v;
                    break;
                }
            }
        }
        if (v_to_attach == -1) {
            v_to_attach = unprocessed_nodes[0];
        }
        
        // Binary search for parent in the processed component
        vector<int> candidates = processed_nodes;
        int low = 0, high = candidates.size() - 1;
        int parent_of_v = -1;

        while(low <= high) {
            int mid = low + (high - low) / 2;
            vector<int> prefix_s;
            for(int j = 0; j <= mid; ++j) {
                prefix_s.push_back(candidates[j]);
            }
            
            vector<int> query_set = prefix_s;
            query_set.push_back(v_to_attach);
            
            if (ask(candidates[mid], query_set)) {
                parent_of_v = candidates[mid];
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }

        edges.push_back({parent_of_v, v_to_attach});
        
        is_processed[v_to_attach] = true;
        processed_nodes.push_back(v_to_attach);
        sort(processed_nodes.begin(), processed_nodes.end());
    }

    cout << "!" << endl;
    for (const auto& edge : edges) {
        cout << edge.first << " " << edge.second << endl;
    }

    return 0;
}