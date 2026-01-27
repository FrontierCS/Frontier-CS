#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

bool ask(int k, const vector<int>& nodes) {
    cout << "? " << k;
    for (int node : nodes) {
        cout << " " << node;
    }
    cout << endl;
    int result;
    cin >> result;
    if (result == -1) exit(0);
    return result == 1;
}

bool is_connected() {
    return ask(1, {1});
}

void block(int road_idx) {
    cout << "- " << road_idx << endl;
}

void unblock(int road_idx) {
    cout << "+ " << road_idx << endl;
}

void solve() {
    int n, m;
    cin >> n >> m;
    
    vector<pair<int, int>> edges(m);
    for (int i = 0; i < m; ++i) {
        cin >> edges[i].first >> edges[i].second;
    }

    vector<int> repaired(m + 1, 0);
    vector<int> non_bridges;

    // Phase 1: Find all bridges
    for (int i = 1; i <= m; ++i) {
        block(i);
        if (!is_connected()) {
            repaired[i] = 1;
        } else {
            non_bridges.push_back(i);
        }
        unblock(i);
    }
    
    // Phase 2: Find repaired non-bridges
    vector<int> repaired_non_bridges;
    vector<bool> is_blocked(m + 1, false);

    for (int road_idx : non_bridges) {
        block(road_idx);
        is_blocked[road_idx] = true;
    }

    for (int road_idx : non_bridges) {
        unblock(road_idx);
        is_blocked[road_idx] = false;

        vector<int> temp_blocked;
        for (int r_nb_idx : repaired_non_bridges) {
            if (!is_blocked[r_nb_idx]) {
                block(r_nb_idx);
                temp_blocked.push_back(r_nb_idx);
            }
        }
        
        if (!is_connected()) {
            repaired[road_idx] = 1;
            repaired_non_bridges.push_back(road_idx);
        }
        
        for (int r_nb_idx : temp_blocked) {
            unblock(r_nb_idx);
        }

        block(road_idx);
        is_blocked[road_idx] = true;
    }

    cout << "!";
    for (int i = 1; i <= m; ++i) {
        cout << " " << repaired[i];
    }
    cout << endl;
    
    int final_response;
    cin >> final_response;
    if (final_response == 0 || final_response == -1) {
        exit(0);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.flush();
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}