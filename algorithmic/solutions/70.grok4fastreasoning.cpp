#include <bits/stdc++.h>
using namespace std;

int main() {
    int t;
    cin >> t;
    for (int test = 0; test < t; test++) {
        int n, m, start, base;
        cin >> n >> m >> start >> base;
        for (int i = 0; i < m; i++) {
            int u, v;
            cin >> u >> v;
            // ignore edges
        }
        int previous_deg = 0;
        while (true) {
            string token;
            cin >> token;
            if (token == "AC" || token == "F") {
                break;
            }
            int d = stoi(token);
            vector<int> deg_list(d);
            vector<int> flag_list(d);
            for (int i = 0; i < d; i++) {
                cin >> deg_list[i] >> flag_list[i];
            }
            int chosen = -1;
            // prefer unvisited
            for (int i = 0; i < d; i++) {
                if (flag_list[i] == 0) {
                    chosen = i + 1;
                    break;
                }
            }
            if (chosen == -1) {
                // backtrack using previous_deg
                vector<int> candidates;
                for (int i = 0; i < d; i++) {
                    if (flag_list[i] == 1 && deg_list[i] == previous_deg) {
                        candidates.push_back(i + 1);
                    }
                }
                if (!candidates.empty()) {
                    sort(candidates.begin(), candidates.end());
                    chosen = candidates[0];
                } else {
                    // any flag1, smallest index
                    for (int i = 0; i < d; i++) {
                        if (flag_list[i] == 1) {
                            chosen = i + 1;
                            break;
                        }
                    }
                }
            }
            cout << chosen << endl;
            cout.flush();
            previous_deg = d;
        }
    }
    return 0;
}