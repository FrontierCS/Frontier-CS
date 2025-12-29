#include <bits/stdc++.h>
using namespace std;

int main() {
    string line;
    getline(cin, line);
    stringstream ss(line);
    int n, m, k;
    ss >> n >> m >> k;

    vector<string> initial(n);
    for (int i = 0; i < n; i++) {
        getline(cin, initial[i]);
    }
    getline(cin, line); // empty after initial

    vector<string> target(n);
    for (int i = 0; i < n; i++) {
        getline(cin, target[i]);
    }

    vector<vector<string>> presets(k);
    vector<pair<int, int>> sizes(k);
    for (int p = 0; p < k; p++) {
        getline(cin, line); // empty before each preset
        getline(cin, line);
        stringstream ss2(line);
        int np, mp;
        ss2 >> np >> mp;
        sizes[p] = {np, mp};
        presets[p].resize(np);
        for (int i = 0; i < np; i++) {
            getline(cin, presets[p][i]);
        }
    }

    // Check if initial == target
    bool same = true;
    for (int i = 0; i < n; i++) {
        if (initial[i] != target[i]) {
            same = false;
            break;
        }
    }
    if (same) {
        cout << 0 << endl;
    } else {
        cout << -1 << endl;
    }

    return 0;
}