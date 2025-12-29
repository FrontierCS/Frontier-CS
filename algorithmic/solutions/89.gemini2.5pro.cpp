#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cassert>

using namespace std;

// Wrapper for judge interaction to ask if v is in Steiner(s).
bool ask(int v, const vector<int>& s) {
    if (s.empty()) return false;
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

// Helper to check if v is on the simple path between u1 and u2.
bool is_on_path(int v, int u1, int u2) {
    if (v == u1 || v == u2) return true;
    return ask(v, {u1, u2});
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    if (n <= 2) {
        cout << "!" << endl;
        if (n == 2) {
            cout << "1 2" << endl;
        }
        return 0;
    }

    // Step 1: Find the path between vertices 1 and 2.
    int u1 = 1, u2 = 2;
    
    vector<int> path_nodes;
    path_nodes.push_back(u1);
    if (u2 != u1) path_nodes.push_back(u2);
    for (int i = 1; i <= n; ++i) {
        if (i == u1 || i == u2) continue;
        if (is_on_path(i, u1, u2)) {
            path_nodes.push_back(i);
        }
    }

    // Step 2: Order the vertices on the path by distance from u1.
    sort(path_nodes.begin(), path_nodes.end(), [&](int p1, int p2) {
        if (p1 == u1) return true;
        if (p2 == u1) return false;
        return is_on_path(p1, u1, p2);
    });

    vector<pair<int, int>> edges;
    for (size_t i = 0; i < path_nodes.size() - 1; ++i) {
        edges.push_back({path_nodes[i], path_nodes[i + 1]});
    }

    // Step 3: Attach all other vertices to the path.
    vector<bool> on_path_mask(n + 1, false);
    for (int node : path_nodes) {
        on_path_mask[node] = true;
    }

    vector<int> other_nodes;
    for (int i = 1; i <= n; ++i) {
        if (!on_path_mask[i]) {
            other_nodes.push_back(i);
        }
    }

    int path_endpoint = path_nodes.back();

    for (int node : other_nodes) {
        int low = 0, high = path_nodes.size() - 1;
        int attach_idx = high;

        // Binary search for the attachment point.
        // The attachment point `p_i` is the first node on the ordered path `u1...endpoint`
        // that also lies on the path from `node` to `endpoint`.
        while (low <= high) {
            int mid = low + (high - low) / 2;
            if (is_on_path(path_nodes[mid], node, path_endpoint)) {
                attach_idx = mid;
                high = mid - 1;
            } else {
                low = mid + 1;
            }
        }
        edges.push_back({node, path_nodes[attach_idx]});
    }

    cout << "!" << endl;
    for (const auto& edge : edges) {
        cout << edge.first << " " << edge.second << endl;
    }

    return 0;
}