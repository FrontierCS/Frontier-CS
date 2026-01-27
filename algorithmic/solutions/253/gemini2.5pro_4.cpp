#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <iterator>

using namespace std;

bool is_connected() {
    cout << "? 1 1" << endl;
    int response;
    cin >> response;
    if (response == -1) {
        exit(0);
    }
    return response == 1;
}

void solve() {
    int n;
    int m;
    cin >> n >> m;
    vector<pair<int, int>> edges(m);
    for (int i = 0; i < m; ++i) {
        cin >> edges[i].first >> edges[i].second;
    }

    vector<int> ans(m, 0);
    vector<int> repaired_roads;
    vector<int> unknown_roads(m);
    iota(unknown_roads.begin(), unknown_roads.end(), 0);

    while (true) {
        vector<int> new_bridges;

        for (int road_idx : repaired_roads) {
            cout << "- " << (road_idx + 1) << endl;
        }

        vector<int> next_unknown_roads;
        for (int road_idx : unknown_roads) {
            cout << "- " << (road_idx + 1) << endl;
            if (!is_connected()) {
                new_bridges.push_back(road_idx);
            } else {
                next_unknown_roads.push_back(road_idx);
            }
            cout << "+ " << (road_idx + 1) << endl;
        }

        for (int road_idx : repaired_roads) {
            cout << "+ " << (road_idx + 1) << endl;
        }

        if (new_bridges.empty()) {
            break;
        }
        
        for (int bridge_idx : new_bridges) {
            ans[bridge_idx] = 1;
            repaired_roads.push_back(bridge_idx);
        }
        unknown_roads = next_unknown_roads;
    }

    cout << "!";
    for (int i = 0; i < m; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;
    
    int final_response;
    cin >> final_response;
    if (final_response == 0) {
        exit(0);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int t;
    cin >> t;
    while (t--) {
        solve();
    }

    return 0;
}